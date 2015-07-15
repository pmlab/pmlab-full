#! /usr/bin/python
"""Module to encode the PN discovery problem into a SAT problem using
Satisfiability Modulo Theories (SMT). Ouput is a CVC file (to stdout)
which can be fed to the STP solver."""

from collections import defaultdict, namedtuple
from operator import itemgetter
from optparse import OptionParser
from bitstring import BitArray
import itertools
import bisect

def constant_factory(value):
    return itertools.repeat(value).next

def binary(number, digits=8):
    """Returns the binary string that represents [n] with the given 
    number of [digits]."""
    return "{0:0>{1}}".format(bin(number)[2:], digits)

def sum_of_bits( bit_list, digits=None, use_parenthesis=False ): 
    """Returns the STP expression that represents the sum of an iterable 
    representing bits. If [digits] is None, the size of the sum is determined by
    the number of elements in [bit_list]."""
    if digits == None:
        bits = len(bin(len(bit_list)))-2 # -2 because of '0b' prefix
    else:
        bits = digits
    if len(bit_list) == 1:
        if bits == 1:
            return bit_list[0]
        return "0bin"+'0'*(bits-1)+'@'+bit_list[0]
    if use_parenthesis:
        left_separator = '('
        right_separator = ')'
    else:
        left_separator = ''
        right_separator = ''
    return "BVPLUS({0},".format(bits)+','.join(["0bin"+'0'*(bits-1)+'@'+
        left_separator+bool_var+right_separator for bool_var in bit_list])+')'

def boolean_variables( ts, var_mode='single' ):
    """Returns the set of Boolean variables used to encode the problem"""
    #for each state, one variable for the multiplicity
    #for each event, two variables, one for negative gradient, one for the positive
    if var_mode == 'double':
        variables = (list( ts.get_state_names() ) + 
                    ['dp_{0}'.format(ev) for ev in ts.get_signals()] +
                    ['dn_{0}'.format(ev) for ev in ts.signals])
    else:
        variables = (list( ts.get_state_names() ) + 
                    ['d_{0}'.format(ev) for ev in ts.get_signals()])
    return variables

def generate_stp_max_multiplicity( ts, max_mult ):
    """Print an equation that limits the sum of multiplicities in the PN region,
     if max_mult != None. Uses only the input variables. Returns the number of 
    constraints generated."""
    if not max_mult:
        return 0
    m = max_mult
    print "% Equations limiting complexity"
    print "% limiting sum of multiplicities to", m
    bits = len(bin(max(m,ts.number_of_states())))-2
    print 'ASSERT( BVLE({0},0bin{1}) );'.format( 
                                    sum_of_bits(ts.number_of_states(), bits),
                                    binary(m, bits ) )
    return 1 # only 1 new constraint

def generate_stp_forbid_places( ts, k, place_list ):
    """Generates an equation that forbids the generation of a superregion
    of any of the regions in [place_list]."""
    bits = len(bin(k)) - 2
    for place in place_list:
        print 'ASSERT(',' OR '.join(['BVLT({0},0bin{1})'.format(state,binary(place.multiplicity[state], bits)) 
                            for state in ts.get_state_names() if place.multiplicity[state] > 0]), ');'
    return len(place_list)

def generate_stp_subset_place( ts, k, place ):
    """Generates an equation that enforces the generation of a subset of the
    region  in [place]."""
    bits = len(bin(k)) - 2
    print 'ASSERT(',' AND '.join(['BVLE({0},0bin{1})'.format(state,binary(place.multiplicity[state], bits)) 
                            for state in ts.get_state_names()]), ');'
    #should be a proper subregion
    print 'ASSERT(',' OR '.join(['BVLT({0},0bin{1})'.format(state,binary(place.multiplicity[state], bits)) 
                            for state in ts.get_state_names() if place.multiplicity[state] > 0]), ');'
    return 2

def generate_stp_from_ts( ts, variables, k=1, var_mode='single', 
                        place_list=[], subset_place=None, max_mult=None ):
    """Main function to generate a CVC file (to stdout) that represents the 
    PN discovery problem. The file can then be fed to the STP solver.
    [place_list] contains a list of already discovered places that should be avoided."""
    #print the variables
    print "% Total number of variables:", len(variables)
    bits = len(bin(k)) - 2
    bitvector_str = ': BITVECTOR({0});'.format(bits)
    if var_mode == 'double':
        for i in xrange(0,len(variables),10):
            print ','.join(variables[i:i+10]), bitvector_str
    else:
        state_vars = [v for v in variables if v[0] != 'd']
        for i in xrange(0,len(state_vars),10):
            print ','.join(state_vars[i:i+10]), bitvector_str
        bitvector_str = ': BITVECTOR({0});'.format(bits+1) # since gradient can be negative
        delta_vars = [v for v in variables if v[0] == 'd']
        for i in xrange(0,len(delta_vars),10):
            print ','.join(delta_vars[i:i+10]), bitvector_str
    #build the constraints
    constraint_number = 0
    if var_mode == 'double':
        for src_st, act, dest_st in ts.get_edges():
            print 'ASSERT( {0}=BVSUB({1},BVPLUS({1},{2},dp_{3}),dn_{3}) );'.format( dest_st, bits,
                                                            src_st, act)
            print 'ASSERT( BVLE(dp_{0},BVSUB({1},0bin{2},{3})) );'.format( act,
                                                                bits, binary(k,bits), src_st )
            print 'ASSERT( BVLE(dn_{0},{1}) );'.format( act, src_st )
            constraint_number += 3
        #require at least one negative gradient
        delta_vars = [v for v in variables if v[0:2] == 'dn']
        print 'ASSERT( BVGT({0},0bin{1}) );'.format('|'.join(delta_vars), binary(0,bits) )
        constraint_number += 1
    else:
        for src_st, act, dest_st in ts.get_edges():
            print 'ASSERT( {0}=BVPLUS({1},0bin0@{2},d_{3})[{4}:0] );'.format( dest_st, bits+1,
                                                            src_st, act, bits-1)
            print 'ASSERT( SBVLE(d_{0},BVSUB({1},0bin{2},0bin0@{3})) );'.format( act,
                                                                bits+1, binary(k,bits+1), src_st )
            print 'ASSERT( SBVLE(BVUMINUS(d_{0}),0bin0@{1}) );'.format( act, src_st )
            constraint_number += 3
        #require at least one negative gradient
        print 'ASSERT( ({0})=0bin1 );'.format( '|'.join(['d_{0}[{1}:{1}]'.format(ev,bits) 
                                                    for ev in ts.get_signals()]) )
        #bound states
        print 'ASSERT( {0} );'.format(' AND '.join(['BVLE({0},0bin{1})'.format(st,binary(k,bits)) 
                                                    for st in ts.get_state_names()]))
        #bound gradients
        minus_k = '0bin{0}'.format(BitArray('int:{0}=-{1}'.format(bits+1,k)).bin)
        print 'ASSERT( {0} );'.format(' AND '.join(['SBVGE(d_{0},{1})'.format(ev,minus_k) 
                                                    for ev in ts.get_signals()]))
        constraint_number += 2
    
    #require non-null region
    print 'ASSERT( BVGT({0},0bin{1}) );'.format('|'.join(ts.get_state_names()), binary(0,bits) )
    constraint_number += 1
    print "% Structural constraints:", constraint_number
    constraint_number += generate_stp_max_multiplicity( ts, max_mult )
    constraint_number += generate_stp_forbid_places( ts, k, place_list )
    if subset_place != None:
        constraint_number += generate_stp_subset_place( ts, k, subset_place )
    
    print "%Total number of constraints:", constraint_number
    print
    print "QUERY (FALSE);"
    print "COUNTEREXAMPLE;"

#def add_parser_options( parser ):
#    """Adds the parser options used by this module to the command line parser"""
#    parser.add_option("-k", type="int", dest="k", 
#            help="Search only for k-bounded regions [default: %default]",
#            default=1)
#    parser.add_option("-m", type="int", dest="max_multiplicity", 
#            help="Maximum sum of multiplicities (0 unbounded) [default: %default]",
#            default=0)
#
#    parser.add_option("--vm", "--var_mode", metavar="MODE", type="choice", 
#            dest="var_mode",
#            choices=["single", "double"],
#            help=("Determine gradient encoding to use [default: %default]:\n"
#            "single: a single variable per event gradient\n"
#            "double: two variables per event, one for the negative and one for the positive gradient."),
#            default="single")
#    parser.add_option("--debug", action="store_true", dest="debug", 
#            help="Debug mode", default=False)

#def main():
#    """Main function of this module, called if the module is directly called"""
#    parser = OptionParser(usage="%prog [options] filename", version="%prog 0.1",
#                description=("Prints the arithmetic constraint problem, "
#                        "in CVC format, that encode the PN discovery "
#                        "problem for the given TS."))
#    add_parser_options( parser )
#    (options, args) = parser.parse_args()
#    if len(args) != 1:
#        parser.error("incorrect number of arguments. Type -h for help.")
#    try:
#        ts = TransitionSystem()
#        ts.read_from_file(args[0])
#    except Exception as ex:
#        print("Error. Cannot open file '%s'. %s" % (args[0], ex))
#        return 1
##    log_info = load_log( logfile )
##    traces = log_info.traces
##    logfile.close()
#    variables = boolean_variables( ts, options )
#    generate_stp_from_ts( ts, variables, options )
#    return 0
#
#if __name__ == '__main__':
#    main()
