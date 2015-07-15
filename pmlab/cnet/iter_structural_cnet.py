#! /usr/bin/python
import sys
import os
import subprocess
import datetime
from optparse import OptionParser

#added by josep
import string 
import random

import cn_stp
#import cnet
import stp_to_cnet
from .. cnet import immediately_follows_cnet_from_log, stp_solver

#stp_solver = '../stp/bin/stp'


#def add_parser_options( parser ):
#    parser.add_option("--fout", action="store_true", dest="file_output", 
#            help="Write C-net output file (using log filename with extension '.cn'), as well as intermediate successful nets", 
#            default=False)
#    parser.add_option("--iout", action="store_true", dest="interactive_output", 
#            help="Activate the interactive output", default=False)
#    parser.add_option("--ubound", type='int', dest="upper_bound", 
#            help="Overwrite manually upper bound in binary search [-1 is autobound, default]", default=-1)

def cnet_binary_search( log,  
                    activity_window=0, exclusive_use_arcs=None,
                    ignored_arcs=None, add_ignored_arcs_to_window=True, 
                    upper_bound=-1,randomized_names=True):
    """Finds a C-net for the log [log] using a binary search strategy than
    minimizes the number of arcs. The C-net returned contains a new field
    stpoutput that can be used to derive frequency information, bindings
    sequence, etc.
    [activity_window] Consider for obligation only the n activities around each 
    activity. To consider them all use value 0 (default).
    [exclusive_use_arcs] List of exclusive obligations that can be used.
    [ignored_arcs] List of obligations not considered for arc minimization.
    [upper_bound] Upper bound of binary search, used to override default which 
    is the number of arcs in the immediately follows C-net for [log]."""
    t0 = datetime.datetime.now()
    traces = log.get_uniq_cases()
    activity_positions = log.get_activity_positions()
    logfilename = log.filename if log.filename else 'tmp'
    if (randomized_names):
        sr = [random.choice(string.ascii_letters + string.digits) for n in xrange(5)]
        logfilename = logfilename.join(sr) 
    var_info = cn_stp.boolean_variables(traces, activity_window,
                                        exclusive_use_arcs,
                                        ignored_arcs,
                                        add_ignored_arcs_to_window)
    net = immediately_follows_cnet_from_log(log)
    old_stdout = sys.stdout
    logprefix, logfileextension = os.path.splitext(logfilename)
    iteration = 0
    if not ignored_arcs:   
        max_bound = net.number_of_arcs()-1
        #new lower bound
        start_activities = set([words[1] for words in traces if len(words) > 1])
        end_activities = set([words[-2] for words in traces if len(words) > 1])
        #print end_activities
        new_min_bound = (len(start_activities) + len(end_activities) + 
                        len(net.activities - 
                        (start_activities | end_activities)) -
                        2 + max(len(start_activities - end_activities), 
                                len(end_activities - start_activities )))
        print "General connectivity min bound:", len(net.activities),"New min bound:",new_min_bound
        min_bound = max(len(net.activities), new_min_bound)
    else:
        ignored_alphabet = set([x[0] for x in ignored_arcs]) | set([x[1] for x in ignored_arcs])
        #compute new activities in log to derive lower bound
        new_alphabet = log.get_alphabet() - ignored_alphabet
        max_bound = len(net.arcs() - set(ignored_arcs))-1
        if len(new_alphabet) == 0:
            min_bound = 0
        else:
            min_bound = len(new_alphabet)+1
        #min_bound = 0
        #since the start and final activities cannot belong to the new activities
        print 'Some arcs are ignored, setting a conservative lower bound of {0}'.format(min_bound)
    if upper_bound >= 0:
        max_bound = min(max_bound, upper_bound)
        print 'Setting manually upper bound to', max_bound
    print "Reducing number of arcs"
    last_fine_net = net
    while min_bound <= max_bound:
        print "Bounds: [{0},{1}]".format(min_bound, max_bound)
        avg_bound = (min_bound+max_bound)/2
        print "Testing arcs =",avg_bound
        max_global_arcs = avg_bound
        stpfile = logprefix+'.it{0}.stp'.format(iteration)
	print stpfile
        print "Generating STP file ({0})...".format(stpfile)
        try:
            sys.stdout = open(stpfile,"w")
        except Exception as ex:
            print("Error. Cannot open file '%s'. %s" % (stpfile, ex))
            quit()
        cn_stp.generate_stp_from_log( log, var_info, 
                                        max_global_arcs=max_global_arcs )
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
            net = stp_to_cnet.build_cnet_from_stp( stpoutput.split("\n") )
#            if options.file_output:
#                cn_file = logprefix+'.it{0}.cn'.format(iteration)
#                net.save(cn_file)
            last_fine_net = net
            last_fine_net.stpoutput = stpoutput
            #max_bound = avg_bound # if we do not want the hassle of having to perform the extraction
            if avg_bound > net.number_of_arcs():
                print "Number of arcs of found C-net:", net.number_of_arcs()
            if not ignored_arcs:
                if avg_bound < net.number_of_arcs():
                    print "ERROR: equation restricting number of arcs is not working. Found C-net has {0} arcs".format(net.number_of_arcs())
                    quit()
                max_bound = net.number_of_arcs() - 1
            else:
#                print "found arcs ({0}):".format(len(net.arcs())), net.arcs()
#                print "ignored arcs ({0}):".format(len(options.ignore_arcs)), set(options.ignore_arcs)
#                print "bounded arcs ({0}):".format(len(net.arcs() - set(options.ignore_arcs))), net.arcs() - set(options.ignore_arcs)
                max_bound = len(net.arcs() - set(ignored_arcs)) - 1
#                print "new max bound:", max_bound
            #last_fine_stpoutput = stpoutput
        else:
            print "Model was unfeasible"
            min_bound = avg_bound + 1
        iteration += 1
    last_fine_net.print_cnet()
    print "Number of C-net arcs:", last_fine_net.number_of_arcs()
    print "Total number of iterations:", iteration
    delta_t = datetime.datetime.now() - t0 
    print "Elapsed time:", delta_t.total_seconds(),"s."
#    if options.file_output:
#        cn_file = logprefix+'.cn'
#        net.save(cn_file)
#    if options.interactive_output:
#        last_fine_net.interactive_output()
    return last_fine_net

#if __name__ == '__main__':
#    parser = OptionParser(usage="%prog [options] filename",version="%prog 0.1", 
#                        description=("Outputs the C-net found from just encoding the log structural restrictions "
#                                "(without forbidden arcs) and performing a binary search to minimize the "
#                                "number of arcs."))
#    cn_stp.add_parser_options( parser )
#    add_parser_options( parser )
#    (options, args) = parser.parse_args()
#    if len(args) != 1:
#        parser.error("incorrect number of arguments. Type -h for help.")
#    cnet_binary_search( options, args[0] )
