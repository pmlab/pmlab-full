#! /usr/bin/python
from collections import defaultdict, Counter
from optparse import OptionParser
import bisect
#import cnet
import re
from .. cnet import Cnet

def binding_seq_from_stp( stpfile ):
    """Returns the set of binding sequences from the stp output."""
    trace = defaultdict(lambda : defaultdict(lambda : (set(),[],[])))
    #maps each trace number to its trace
    # a trace is a map from sequence 
    for line in stpfile:
        words = line.split()
        if len(words) == 5:
            if words[3] == '0b1':
                elements = words[1].split('_')
                if len(elements) != 3:
                    # skip lines that do not conform to this
                    # (sometimes used to skip auxiliary vars )
                    continue
                m = re.search('t(\d+)(x|y)(\d+)',elements[0])
                trace_number = int(m.group(1))
                xy = m.group(2)
                seq_number = int(m.group(3))
                if xy == 'x':
                    trace[trace_number][seq_number][0].add(elements[2])
                    trace[trace_number][seq_number][1].append(elements[1])
                else:
                    trace[trace_number][seq_number][0].add(elements[1])
                    trace[trace_number][seq_number][2].append(elements[2])
                #obligations[elements[0]].append( (elements[1], elements[2]) )
    #print trace
    binding_seq = []
    for i in xrange(len(trace)):
        curr_trace = trace[i]
        bs = []
#        print 'i',i, curr_trace
        for j in xrange(len(curr_trace)):
#            print 'j',j
            #print curr_trace[j], 
            bs.append( (curr_trace[j][0].pop(), set(curr_trace[j][1]), set(curr_trace[j][2])) )
        binding_seq.append( bs )
        #print
    return binding_seq

def binding_frequencies(stpfile, multiset=True):
    """Returns the binding frequencies of the C-net in the STP file (or 
    iterable).
    
    If [multiset] is False, it returns also a tuple of two dictionaries
    (defaultdict(set)) mapping each input/output binding to the trace numbers in
    which they appear.
    
    Otherwise, it returns a tuple of two dictionaries
    (defaultdict(Counter)) mapping each input/output binding to a Counter that 
    maps each trace numbers in which they appear to the number of occurrences of
    that binding in that trace.
    """
    if not multiset:
        freqs = (defaultdict(set), defaultdict(set))
    else:
        freqs = (defaultdict(Counter), defaultdict(Counter))
    obligations = defaultdict(list)
    for line in stpfile:
        words = line.split()
        if len(words) == 5:
            if words[3] == '0b1':
                elements = words[1].split('_')
                if len(elements) != 3:
                    # skip lines that do not conform to this
                    # (sometimes used to skip auxiliary vars )
                    continue
                obligations[elements[0]].append( (elements[1], elements[2]) )
    #print obligations
    for key, obl_list in obligations.iteritems():
        if 'x' in key: #input set
            input_set = frozenset([x[0] for x in obl_list])
            if binding_freq == 'set':
                #extract trace number from key
                freqs[0][(obl_list[0][1], input_set)].add(int(key[1:key.index('x')]))
            elif binding_freq == 'multiset':
                freqs[0][(obl_list[0][1], input_set)][int(key[1:key.index('x')])] += 1
        else:
            output_set = frozenset([x[1] for x in obl_list])
            if not multiset:
                #extract trace number from key
                freqs[1][(obl_list[0][0], output_set)].add(int(key[1:key.index('y')]))
            else:
                freqs[1][(obl_list[0][0], output_set)][int(key[1:key.index('y')])] += 1
    return freqs

def build_cnet_from_stp(stpfile, binding_freq=None):
    """Reads the content of an output STP file and returns a cnet object.
    If [binding_freq] is 'set', it returns also a tuple of two dictionaries 
    (defaultdict(set)) mapping each input/output binding to the trace numbers in
    which they appear.
    If it is 'multiset', then it returns a tuple of two dictionaries 
    (defaultdict(Counter)) mapping each input/output binding to a Counter that 
    maps each trace numbers in which they appear to the number of occurrences of
    that binding in that trace.
    """
    if binding_freq == 'set':
        freqs = (defaultdict(set), defaultdict(set))
    elif binding_freq == 'multiset':
        freqs = (defaultdict(Counter), defaultdict(Counter))
    obligations = defaultdict(list)
    net = Cnet()
    for line in stpfile:
        words = line.split()
        if len(words) == 5:
            if words[3] == '0b1':
                elements = words[1].split('_')
                if len(elements) != 3:
                    # skip lines that do not conform to this
                    # (sometimes used to skip auxiliary vars )
                    continue

                net.add_activity( elements[1] )
                net.add_activity( elements[2] )
                obligations[elements[0]].append( (elements[1], elements[2]) )

    #print obligations
    for key, obl_list in obligations.iteritems():
        if 'x' in key: #input set
            input_set = frozenset([x[0] for x in obl_list])
            net.add_inset( obl_list[0][1], input_set )
            if binding_freq == 'set':
                #extract trace number from key
                freqs[0][(obl_list[0][1], input_set)].add(int(key[1:key.index('x')]))
            elif binding_freq == 'multiset':
                freqs[0][(obl_list[0][1], input_set)][int(key[1:key.index('x')])] += 1
        else:
            output_set = frozenset([x[1] for x in obl_list])
            net.add_outset( obl_list[0][0], output_set )
            if binding_freq == 'set':
                #extract trace number from key
                freqs[1][(obl_list[0][0], output_set)].add(int(key[1:key.index('y')]))
            elif binding_freq == 'multiset':
                freqs[1][(obl_list[0][0], output_set)][int(key[1:key.index('y')])] += 1
    if binding_freq:
        return net, freqs
    return net

def simplify_net( net, binding_freq, total_traces, min_fitness, max_bind, trace_histo=None ):
    """
    Discards bindings until the least fitness over [min_fitness] is obtained, or
    [max_bind] bindings have been saved (ignored if 0 is specified).
    If [trace_histo] is not None, it is expected to be an array containing
    the occurrences of each trace. Otherwise fitness is over distinct traces.
    """
    #greedy approach, start from smallest binding
    #then incorporate always the set wich makes the smaller size increase
    # create a single map
    bf = dict([((0,act,binding), traces) for (act,binding),traces in binding_freq[0].iteritems()] + 
        [((1,act,binding), traces) for (act,binding),traces in binding_freq[1].iteritems()])
    num_bindings = len(bf)
    if max_bind == 0:
        bindings_to_discard = num_bindings
    else:
        bindings_to_discard = num_bindings - max_bind -1
        min_fitness = 0.0
#    print 'Minimum fitness:', min_fitness
#    print 
#    print 'Bindings to discard:', bindings_to_discard
    #print bf
    if trace_histo == None:
        bf_list = sorted(bf.items(), key=lambda x: len(x[1]))
        seed = bf_list[0]
        if len(seed[1])/(1.0*total_traces) > 1.0 - min_fitness:
            return net
    else:
        bf_list = sorted(bf.items(), key=lambda x: sum([trace_histo[i] for i in x[1]]))
        debug_list = [(x, sum([trace_histo[i] for i in x[1]])) for x in bf_list]
#        print trace_histo
        #print debug_list
        total_traces = sum(trace_histo) # change to total (non-distinct) traces
        #decide which is the best option, using the set with equal cost function that appears
        #in more bindings
        candidates = [x for x in debug_list if x[1] == debug_list[0][1]]
        #print 'Candidates:', candidates
        #set traces binding histogram
        binding_histo = defaultdict(int)
        for bind in candidates:
            binding_histo[frozenset(bind[0][1])] += 1
        #print binding_histo
        #seed = bf_list[0]
        seed_traces = sorted(binding_histo.items(), key=lambda x: x[1])[-1][0]
        candidates = [x for x in bf_list if frozenset(x[1])==seed_traces]
        seed = candidates[0]
        #print seed
        if sum([trace_histo[i] for i in seed[1]])/(1.0*total_traces) > 1.0 - min_fitness:
            return net
    
    #print seed
#    print total_traces
#    print len(seed[1])/(1.0*total_traces)
#    print 1.0 - min_fitness
    
    removed_traces = seed[1]
    removed_bindings = [seed[0]]
    while len(removed_bindings) < num_bindings:
        if trace_histo == None:
            delta_sets = sorted([(x[0],x[1]-removed_traces) for x in bf_list if x[0] not in removed_bindings], key=lambda v: len(v[1]))
        else:
            delta_sets = sorted([(x[0],x[1]-removed_traces) for x in bf_list if x[0] not in removed_bindings], key=lambda v: sum([trace_histo[i] for i in v[1]]))
        new_removed = removed_traces | delta_sets[0][1]
        if trace_histo == None:
            if (len(new_removed)/(1.0*total_traces) > 1.0 - min_fitness or 
                (bindings_to_discard <= 0 and len(delta_sets[0][1]) > 0) ):
                break
        else:
            if (sum([trace_histo[i] for i in new_removed])/(1.0*total_traces) > 1.0 - min_fitness or
                (bindings_to_discard <= 0 and len(delta_sets[0][1]) > 0)):
                break
        removed_traces = new_removed
        removed_bindings.append( delta_sets[0][0] )
        bindings_to_discard -= 1
    print "Removed {0} bindings:".format(len(removed_bindings)), removed_bindings
    print "Removed {0} (distinct) traces:".format(len(removed_traces)), removed_traces
    if trace_histo != None:
        print 'Representing {0} traces'.format( sum([trace_histo[i] for i in removed_traces]) )
    cn = cnet.Cnet()
    for act,insets in net.inset.iteritems():
        for ins in insets:
            if (0,act,ins) not in removed_bindings:
                cn.add_activity( act )
                cn.add_inset(act, ins)
    for act,outsets in net.outset.iteritems():
        for outs in outsets:
            if (1,act,outs) not in removed_bindings:
                cn.add_activity( act )
                cn.add_outset(act, outs)
    return cn

if __name__ == "__main__":
    parser = OptionParser(usage="%prog [options] filename",
                        version="%prog 0.2", 
                        description="Builds a C-net out of the output of the STP solver.")
    parser.add_option("--minfit", type='float', dest="minimum_fitness", 
            help=("Simplifies deleting bindings and requiring a minimum amount "
                "of fitting [1 is completely fitting and disabled simplification, default]"),
                default=1.0)
    parser.add_option("--freq", action="store_true", dest="count_freq", 
            help="Print in which traces each binding appears", default=False)
    parser.add_option("--iout", action="store_true", dest="interactive_output", 
            help="Activate the interactive output", default=False)
    parser.add_option("--json", action="store_true", dest="json", 
            help="Print C-net in JSON format", default=False)
    parser.add_option("--prom", action="store_true", dest="newprom", 
                        help="Print C-net in ProM (new) format", default=False)
    parser.add_option("--oldprom", action="store_true", dest="oldprom", 
                        help="Print C-net in ProM (old) format", default=False)
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("incorrect number of arguments. Type -h for help.")
    try:
        stpfile = open(args[0])
    except Exception as ex:
        print("Error. Cannot open file '%s'. %s" % (args[0], ex))
        quit()
    if options.count_freq or options.minimum_fitness < 1.0:
         #= (defaultdict(set),defaultdict(set))
        net, binding_freq = build_cnet_from_stp( stpfile, binding_freq='set' )
        total_traces = max([max(tn) for tn in binding_freq[0].values()])+1
        if options.count_freq:
            print 'Total traces:', total_traces
            print binding_freq[0]
            print binding_freq[1]
        if options.minimum_fitness < 1.0:
            net = simplify_net( net, binding_freq, total_traces, options.minimum_fitness )
    else:
        net = build_cnet_from_stp( stpfile )
    stpfile.close()
    if options.newprom:
        net.print_prom()
    elif options.oldprom:
        net.print_prom( True )
    elif options.interactive_output:
        net.interactive_output()
    elif options.json:
        net.save('-') #to stdout
    else:
        net.print_cnet()