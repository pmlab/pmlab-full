#! /usr/bin/python

""" Module offering different simulation algorithms for causal nets
"""
import sys
import subprocess
import datetime
from optparse import OptionParser, OptionGroup
from collections import defaultdict, Counter, namedtuple
import copy

#from cnet import Cnet
from cn_stp import (var_prefix, VariableInformation, generate_structural_stp_inout,
                    generate_stp_max_obligations, sum_of_bits, binary, 
                    boolean_variables)
from .. cnet import Cnet, stp_solver
from .. log import Log

#stp_solver = '/usr/local/bin/stp'

BindingInformation = namedtuple('BindingInformation','input_binding_positions input_mandatory output_binding_positions output_mandatory')

def submultiset_set( mult1, mult2 ):
    """Returns True if mult1 is a submultiset of mult2. In this case mult1 is simply a set of elements
    with occurrence 1"""
    for act in mult1:
        if act not in mult2:
            return False
        else:
            if mult2[act]==0:
                return False
    return True

##TODO: update to new TS class
def simulate_ts_state(cn, tsys, options):
    """For each state in the transition system tsys, we compute its 
    obligation state. The result is the list of obligation states"""
    debug = options.debug
    states = [[] for x in tsys.states]
    #deviations = defaultdict(int) # key is (0) available obligations on act. e, (1) consumed obligations on act. e, 
                    # value is num. of traces where this deviation occurs.
    start_act = cn.starting_activities()
    final_act = cn.final_activities()
    if debug:
        print 'Initial activities:', start_act
    for act in start_act:
        #print 'Activity',act,'has no input set'
        try:
            pos = [x[0] for x in tsys.states[0][1]].index(act)
            target_state = tsys.states[0][1][pos][1]
            # generate target multiset
            outstate_list = [Counter(dict([((act, outact),1) for outact in outset])) for outset in cn.outset[act]]
            #print outstate_list
            states[ target_state ]= outstate_list
        except ValueError:
            if debug:
                print 'Activity',act,'with empty input set (so it is an initial activity),',
                print 'has no corresponding arc in transition system'
    ok_traces = 0
    ok_distinct_traces = 0
    for i in range(1,len(states)):
        #find fireable activities
        if debug:
            print 'Simulating at state',i,'out of {0}'.format(len(states))
            #print 'Simulating at state',i,'out of {0}:'.format(len(states)), states[ i ]
        #check if it is a sink state
        if len(tsys.states[i][1]) == 0:
            #sink state
            #check if emptyset 
            if states[i] == [Counter()]:
                #print tsys.states[i][0][0]
                ok_traces += tsys.states[i][0][0][1]
                ok_distinct_traces += 1
        for act, inset in cn.inset.iteritems():
            for ins in inset:
                #check if this inset is a submultiset of some of the multisets of the state
                inmultiset = dict([((inact, act),1) for inact in ins])
                for multiset in states[i]:
                    if submultiset_set(inmultiset, multiset):
                        
                        remainder_multiset = multiset - Counter(inmultiset)
                        if act in final_act and len(remainder_multiset) > 0: # final activities should leave an empty state
                            continue
                        if debug:
                            print "activity", act, "fireable in state", i,
                        try:
                            pos = [x[0] for x in tsys.states[i][1]].index(act)
                            target_state = tsys.states[i][1][pos][1]
                            if debug:
                                print 'to state', target_state
                            outstate_list = [remainder_multiset+Counter(dict([((act, outact),1) for outact in outset])) for outset in cn.outset[act]]
                            if len(outstate_list) > 0:
                                states[ target_state ] += outstate_list
                            else:
                                states[ target_state ] += [Counter()]
                        except ValueError:
                            total_traces_through_i = sum([x[1] for x in tsys.states[i][0]])
                            relevant_state_obligations = tuple([x for x in multiset.keys() if x[1]==act])
                            #deviations[(relevant_state_obligations, tuple(inmultiset.keys()))] += total_traces_through_i
                            if debug:
                                print 'Activity',act,'has no corresponding arc in transition system'
                        #pass
    #state = Counter()
    #print deviations
    return states, ok_traces, ok_distinct_traces
    #return deviations
    
def smt_boolean_variables(cn, traces):
    """Returns the set of Boolean variables used to encode the problem"""
    arcs = cn.arcs()
    input_alphabet = defaultdict(set) #use Cnet arcs
    output_alphabet = defaultdict(set)
    for act1, act2 in arcs:
        input_alphabet[act2].add( act1 )
    # compute also output alphabet, by reversing information
    for act1, act_set in input_alphabet.iteritems():
        for act2 in act_set:
            output_alphabet[act2].add(act1)
    variables = []
    obligation_dict = {}
    alphabet = set()
    # maps each obligation (a,b) to a tuple: 
    # (0) variables for input (1) variables for output
    for case_num, words in enumerate(traces):
        for i in range(len(words)):
            alphabet.add( words[i] )
            #input variables (obligation consumption)
            seen_vars = set()
            for j in range(i):
                if words[j] not in input_alphabet[words[i]]:
                    continue
                if words[j] not in seen_vars:
                    var_name = "{0}x{1}_{2}_{3}".format(
                                    var_prefix( case_num, i), i, 
                                    words[j], words[i])
                    if (words[j], words[i]) not in obligation_dict:
                        obligation_dict[(words[j], words[i])] = ([var_name], [])
                    else:
                        obligation_dict[(words[j], words[i])][0].append(var_name)
                    seen_vars.add( words[j] )
                    variables.append( var_name )
            #output variables (obligation production)
            seen_vars = set()
            for j in range(i+1, len(words)):
                if words[j] not in output_alphabet[words[i]]:
                    continue
                if words[j] not in seen_vars:
                    var_name = "{0}y{1}_{2}_{3}".format(
                                var_prefix(case_num, j), i, 
                                words[i], words[j])
                    if (words[i], words[j]) not in obligation_dict:
                        obligation_dict[(words[i], words[j])] = ([], [var_name])
                    else:
                        obligation_dict[(words[i], words[j])][1].append(var_name)
                    seen_vars.add( words[j] )
                    variables.append( var_name )
    return VariableInformation( alphabet, variables, obligation_dict, input_alphabet, output_alphabet )

def generate_stp_cn_choices( cn, log, var_info ):
    constraint_number = 0
    traces = log.get_uniq_cases()
    #activity_positions = log_info.activity_positions
    input_alphabet = var_info.input_alphabet
    output_alphabet = var_info.output_alphabet
    input_binding_positions = dict([(act,defaultdict(list)) for act in var_info.alphabet])
    output_binding_positions = dict([(act,defaultdict(list)) for act in var_info.alphabet])
    #maps activity to a dictionary. This second dict, maps binding to position information:
    # list of (trace_number, pos, local_universe)
    input_mandatory = set()
    output_mandatory = set()
    #set of tuples (act, binding) that are mandatory
    #print input_binding_positions
    for case_num, words in enumerate(traces):
        prev_alph = set()
        for i,w in enumerate(words):
            #check which input bindings are possible in this context
            candidates = [ins for ins in cn.inset[w] if ins <= prev_alph]
            local_universe = input_alphabet[w] & prev_alph
            terms = []
            if len(candidates) == 1:
                input_mandatory.add((w,candidates[0]))
            elif len(candidates) == 0 and i > 0:
                print '%Activity {0} in position {1} of trace {2} has empty input!'.format( w, i, case_num )
                print 'ASSERT( FALSE );'
            for ins in candidates:
                input_binding_positions[w][ins].append((case_num,i,local_universe))
                remainder = local_universe - ins
                assignments = []
                for act in ins:
                    #set to 1
                    var_name = "t{0}x{1}_{2}_{3}".format(case_num, i, 
                                                            act, w)
                    assignments.append( var_name + '=0bin1' )
                for act in remainder:
                    #set to 0
                    var_name = "t{0}x{1}_{2}_{3}".format(case_num, i, 
                                                            act, w)
                    assignments.append( var_name + '=0bin0' )
                terms.append( '('+' AND '.join(assignments)+')' )
            if len(terms) > 0:
                print 'ASSERT('+' OR '.join( terms )+');'
                constraint_number += 1
            prev_alph.add(w)
        #now restrict output bindings
        all_occ = Counter(words[1:])
        for i,w in enumerate(words):
            #print all_occ
            #check which output bindings are possible in this context
            succ_alph = set(all_occ)
            #print succ_alph
            candidates = [outs for outs in cn.outset[w] if outs <= succ_alph]
            local_universe = output_alphabet[w] & succ_alph
            terms = []
            if len(candidates) == 1:
                output_mandatory.add((w,candidates[0]))
            elif len(candidates) == 0 and i < len(words)-1:
                print '%Activity {0} in position {1} of trace {2} has empty output!'.format( w, i, case_num )
                print 'ASSERT( FALSE );'
            for outs in candidates:
                output_binding_positions[w][outs].append((case_num,i,local_universe))
                remainder = local_universe - outs
                assignments = []
                for act in outs:
                    #set to 1
                    var_name = "t{0}y{1}_{2}_{3}".format(case_num, i, 
                                                            w, act)
                    assignments.append( var_name + '=0bin1' )
                for act in remainder:
                    #set to 0
                    var_name = "t{0}y{1}_{2}_{3}".format(case_num, i, 
                                                         w, act)
                    assignments.append( var_name + '=0bin0' )
                terms.append( '('+' AND '.join(assignments)+')' )
            if len(terms) > 0:
                print 'ASSERT('+' OR '.join( terms )+');'
                constraint_number += 1
            if i < len(words)-1:
                all_occ -= Counter({words[i+1]:1})
        
    return constraint_number, BindingInformation(input_binding_positions, input_mandatory,
                                output_binding_positions, output_mandatory)

#def generate_smt_min_unused( cn, log_info, var_info, options ):
def generate_smt_unused_bindings( binding_info, min_unused ):
    """Generates a formula that bounds the minimum number of unused bindings"""
    # A binding is unused if, in all places where it can appear, it does not.
    print "%Generating min unused bindings formula with min_unused =", min_unused
    if min_unused == 0:
        return 0
    in_binding_pos = binding_info.input_binding_positions
    out_binding_pos = binding_info.output_binding_positions
    in_mandatory = binding_info.input_mandatory
    out_mandatory = binding_info.output_mandatory
    and_terms = []
    for act, mp in in_binding_pos.iteritems():
        for ins, pos in mp.iteritems():
            if (act,ins) in in_mandatory:
                continue
            or_terms = []
            for p in pos:
                remainder = p[2] - ins
                assignments = []
                for pre in ins:
                    #set to 1
                    var_name = "t{0}x{1}_{2}_{3}".format(p[0], p[1], pre, act)
                    assignments.append( '~'+var_name )
                for pre in remainder:
                    #set to 0
                    var_name = "t{0}x{1}_{2}_{3}".format(p[0], p[1], pre, act)
                    assignments.append( var_name )
                or_terms.append('('+'|'.join( assignments )+')')
                #print or_terms
            and_terms.append( '&'.join(or_terms) )
    for act, mp in out_binding_pos.iteritems():
        for outs, pos in mp.iteritems():
            if (act,outs) in out_mandatory:
                continue
            or_terms = []
            for p in pos:
                remainder = p[2] - outs
                assignments = []
                for post in outs:
                    #set to 1
                    var_name = "t{0}y{1}_{2}_{3}".format(p[0], p[1], act, post)
                    assignments.append( '~'+var_name )
                for post in remainder:
                    #set to 0
                    var_name = "t{0}y{1}_{2}_{3}".format(p[0], p[1], act, post)
                    assignments.append( var_name )
                or_terms.append('('+'|'.join( assignments )+')')
                #print or_terms
            and_terms.append( '&'.join(or_terms) )
    bits = len(bin(len(and_terms)))-2 # discard '0b'
    print 'ASSERT(BVGE({0},0bin{1}));'.format(sum_of_bits(and_terms,use_parenthesis=True), binary(min_unused, bits ))
    return 1

def generate_smt_from_cn_and_log( cn, log, var_info, 
                                    min_unused_bindings=None,
                                    max_global_obligations=0 ):
    """Main function to generate a CVC file (to stdout) that represents the 
    C-net simulation problem. The file can then be fed to the STP solver.
    Returns the number of potentially unused bindings in the C-net.
    
    [cn] C-net to simulate.
    [log] log to simulate. Must fit inside [cn]
    [min_unused_bindings] Minimum number of required unused bindings.
        If 0, then compute the number of mandatory bindings
        and the number of potentially unused bindings. Use this latter value 
        halfed as required number of minimum unused bindings. Use None
        if no minimum number of bindings is required.
    [max_global_obligations] If > 0, restricts the maximum number of generated
        obligations during the simulation of the log.
    """
    #print the variables
    traces = log.get_uniq_cases()
    activity_positions = log.get_activity_positions()
    variables = var_info.variables
    obligation_dict = var_info.obligation_dict
    print "% Total number of variables:", len(variables)
    var_num = 1
    for var in variables:
        if var_num % 10 == 0 or var_num == len(variables):
            print var, ': BITVECTOR(1);'
        else:
            print var+',',
        var_num += 1
    #build the constraints
    constraint_number = generate_structural_stp_inout(log, var_info)
    if max_global_obligations > 0:
        constraint_number += generate_stp_max_obligations( log, variables, 
                                         max_global_obligations )
    print "% Structural constraints:", constraint_number
    #restrict input/output bindings to the ones in the given Cnet cn
    constraint_number2, binding_info = generate_stp_cn_choices( cn, log, var_info )
    constraint_number += constraint_number2
    in_binding_pos = binding_info.input_binding_positions
    out_binding_pos = binding_info.output_binding_positions
    in_mandatory = binding_info.input_mandatory
    out_mandatory = binding_info.output_mandatory
    total_bindings = (sum([len(ins) for ins in cn.inset.values()]) + 
                        sum([len(outs) for outs in cn.outset.values()]))
    total_mandatory = len(in_mandatory)+len(out_mandatory)
    print '%Total bindings:', total_bindings
    print '%Known mandatory bindings:', total_mandatory
    #print in_mandatory
    #print out_mandatory
    potential_unused = total_bindings-total_mandatory
    print '%Min unused bindings', min_unused_bindings
    if min_unused_bindings is not None and min_unused_bindings >= 0:
        if min_unused_bindings == 0:
            #find all non-initial activities without mandatory input bindings
            in_missing = (log.get_alphabet()-set(cn.starting_activities())-
                            set([x[0] for x in in_mandatory]))
            #find all non-final activities without mandatory output bindings
            out_missing = (log.get_alphabet()-set(cn.final_activities())-
                            set([x[0] for x in out_mandatory]))
            remaining_mandatory = len(in_missing) + len(out_missing)
            print '%Generic mandatory bindings (due to obliged connectedness):', remaining_mandatory
            total_mandatory += remaining_mandatory
            print '%Total mandatory bindings:', total_mandatory
            potential_unused = total_bindings-total_mandatory
            constraint_number += generate_smt_unused_bindings( binding_info, 
                                                                potential_unused/2)
        else:
            constraint_number += generate_smt_unused_bindings( binding_info, 
                                                                min_unused_bindings)
    #print in_binding_pos
    #print out_binding_pos
    print "%Total number of constraints:", constraint_number
    print
    print "QUERY (FALSE);"
    print "COUNTEREXAMPLE;"
    return potential_unused

def simulate_smt(cn, log, min_unused_bindings=0):
    var_info = smt_boolean_variables(cn, log.get_uniq_cases())
    return generate_smt_from_cn_and_log(cn, log, var_info, min_unused_bindings)

def fitting_cases_in_skeleton(log, skeleton):
    """Returns a log containing the sequences that would fit in any C-net
    using the arcs in [skeleton] (regardless of the actual bindings that would
    be required).
    
    To speed up the checking, all sequences whose immediately follows relation
    is inside [skeleton] are automatically accepted. Similarly if none of its
    predecessors or successors appears in the skeleton, then the case is sure
    non-fitting."""
#    Be careful with extended strategies. For instance, assume that we check
#    that, for each activity, it must have a relation with at least one 
#    predecessor activity in the case, and the same for successors). 
#    
#    This is an overapproximation, since activities could 'steal' obligations
#    needed by other occurrences of the same activity. e.g., saa with skeleton
#    (s,a) would pass the check, but will not be really fitting. However,
    cases = log.get_uniq_cases()
    set_skeleton = set(skeleton)
    new_cases = defaultdict(int)
    old_stdout = sys.stdout
    stpfile = 'simulate.stp'
    for case_num, (case, occ) in enumerate(cases.iteritems()):
        imm_follows = True
        for i, act in enumerate(case[:-1]):
            if (act,case[i+1]) not in set_skeleton:
                imm_follows = False
                break
        if not imm_follows:
            #see if it is directly non-fitting
            possible = True
            for i, act in enumerate(case):
                if i < len(case)-1:
                    shared_succ = [(a,b) for a,b in skeleton if a==act and b in case[i+1:]]
                    if not shared_succ:
                        possible = False
                        break
                if i > 0:
                    shared_pred = [(a,b) for a,b in skeleton if b==act and a in case[:i]]
                    if not shared_pred:
                        possible = False
                        break
            if possible:
                #check with SMT
                singleton_log = Log(cases=[case])
                sys.stdout = open(stpfile,'w')
                var_info = boolean_variables({case:1}, exclusive_use_arcs=skeleton)
                variables = var_info.variables
                print "% Total number of variables:", len(variables)
                for i in xrange(0,len(variables),10):
                    print ','.join(variables[i:i+10]),': BITVECTOR(1);'
                generate_structural_stp_inout(singleton_log, var_info)
                print
                print "QUERY (FALSE);"
                print "COUNTEREXAMPLE;"
                sys.stdout = old_stdout
                stpoutput = subprocess.check_output( [stp_solver, stpfile] )
                smt_verified = 'Invalid' in stpoutput
            else:
                print 'Unique case {0} is trivially NON-replayable'.format(case_num)
        else:
            print 'Unique case {0} is trivially replayable'.format(case_num)
        if imm_follows or (possible and smt_verified):
            new_cases[copy.copy(case)] = occ 
    return Log(uniq_cases=new_cases)

#def find_nonfitting_sequences(cn, log):
def nonfitting_cases_in_cn(cn, log):
    """Returns a log with all the non-fitting sequences of the given log."""
    #create a dummy log_info object for each trace, to perform a per-trace
    #simulation
    cases = log.get_uniq_cases()
    t0 = datetime.datetime.now()
    old_stdout = sys.stdout
    stpfile = 'simulate.stp'
    #nonreplay = []
    nonreplay_cases = defaultdict(int)
    #for words, trace_info in log_info.traces.iteritems():
    for case_num, (case, occ) in enumerate(cases.iteritems()):
        print "Checking trace {0}...".format(case_num)
        #useful for debugging
        #stpfile = 'simulate.t{0}.stp'.format(trace_number)
        try:
            sys.stdout = open(stpfile,"w")
        except Exception as ex:
            print("Error. Cannot open file '%s'. %s" % (stpfile, ex))
            quit()
        singleton_log = Log(cases=[case])
        
        var_info = smt_boolean_variables( cn, singleton_log.get_cases() )
        generate_smt_from_cn_and_log( cn, singleton_log, var_info, 
                                        min_unused_bindings=None )
        sys.stdout = old_stdout
        stpoutput = subprocess.check_output( [stp_solver, stpfile] )
        if 'Invalid' in stpoutput:
            print 'Ok'
        else:
            print 'Non-replayable'
            nonreplay_cases[copy.copy(case)] = occ 
            #nonreplay.append((case,occ))
    print 'Total non-replayable distinct cases:', len(nonreplay_cases)
    print 'Total non-replayable cases:', sum(nonreplay_cases.itervalues())
    delta_t = datetime.datetime.now() - t0 
    print "Elapsed time to check all traces:", delta_t.total_seconds(),"s."
    #return nonreplay
    return Log(uniq_cases=nonreplay_cases)

def fitness(cn, log):
    """Returns the fitness of the given log with respect to the C-net [cn]."""
    nonrep = nonfitting_cases_in_cn(cn, log)
    return 1.0-1.0*len(nonrep.get_cases())/len(log.get_cases())

def add_parser_options( parser ):
    """Adds the parser options used by this module to the command line parser"""
#    parser.add_option("--mgo", type="float", dest="max_global_obligations", 
#            help="Maximum number of obligations for all traces, as a fraction of the single obligation C-net (0 is unbounded [default])",
#            default=0)
#    parser.add_option("-i", action="append", nargs=2, dest="explicit_max_input_sets", 
#            help="Maximum number of input sets of given activity in the C-net (format: '-i b 1')", default=[])
#    parser.add_option("--mos", type="int", dest="max_output_sets", 
#            help=("Maximum number of output sets per activity in the C-net "
#                "(0 is unbounded [default]). Requires 'input_output' variable mode"),
#            default=0)
    group = OptionGroup(parser, "Simulation Options", "Options controlling how "
                        "the C-net simulation must be performed.")
    group.add_option("--mub", type="int", dest="min_unused_bindings", 
            help=("Minimum number of unused bindings in the C-net "
                  "(-1 is unbounded [default], 0 is 50% of potential unused bindings)"),
            default=-1)
    group.add_option("--mgo", type="int", dest="max_global_obligations", 
                        help="Maximum number of obligations for all traces (i.e. limits "
                            "the sum of all variables) (0 is unbounded [default])",
                        default=0)
    group.add_option("--sm", "--sim_mode", metavar="MODE", type="choice", 
            dest="simulation_mode",
            choices=["state", "backtrack", "implicit","smt","smt_pt"],
            help=("Determine which Boolean variables to use:\n"
            "state: brute force, compute all the states [default]\n"
            "backtrack: simply check which sequences are feasible, using backtracking to save space\n"
            "implicit: brute force, but using the implicit representation\n"
            "smt: use SMT enconding to obtain one of the possible binding assignments\n"
            "smt_pt: use SMT enconding for each trace"),
            default="state")
    parser.add_option_group( group )
    parser.add_option("--debug", action="store_true", dest="debug", 
            help="Debug mode", default=False)

def main():
    """Main function of this module, called if the module is directly called"""
    parser = OptionParser(usage="%prog [options] cnet log", version="%prog 0.1",
                description=("Simulates a log in the given Cnet using some of "
                        "the available simulation algorithms."))
    add_parser_options( parser )
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.error("incorrect number of arguments. Type -h for help.")
    try:
        cn = Cnet()
        cn.load(args[0])
        logfile = open(args[1])
    except Exception as ex:
        print("Error. Cannot open file '%s'. %s" % (args[1], ex))
        quit()
    log_info = load_log( logfile )
    traces = log_info.traces
    logfile.close()
    seq_ts = build_seq_ts( traces )
    all_distinct_seq = len(traces)
    all_seq = sum([val[1] for val in traces.values()])
    if options.simulation_mode == 'state':
        _, ok_traces, ok_distinct_traces = simulate_ts_state( cn, seq_ts, options )
    elif options.simulation_mode == 'backtrack':
        pass
    elif options.simulation_mode == 'implicit':
        pass
    elif options.simulation_mode == 'smt':
        simulate_smt( cn, log_info, options )
        # dummy values to avoid crashing. SMT will fail if at least one seq. is unfeasible, 
        # thus result is correct if SMT is satisfiable.
        ok_traces = all_seq
        ok_distinct_traces = all_distinct_seq
    elif options.simulation_mode == 'smt_pt':
        nonrep = nonfitting_cases_in_cn( cn, log_info, options )
        ok_traces = all_seq - sum([val[1] for val in nonrep])
        ok_distinct_traces = all_distinct_seq - len(nonrep)
    if options.simulation_mode != 'smt':
        print 'Sequences in the model: {0} Distinct seq. in the model: {1}'.format( ok_traces, ok_distinct_traces )
        print 'Fitness (all seq): {0} Fitness (dist. seq): {1}'.format( ok_traces/(1.0*all_seq), ok_distinct_traces/(1.0*all_distinct_seq) )
    
if __name__ == "__main__":
    main()
