#! /usr/bin/python
import sys
import os
import subprocess
import datetime
from optparse import OptionParser
from .. pn import PetriNet

import pn_stp
import stp_to_pn

#stp_solver = '../stp/bin/stp'
stp_solver = '/usr/local/bin/stp'

#def add_parser_options( parser ):
#    parser.add_option("--fout", action="store_true", dest="file_output", 
#            help="Write Petri net output file (using TS filename with extension '.pnminer.g')", 
#            default=False)
#    #parser.add_option("--iout", action="store_true", dest="interactive_output", 
#    #        help="Activate the interactive output", default=False)
#    parser.add_option("--subset", action="store_true", dest="subset_method", 
#            help="Use subset method, instead of sum of multiplicity reduction", 
#            default=False)
#    parser.add_option("--ubound", type='int', dest="upper_bound", 
#            help="Overwrite manually upper bound in binary search [-1 is autobound, default]", default=-1)

#def min_region_binary_search( ts, options ):
#    t0 = datetime.datetime.now()
#    if options.debug:
#        ts.print_ts()
#    variables = pn_stp.boolean_variables( ts, options )
#    #pn_stp.generate_stp_from_ts( ts, variables, options )
#    old_stdout = sys.stdout
#    tsprefix, tsfileextension = os.path.splitext(ts.filename)    
#    places = []
#    min_bound = 1 #min bound is never reset, since we discover regions in order
#    while True:
#        place = None
#        iteration = 0
#        max_bound = (len(ts.states)-1)*options.k
#        if options.upper_bound >= 0:
#            max_bound = min(max_bound, options.upper_bound)
#            print 'Setting manually upper bound to', max_bound
#        print "Reducing total multiplicity"
#        t1 = datetime.datetime.now()
#        while min_bound <= max_bound:
#            print "Bounds: [{0},{1}]".format(min_bound, max_bound)
#            avg_bound = (min_bound+max_bound)/2
#            print "Testing total multiplicity =",avg_bound
#            options.max_multiplicity = avg_bound
#            stpfile = tsprefix+'.it{0}.stp'.format(iteration)
#            print "Generating STP file ({0})...".format(stpfile)
#            try:
#                sys.stdout = open(stpfile,"w")
#            except Exception as ex:
#                print("Error. Cannot open file '%s'. %s" % (stpfile, ex))
#                quit()
#            pn_stp.generate_stp_from_ts( ts, variables, options, places )
#            sys.stdout = old_stdout
#            #call stp solver
#            print "Calling STP solver..."
#            t0_solver = datetime.datetime.now()
#            stpoutput = subprocess.check_output( [stp_solver, stpfile] )
#            delta_t = datetime.datetime.now() - t0_solver 
#            print "Solver elapsed time:", delta_t.total_seconds(),"s."
#            #print stpoutput
#            if 'Invalid' in stpoutput:
#                place = stp_to_pn.build_place_from_stp( stpoutput.split("\n") )
#                print place
#    #            if options.file_output:
#    #                cn_file = logprefix+'.it{0}.cn'.format(iteration)
#    #                net.save(cn_file)
#    #            last_fine_net = net
#                #max_bound = avg_bound # if we do not want the hassle of having to perform the extraction
#                if avg_bound > place.total_multiplicity:
#                    print "Total multiplicity of found place:", place.total_multiplicity
#                if avg_bound < place.total_multiplicity:
#                    print "ERROR: equation restricting multiplicity is not working. Found place has {0} multiplicity".format(place.total_multiplicity)
#                    quit()
#                max_bound = place.total_multiplicity - 1
#            else:
#                print "Model was unfeasible"
#                min_bound = avg_bound + 1
#            iteration += 1
#    #    last_fine_net.print_cnet()
#        if place == None:
#            break
#        print place
#        places.append( place )
#    #    print "Number of C-net arcs:", last_fine_net.number_of_arcs()
#        print "Total number of iterations:", iteration
#        delta_t = datetime.datetime.now() - t1 
#        print "Elapsed time for this place:", delta_t.total_seconds(),"s."
#    delta_t = datetime.datetime.now() - t0 
#    print "Total elapsed time:", delta_t.total_seconds(),"s."
##    if options.file_output:
##        cn_file = logprefix+'.cn'
##        net.save(cn_file)
##    if options.interactive_output:
##        last_fine_net.interactive_output()
##    return last_fine_net
#    return places

def min_region_subset_binary_search( ts, k ):
    t0 = datetime.datetime.now()
#    if options.debug:
#        ts.print_ts()
    variables = pn_stp.boolean_variables( ts )
    #pn_stp.generate_stp_from_ts( ts, variables, options )
    old_stdout = sys.stdout
    tsprefix, tsfileextension = os.path.splitext(ts.filename)
    places = []
    place = stp_to_pn.Place()
    place.multiplicity = dict([(st,k) for st in ts.get_state_names()])
    place.total_multiplicity = ts.number_of_states()*k
    explored = [place]
    while len(explored) > 0:
        place = explored[-1]
        iteration = 0
        print "Searching for subset region"
        t1 = datetime.datetime.now()
        new_place_generated = False
        while True:
#            print "Bounds: [{0},{1}]".format(min_bound, max_bound)
#            avg_bound = (min_bound+max_bound)/2
#            print "Testing total multiplicity =",avg_bound
#            options.max_multiplicity = avg_bound
            stpfile = tsprefix+'.it{0}.stp'.format(iteration)
            print "Generating STP file ({0})...".format(stpfile)
            try:
                sys.stdout = open(stpfile,"w")
            except Exception as ex:
                print("Error. Cannot open file '%s'. %s" % (stpfile, ex))
                quit()
            pn_stp.generate_stp_from_ts( ts, variables, k, 
                                        place_list=places, 
                                        subset_place=place )
            sys.stdout = old_stdout
            #call stp solver
            print "Calling STP solver..."
            t0_solver = datetime.datetime.now()
            stpoutput = subprocess.check_output( [stp_solver, stpfile] )
            delta_t = datetime.datetime.now() - t0_solver 
            print "Solver elapsed time:", delta_t.total_seconds(),"s."
            #print stpoutput
            if 'Invalid' in stpoutput:
                place = stp_to_pn.build_place_from_stp( stpoutput.split("\n") )
                print place
                explored.append(place)
                new_place_generated = True
            else:
                print "Model was unfeasible"
                break
            iteration += 1
        explored.pop()
        if len(explored) == 0:
            break
        if new_place_generated:
            print place
            places.append( place )
        print "Total number of iterations:", iteration
        delta_t = datetime.datetime.now() - t1 
        print "Elapsed time for this place:", delta_t.total_seconds(),"s."
    delta_t = datetime.datetime.now() - t0 
    print "Total elapsed time:", delta_t.total_seconds(),"s."
    return places

def pn_from_ts(ts, k=1):
    places = min_region_subset_binary_search( ts, k )
    #build pn from places
    pn = PetriNet()
    activities = reduce(set.union,[set(p.pos_gradient)|set(p.neg_gradient) for p in places])
    for act in activities:
        pn.add_transition(act)
    for i,place in enumerate(places):
        p = pn.add_place('p{0}'.format(i))
        for ev,grad in place.neg_gradient.iteritems():
            if grad > 0:
                pn.add_edge(p, ev, grad)
        for ev,grad in place.pos_gradient.iteritems():
            if grad > 0:
                pn.add_edge(ev, p, grad)
        #print 'TS initial state:', ts.initial_state
        pn.set_initial_marking(p,place.multiplicity[ts.get_initial_state()])
    return pn

if __name__ == '__main__':
    parser = OptionParser(usage="%prog [options] filename",version="%prog 0.1", 
                        description=("Outputs the C-net found from just encoding the log structural restrictions "
                                "(without forbidden arcs) and performing a binary search to minimize the "
                                "number of arcs."))
    pn_stp.add_parser_options( parser )
    add_parser_options( parser )
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("incorrect number of arguments. Type -h for help.")
    ts = pn_stp.TransitionSystem()
    try:
        ts.read_from_file(args[0])
    except Exception as ex:
        print("Error. Cannot open file '%s'. %s" % (args[0], ex))
        quit()
    tsprefix, tsfileextension = os.path.splitext(ts.filename)
    if options.subset_method:
        places = min_region_subset_binary_search( ts, options )
    else:
        places = min_region_binary_search( ts, options )
    if options.file_output:
        pnfilename = tsprefix+'.pnminer.g'
        pnfile = open(pnfilename,'w')
        print "Writing PN to file '{0}'".format(pnfilename)
        activities = reduce(set.union,[set(p.pos_gradient)|set(p.neg_gradient) for p in places])
        print >> pnfile, '.model minedPN'
        print >> pnfile, '.outputs '+' '.join(activities)
        print >> pnfile, '.graph'
        arcs = 0
        for i,p in enumerate(places):
            for ev,grad in p.neg_gradient.iteritems():
                if grad > 0:
                    arcs += 1
                    print >> pnfile, 'p{0}'.format(i), ev, '({0})'.format(grad) if grad > 1 else ''
            for ev,grad in p.pos_gradient.iteritems():
                if grad > 0:
                    arcs += 1
                    print >> pnfile, ev, 'p{0}'.format(i), '({0})'.format(grad) if grad > 1 else ''
        #print 'TS initial state:', ts.initial_state
        print >> pnfile, '.marking {'+' '.join(['p{0}={1}'.format(i,p.multiplicity[ts.initial_state]) 
                                                                for i,p in enumerate(places)
                                                                if p.multiplicity[ts.initial_state] > 0])+'}'
        print >> pnfile, '.end'
        print >> pnfile, '#places: {0}, transitions: {1}, arcs: {2}'.format(len(places), 
                                                                        len(activities),
                                                                        arcs)
    else:    
        for p in places:
            print p
        