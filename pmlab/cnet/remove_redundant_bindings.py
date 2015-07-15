#! /usr/bin/python
import sys
import os
import subprocess
import datetime
from optparse import OptionParser, OptionGroup
from collections import defaultdict
import simplejson as json

#import cn_stp
import simulate_cnet
#import cnet
import stp_to_cnet
import cn_stp
from .. cnet import stp_solver

def cnet_remove_redundant_bindings_binary_search(cn, log, 
                                                most_freq_bindings=0, 
                                                minimum_fitness=1.0,
                                                use_distinct=False,
                                                compute_bind_freq=None):
    """Returns a cnet in which the maximum number of redundant bindings have 
    been removed.
    [cn] Cnet.
    [log] Log that [cn] must be able to simulate.
    [most_freq_bindings] Keep that number of the most frequent bindings.
    [minimum_fitness] Remove bindings as long as the fitness does not decrease 
        below the given bound.
    [use_distinct] True if we must consider only unique cases in terms of 
        frequency
    [compute_bind_freq] True if we want to get also the binding frequencies as
        return (2nd parameter in a tuple). Note: these are the binding 
        frequencies BEFORE simplification due to [most_freq_binding] or 
        [minimum_fitness]."""
    t0 = datetime.datetime.now()
    cnet_from_stp = stp_to_cnet.build_cnet_from_stp
    activity_positions = log.get_activity_positions()
    logfilename = log.filename if log.filename else 'tmp_log'
    cnetfilename = cn.filename if cn.filename else 'tmpk_cnet'
    old_stdout = sys.stdout
    logprefix, logfileextension = os.path.splitext(logfilename)
    cnetprefix, cnetfileextension = os.path.splitext(cnetfilename)
    iteration = 0
    min_bound = 0
    max_bindings = cn.number_of_bindings()
    max_bound = max_bindings # temporary value to pass while
    print "Original C-net has {0} bindings".format(max_bindings)
    print "Maximizing number of unused bindings"
    last_fine_net = cn
    min_unused_bindings = 0
    while min_bound <= max_bound:
        if iteration == 0:
            stpfile = logprefix+'.simpl.stp'
	    #stpfile = cnetprefix+'.simpl.stp'
            #stpfile = cnetprefix+'.simpl.it{0}.stp'.format(iteration)
            #print "Generating STP file ({0})...".format(stpfile)
            try:
                sys.stdout = open(stpfile,"w")
            except Exception as ex:
                print("Error. Cannot open file '%s'. %s" % (stpfile, ex))
                quit()
            max_bound = simulate_cnet.simulate_smt(cn, log)
            sys.stdout = old_stdout
        print "Bounds: [{0},{1}]".format(min_bound, max_bound)
        avg_bound = (min_bound+max_bound)/2
        print "Testing unused bindings >=",avg_bound
        if avg_bound == 0:
            min_unused_bindings = -1 #since 0 is for default behavior
        else:
            min_unused_bindings = avg_bound
        #stpfile = cnetprefix+'.simpl.it{0}.stp'.format(iteration)
        #stpfile = cnetprefix+'.simpl.stp'
 	stpfile = logprefix+'.simpl.stp'
        print "Generating STP file ({0})...".format(stpfile)
        if iteration > 0:
            try:
                sys.stdout = open(stpfile,"w")
            except Exception as ex:
                print("Error. Cannot open file '%s'. %s" % (stpfile, ex))
                quit()
            simulate_cnet.simulate_smt(cn, log, min_unused_bindings)
        sys.stdout = old_stdout
        #call stp solver
        print "Calling STP solver..."
        t0_solver = datetime.datetime.now()
        stpoutput = subprocess.check_output( [stp_solver, stpfile] )
        delta_t = datetime.datetime.now() - t0_solver 
        print "Solver elapsed time:", delta_t.total_seconds(),"s."
        #print stpoutput
        if 'Invalid' in stpoutput:
            print "Model was feasible"
            if minimum_fitness < 1.0 or max_bindings > 0 or compute_binding_freq:
                net, binding_freq = cnet_from_stp( stpoutput.split("\n"), 
                                                    binding_freq=compute_bind_freq )
            else:
                net = cnet_from_stp( stpoutput.split("\n") )
#            if options.file_output:
#                cn_file = cnetprefix+'.simpl.it{0}.cn'.format(iteration)
#                net.save(cn_file)
#            if options.stp_output or options.all_output:
#            last_stpoutput = stpoutput
            last_binding_freq = binding_freq
            last_fine_net = net
            last_fine_net.stpoutput = stpoutput
            #max_bound = avg_bound # if we do not want the hassle of having to perform the extraction
            print "Number of bindings of found C-net:", net.number_of_bindings()
            unused_bindings = max_bindings - net.number_of_bindings()
            if avg_bound > unused_bindings:
                print "ERROR: equation restricting number of bindings is not working. Found C-net has {0} unused bindings".format(unused_bindings)
                quit()
            min_bound = unused_bindings + 1
        else:
            print "Model was unfeasible"
            max_bound = avg_bound - 1
        iteration += 1
    if minimum_fitness < 1.0 or most_freq_bindings > 0:
        total_traces = max([max(tn) for tn in last_binding_freq[0].values()])+1
        if use_distinct:
            last_fine_net = stp_to_cnet.simplify_net( last_fine_net, 
                                            last_binding_freq, total_traces,
                                            minimum_fitness, most_freq_bindings)
        else:
            #compute trace histogram
            trace_histo = log.get_uniq_cases().values()#[occ for _ in log.get_uniq_cases()]
#            for _, tr_info in log_info.traces.iteritems():
#                trace_histo[tr_info[0]] = tr_info[1]
            last_fine_net = stp_to_cnet.simplify_net( last_fine_net, last_binding_freq, 
                                        total_traces, minimum_fitness, 
                                        most_freq_bindings, trace_histo )
    last_fine_net.print_cnet()
    print "Number of C-net arcs:", last_fine_net.number_of_arcs()
    print "Number of C-net bindings:", last_fine_net.number_of_bindings()
    print "Total number of iterations:", iteration
    delta_t = datetime.datetime.now() - t0 
    print "Elapsed time:", delta_t.total_seconds(),"s."
#    if options.file_output or options.all_output:
#        cn_file = cnetprefix+'.simpl.cn'
#        last_fine_net.save(cn_file)
#        if options.freq_output or options.all_output:
#            with open(cnetprefix+'.simpl.freq','w') as freq_file:
#                #print 'hi!'
#                try:
#                    trace_histo
#                except NameError:
##                    trace_histo = [0 for _ in range(len(log_info.traces))]
##                    for _, tr_info in log_info.traces.iteritems():
##                        trace_histo[tr_info[0]] = tr_info[1]
#                    trace_histo = log.get_uniq_cases().values()
#                save_frequencies( trace_histo, last_binding_freq, freq_file )
#        if options.stp_output or options.all_output:
#            with open(cnetprefix+'.simpl.stpout','w') as stpout_file:
#                stpout_file.write(last_stpoutput)
#    if options.interactive_output:
#        last_fine_net.interactive_output()
    if compute_bind_freq:
        return last_fine_net, last_binding_freq
    return last_fine_net

#if __name__ == '__main__':
#    parser = OptionParser(usage="%prog [options] cnet log",version="%prog 0.1", 
#                        description=("Outputs the C-net obtained by removing "
#                                "the maximum possible number of redundant "
#                                "bindings."))
#    simulate_cnet.add_parser_options( parser )
#    add_parser_options( parser )
#    (options, args) = parser.parse_args()
#    if len(args) != 2:
#        parser.error("incorrect number of arguments. Type -h for help.")
#    cnet_remove_redundant_bindings_binary_search( options, args[0], args[1] )
