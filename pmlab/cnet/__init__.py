from copy import deepcopy
from collections import defaultdict, Counter, deque
import sys
import simplejson as json

import force_graph

from .. log import Log
from .. log.reencoders import StpReencoder
from .. ts import IndeterminedTsError
#from cnet import Cnet

stp_solver = '/usr/local/bin/stp'

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

def cnet_from_file(filename):
    cn = Cnet()
    cn.load(filename)
    return cn

def condition_log_for_cnet(log):
    """Returns a log that is prepared for cnet analysis (in terms of activity 
    names and unique start and end activities)"""
    orig_alp = list(log.get_alphabet())
    stp_enc = StpReencoder()
    enc_alp = map(stp_enc.reencode, orig_alp)
    same_alphabet = (orig_alp==enc_alp)
    uniq_start = log.has_unique_start_activity()
    uniq_end = log.has_unique_end_activity()
    if (uniq_start and uniq_end and same_alphabet):
        return log
    condl = Log(cases=deepcopy(log.get_cases()))
    if not same_alphabet:
        condl.reencode( stp_enc )
    if not uniq_start:
        condl.add_dummy_start_activity()
    if not uniq_end:
        condl.add_dummy_end_activity()    
    return condl

class Cnet:
    """ Class for a causal net"""
    def __init__(self):
        self.inset = defaultdict(set)
        self.outset = defaultdict(set)
        self.activities = set()
        self.name = "cnet"
        self.filename = None # the filename if loaded or saved to disk 
        self.stpoutput = None # to store the stpoutput that generated this Cnet
    
    def set_name( self, name ):
        """Set the name of the Cnet"""
        self.name = name
        
    def add_activity(self, activity):
        """Add activity to the C-net"""
        self.activities.add( activity )
    
    def add_inset( self, activity, inset ):
        """Add an input set to the activity"""
        if isinstance(inset, frozenset):
            self.inset[activity].add( inset )
        else:
            self.inset[activity].add( frozenset(inset) )
    
    def add_outset( self, activity, outset ):
        """Add an output set to the activity"""
        if isinstance(outset, frozenset):
            self.outset[activity].add( outset )
        else:
            self.outset[activity].add( frozenset(outset) )
    
    def arcs( self ):
        """Returns the arcs of the C-net"""
        arcs = set()
        for act, inset in self.inset.iteritems():
            for ins in inset:
                for in_act in ins:
                    arcs.add((in_act,act))
        return arcs
    
    def number_of_arcs( self ):
        """Returns the number of arcs in the C-net"""
        #print arcs
        return len(self.arcs())
    
    def number_of_bindings( self ):
        """Returns the total number of bindings in the C-net"""
        return (sum([len(ins) for ins in self.inset.values()])+
            sum([len(outs) for outs in self.outset.values()]))
    
    def starting_activities(self):
        """Returns the set of activities with empty input set. In a valid C-net
        this should be a singleton"""
        return [act for act in self.activities if len(self.inset[act]) == 0]
    
    def final_activities(self):
        """Returns the set of activities with empty output set. In a valid C-net
        this should be a singleton"""
        return [act for act in self.activities if len(self.outset[act]) == 0]
    
    def etc_lower_bound(self, tsys, debug=False):
        """For each state in the transition system [tsys], we compute its 
        obligation state. We compute the number of potential outgoing arcs
        from the behavior in [tsys] when considering the Cnet. To alleviate
        state explosion, we do compute the top and bottom elements of each 
        output and input binding sets per activity, respectively. This 
        guarantees that we generate the maximal number of obligations, and 
        consume the least possible ones, thus it is suitable to detect activity
        enabling."""
        start_act = self.starting_activities()
        final_act = self.final_activities()
        divergence_arcs = 0
        s0 = tsys.get_initial_state()
        num_cases = tsys.get_state_frequency(s0) 
        all_arcs = num_cases*len(start_act)
        to_process = deque()
        #preprocess outsets and insets
        top_outset = defaultdict(set)
        bot_inset = defaultdict(set)
        new_bind = 0
        for act, outset in self.outset.iteritems():
            non_top = set([out for out in outset if any([out < S for S in outset])])
            top_outset[act] = outset-non_top
            new_bind += len(top_outset[act])
            if debug and len(non_top) > 0:
                print 'original output bindings for {0}:'.format(act), outset
                print 'non-top bindings for {0}:'.format(act), non_top
        for act, inset in self.inset.iteritems():
            non_bot = set([ins for ins in inset if any([ins > S for S in inset])])
            bot_inset[act] = inset-non_bot
            new_bind += len(bot_inset[act])
            if debug and len(non_bot) > 0:
                print 'original input bindings for {0}:'.format(act), inset
                print 'non-bottom bindings for {0}:'.format(act), non_bot
        if debug:
            print 'Initial bindings:', self.number_of_bindings()
            print 'Bindings after simplification:', new_bind
            print 'Initial activities:', start_act
        for act in start_act:
            #print 'Activity',act,'has no input set'
            target_states = tsys.follow_label(s0,act)#tsys.states[0][1][pos][1]
            if len(target_states) == 0:
                divergence_arcs += num_cases
                if debug:
                    print 'Activity',act,'with empty input set (so it is an initial activity),',
                    print 'has no corresponding arc in transition system'
            elif len(target_states) > 1:
                raise IndeterminedTsError
            else:
                target_state = target_states[0]
                # generate target multiset
                outstate_list = [Counter(dict([((act, outact),1) for outact in outset])) 
                                for outset in top_outset[act]]
                #print outstate_list
                to_process.append((target_state,outstate_list))
                
        while len(to_process) > 0:
            (ts_state,cnet_state) = to_process.popleft()
            num_cases = tsys.get_state_frequency(ts_state)
            #print "Processing:", state, marking
            #find fireable activities
            if debug:
                print 'Simulating at state',ts_state,'with {0} cases:'.format(num_cases), cnet_state
            for act, inset in bot_inset.iteritems():
                outstate_list = []
#                outstate_list = set()
                skip_activity = False
                activity_ok = False
                for ins in inset:
                    #check if this inset is a submultiset of some of the multisets of the cnet state
                    inmultiset = dict([((inact, act),1) for inact in ins])
                    for multiset in cnet_state:
                        if submultiset_set(inmultiset, multiset):
                            remainder_multiset = multiset - Counter(inmultiset)
                            #since we are using an approximated technique (using top's and bottom's)
                            #this is no longer a good approximation to discard the final activity
                            #as we do not know if the empty obligation set is possible
                            #if act in final_act and len(remainder_multiset) > 0: # final activities should leave an empty state
                            #    continue
                            if debug:
                                print "activity", act, "fireable in state", ts_state,
                            if not activity_ok:
                                target_states = tsys.follow_label(ts_state, act)
                                if len(target_states) == 0:
                                    divergence_arcs += num_cases
                                    all_arcs += num_cases
                                    if debug:
                                        print ('Activity',act,'has no '
                                                'corresponding arc in transition'
                                                'system')
                                        print 'Adding', num_cases, 'to all arcs'
                                    skip_activity = True # we do no longer need to compute an unreachable Cnet state
                                    break
                                elif len(target_states) > 1:
                                    raise IndeterminedTsError
                                else:
                                    target_state = target_states[0]
                                    if debug:
                                        print 'to state', target_state
                                    outstate_list += [remainder_multiset+Counter(dict([((act, outact),1) 
                                                    for outact in outset])) for outset in top_outset[act]]
                                    if not activity_ok:
                                        activity_ok = True
                                    all_arcs += num_cases
                                    if debug:
                                        print 'Adding', num_cases, 'to all arcs'
#                                outstate_list |= set([remainder_multiset+Counter(dict([((act, outact),1) 
#                                                    for outact in outset])) for outset in self.outset[act]])
                    if skip_activity:
                        break
                if not skip_activity and activity_ok:
                    # enqueue
                    to_process.append((target_state,outstate_list))
            #print 'to_process:', to_process
        #state = Counter()
        #print "divergence arcs:", divergence_arcs
        #print "all arcs:", all_arcs
        #return states
        return 1-(divergence_arcs/(1.0*all_arcs))
    
    def simple_graph_complexity(self):
        """Returns the 'simple graph complexity' of the C-net"""
        arcs = 0
        for (a,b) in self.arcs():
            arcs_a = [S for S in self.inset[b] if a in S]
            arcs_b = [S for S in self.outset[a] if b in S]
            arcs += len(arcs_a) + len(arcs_b) + 1
        sum_ib_v = 0
        sum_ib_e = 0
        for insets in self.inset.itervalues():
            for S in insets:
                sum_ib_v += len(S)
                sum_ib_e += len(S)-1
        sum_ob_v = 0
        sum_ob_e = 0
        for insets in self.outset.itervalues():
            for S in insets:
                sum_ob_v += len(S)
                sum_ob_e += len(S)-1
#        for S in self.inset.itervalues():
#            print S
        arcs += sum_ib_e + sum_ob_e
#        print 'sum_ib:',sum_ib, 'len(self.inset):', len(self.inset)
#        print 'sum_ob:',sum_ob, 'len(self.outset):', len(self.outset)
        vertices = len(self.activities)+sum_ib_v+sum_ob_v
#        print 'arcs:', arcs, 'vertices:', vertices
        return arcs/(1.0*vertices)
    
    def global_complexity(self):
        """Returns the global complexity: the sum of the number of several
        structural elements"""
        bsizes = 0
        for insets in self.inset.itervalues():
            for S in insets:
                bsizes += len(S)
        for outsets in self.outset.itervalues():
            for S in outsets:
                bsizes += len(S)
        return len(self.activities)+self.number_of_arcs()+self.number_of_bindings()+bsizes
    
    def __add__(self, other):
        """Returns the union of two C-nets"""
        cn = Cnet()
        #map( cn.add_activity, self.activities )
        #map( cn.add_activity, other.activities )
        cn.activities = self.activities | other.activities
        cn.inset = self.inset.copy()
        for act, ins in other.inset.iteritems():
            cn.inset[act] |= ins
        cn.outset = self.outset.copy()
        for act, outs in other.outset.iteritems():
            cn.outset[act] |= outs
        return cn
    
    def save( self, filename, format='json', suffix_act_names=False):
        """Writes the C-net.
        
        [filename] can be either a file or a filename.
        [format] Valid values:
            'json': a human readable format (JSON) that can also be 
                loaded by the load function.
            'prom': planned new ProM format.
            'prom_old': old ProM format used in some intial versions of ProM6.
        [suffix_act_names]: Only for ProM formats. If True, appends '+complete' 
            to the activity names.
        """
        if format not in ('json','prom','prom_old'):
            raise ValueError, 'Unknown format to save the C-net'
        own_fid = False
        if isinstance(filename, basestring): #a filename
            f = open(filename,'w')
            self.filename = filename
            own_fid = True
        else:
            f = filename
            self.filename = file.name
        if format=='json':
            list_inputs = {}
            for act, inset in self.inset.iteritems():
                list_inputs[act] = [list(ins) for ins in inset]
            list_outputs = {}
            for act, outset in self.outset.iteritems():
                list_outputs[act] = [list(outs) for outs in outset]
            info = {'input_sets': list_inputs, 'output_sets': list_outputs, 
                    'stpoutput': self.stpoutput}
            json.dump( info, f, indent=" ")
        elif format in ('prom','prom_old'):
            old_format = (format == 'prom_old')
            wr = f.write
            wr('<?xml version="1.0" encoding="UTF-8"?><cnet>')
            wr('<net type="http://www.processmining.org" id="Causal net" />')
            wr("<name>"+self.name+"</name>")
            act_id = {}
            for act in self.activities:
                act_id[ act ] = len( act_id )
                if suffix_act_names:
                    act_name = act+'+complete'
                else:
                    act_name = act
                if old_format:
                    wr('<node id="{0}" isInvisible="false"><name>{1}</name></node>'.format( act_id[act], act_name ))
                else:
                    wr('<node id="{0}"><name>{1}</name></node>'.format( act_id[act], act_name ))
            start_act = [act for act in self.activities if len(self.inset[act]) == 0]
            if len(start_act) == 0:
                print "Error: no start activity!"
            elif len(start_act) > 1:
                print "Error: more than one starting activity,", start_act
            else:
                wr('<startTaskNode id="{0}"/>'.format( act_id[ start_act[0] ] ))
            end_act = [act for act in self.activities if len(self.outset[act]) == 0]
            if len(end_act) == 0:
                print "Error: no ending activity!"
            elif len(end_act) > 1:
                print "Error: more than one ending activity,", end_act
            else:
                wr('<endTaskNode id="{0}"/>'.format( act_id[ end_act[0] ] ))
            arcs = []
            for act, inset in self.inset.iteritems():
                if len(inset) == 0:
                    continue
                wr('<inputNode id="{0}">'.format( act_id[act] ))
                for ins in inset:
                    wr('<inputSet>')
                    for in_act in ins:
                        arcs.append((in_act,act))
                        wr('<node id="{0}"/>'.format( act_id[ in_act ] ))
                    wr('</inputSet>')
                wr('</inputNode>')
            for act, outset in self.outset.iteritems():
                if len(outset) == 0:
                    continue
                wr('<outputNode id="{0}">'.format( act_id[act] ))
                for outs in outset:
                    wr('<outputSet>')
                    for out_act in outs:
                        wr('<node id="{0}"/>'.format( act_id[ out_act ] ))
                    wr('</outputSet>')
                wr('</outputNode>')
            if old_format:
                # print redundant arc information
                i = len(self.activities)
                for arc in arcs:
                    wr('<arc id="{0}" source="{1}" target="{2}"/>'.format( i, act_id[arc[0]], act_id[arc[1]]))
                    i += 1
            wr("</cnet>")
        if own_fid:
            f.close()
        
    def load( self, filename ):
        """Loads the C-net stored in filename. The format is human readable 
        (JSON), so that it can be generated also by humans. Contains input
        sets and output sets. The list of activities is inferred from
        that information."""
        try:
            f = open(filename)
        except IOError as (errno, strerror):
            print "I/O error({0}): {1}".format(errno, strerror)
            return
        info = json.load( f )
        for act, inset in info['input_sets'].iteritems():
            for ins in inset:
                self.add_inset( act, ins )
        for act, outset in info['output_sets'].iteritems():
            for outs in outset:
                self.add_outset( act, outs )
        self.activities = set(self.inset.keys() + self.outset.keys())
        if 'stpoutput' in info:
            self.stpoutput = info['stpoutput']
        self.filename = filename
        
    def print_cnet(self):
        """Print the C-net to stdout"""
        print "Activities:", sorted(list(self.activities))
        print "Insets:"
        for act, inset in self.inset.iteritems():
            printable_inset = [sorted(list(ins)) for ins in inset] 
            print "For", act, ":", printable_inset
#            for ins in inset:
#                pprint.pprint(list(ins))
        print "Outsets:"
        for act, outset in self.outset.iteritems():
            printable_outset = [sorted(list(outs)) for outs in outset] 
            print "For", act, ":", printable_outset
    
    def draw(self):
        s = force_graph.ForceDirectedGraph( self.activities, self.inset, self.outset )
        s.run()


def immediately_follows_cnet_from_raw( filename ):
    """Returns the immediately follows Cnet from the log in [filename].
    
    [filename] can either be a file or a filename."""
    own_fid = False
    if isinstance(filename, basestring):
        file = open( filename )
        own_fid = True
    else:
        file = filename
    cnet = Cnet()
    for line in file:
        activities = line.split()
        prev = None
        for act in activities:
            cnet.add_activity( act )
            if prev is not None:
                cnet.add_outset( prev, [act] )
                cnet.add_inset( act, [prev] )
            prev = act
    if own_fid:
        file.close()
    return cnet

def immediately_follows_cnet_from_log( log ):
    """Returns the immediately follows Cnet from the log [log]."""
    cnet = Cnet()
    cases = log.get_uniq_cases()
    for case in cases:
        prev = None
        for act in case:
            cnet.add_activity( act )
            if prev is not None:
                cnet.add_outset( prev, [act] )
                cnet.add_inset( act, [prev] )
            prev = act
    return cnet

def arc_similarity(cnets, verbose=False):
    """Returns the arc similarity metric between the set/list of cnets in 
    [cnets].
    
    The arc similarity is defined as the set of shared arcs divided by the
    set of all arcs."""
    arcs = [cn.arcs() for cn in cnets]
    common_arcs = set.intersection( *arcs )
    all_arcs = set.union( *arcs )
    similarity = len(common_arcs) / (1.0*len(all_arcs))
    if verbose:
        for i,s in enumerate(arcs):
            print 'Arcs of Cnet {0}: {1}'.format(i, len(s))
        print 'Common arcs:', len(common_arcs)
        print 'All arcs:', len(all_arcs)
        print "Arc similarity:", similarity
    return similarity

def binding_similarity(cnets, verbose = False):
    """Returns the input/output binding similarity metric between the set/list 
    of cnets in [cnets].
    
    The binding similarity is defined as the set of shared bindings divided by 
    the set of all bindings."""
    insets = [cn.inset for cn in cnets]
    in_similarities = []
    alphabet = set.union( *[set(ins.keys()) for ins in insets] )
    for act in alphabet:
        ins_act = [ins[act] for ins in insets]
        common_in = set.intersection(*ins_act)
        all_in = set.union( *ins_act )
        similarity = len(common_in) / (1.0*len(all_in))
        in_similarities.append( similarity )
        if verbose:
            for i,s in enumerate(ins_act):
                print 'Input bindings for activity {0} in Cnet {1}: {2}'.format(act, i, len(s))
            print 'Common bindings:', len(common_in)
            print 'All bindings:', len(all_in)
    if verbose:
        print 'Average input binding similarity: {0}'.format(sum(in_similarities)/len(in_similarities))
    outsets = [cn.outset for cn in cnets]
    out_similarities = []
    alphabet = set.union( *[set(outs.keys()) for outs in outsets] )
    for act in alphabet:
        outs_act = [outs[act] for outs in outsets]
        common_out = set.intersection(*outs_act)
        all_out = set.union( *outs_act )
        similarity = len(common_out) / (1.0*len(all_out))
        out_similarities.append( similarity )
        if verbose:
            for i,s in enumerate(outs_act):
                print 'Output bindings for activity {0} in Cnet {1}: {2}'.format(act, i, len(s))
            print 'Common bindings:', len(common_out)
            print 'All bindings:', len(all_out)
    if verbose:
        print 'Average output binding similarity: {0}'.format(sum(out_similarities)/len(out_similarities))
    all_similarities = in_similarities + out_similarities
    iobs = sum(all_similarities)/len(all_similarities)
    if verbose:
        print 'Average input/output binding similarity: {0}'.format(iobs)
    return iobs

def save_frequencies(last_binding_freq, freq_file):
    """Saves frequency information in a [freq_file] using JSON format.
    
    [freq_file] can be either a file or a filename.
    The frequency information is the list of distinct traces using
    each binding (a duple: first the input bindings, then the output)"""
    own_fid = False
    if isinstance(freq_file, basestring):
        file = open(freq_file, 'w')
        own_fid = True
    else:
        file = freq_file
    json_binding_freq = [[(k[0],tuple(k[1]),list(v)) for k,v in fmp.iteritems()] for fmp in last_binding_freq]
    #print json_binding_freq
    json.dump(json_binding_freq, file)
    if own_fid:
        file.close()
    #print json.dumps(trace_histo)
    #json.dump(trace_histo, freq_file)

def load_frequencies( freq_file ):
    """Loads frequency information stored in a [freq_file] using JSON format.
    
    Returns the frequency information: the list of distinct traces using
    each binding (a duple: first the input bindings, then the output)
    [freq_file] can be either a file or a filename.
    """
    own_fid = False
    if isinstance(freq_file, basestring):
        file = open(freq_file)
        own_fid = True
    else:
        file = freq_file
    ret = json.load( file )
    if own_fid:
        file.close()
    return [{(a,frozenset(s)):v for a,s,v in fmp} for fmp in ret]

def cnet_from_log(log, method='stp', activity_window=1, skeleton=None,
                    remove_redundant_bindings=True,
                    compute_binding_freq='multiset'):
    """Returns a Cnet with minimum number of arcs whose language contains the 
    log.
    
    [method] Valid values are:
        'stp': SMT solver (STP)
        'pb': pseudo-boolean solver (TODO)
        'lp': LP solver (lp_solve) (TODO)
    [activity_window] size of the activity window. 0 deactivates the window.
    [skeleton] list of 2-tuples indicating the allowed arcs in the C-net. This
        option is compatible with [activity_window], although usually the
        activity window is deactivated while using a skeleton.
    [remove_redundant_bindings] If True, then redundant bindings are removed 
        after the number of arcs is minimized.
    [compute_binding_freq] If 'set' or 'multiset', the binding frequencies are 
    computed and returned (as 2nd object of return tuple). The difference 
    between 'set' and 'multiset' is that the former only tells in which cases
    every binding appears, while the latter also contains how many occurrences
    of the binding appear in each case. Use None to avoid returning any 
    frequency.
    """
    import iter_structural_cnet as isc
    import stp_to_cnet as stc
    min_arcs_cnet = isc.cnet_binary_search
    if method=='stp':    
        b_freq = compute_binding_freq and not remove_redundant_bindings
        net = min_arcs_cnet(log, activity_window=activity_window,
                            exclusive_use_arcs=skeleton)
        if b_freq:
            bind_freq = stc.binding_frequencies(net.stpoutput.split('\n'),
                                                compute_binding_freq)
    else:
        raise TypeError, 'Unknown discovery method for Cnet: '+method
    if remove_redundant_bindings:
        import remove_redundant_bindings as rdb
        remove_redundant_bind = rdb.cnet_remove_redundant_bindings_binary_search
        if compute_binding_freq:
            net, bind_freq = remove_redundant_bind(net, log, 
                                                    compute_bind_freq=compute_binding_freq)
        else:
            net = remove_redundant_bind(net, log)
    if compute_binding_freq:
        return net, bind_freq
    return net

def flexible_heuristic_miner(log, l1loop=0.9, l2loop=0.9, gen_th=0.9):
    """Computes the C-net using the FHM strategy of :
    Flexible Heuristics Miner (FHM)
    A.J.M.M. Weijters, J.T.S. Ribeiro
    Beta Working Paper series 334
    """
    directsucc = defaultdict(int)
    twoloop = defaultdict(int)
    succ = defaultdict(int)
    alph = list(log.get_alphabet())
    cases = log.get_uniq_cases()
    for case, occ in cases.iteritems():
        for i, act in enumerate(case[:-1]):
            directsucc[(act,case[i+1])] += occ
            if i < len(case)-2 and case[i+2]==act:
                twoloop[(act,case[i+1])] += occ
            for act2 in case[i+1:]:
                succ[(act,act2)] += occ
    print 'direct succ:', directsucc
    print 'two length loop:', twoloop
    print 'succ:', succ
    deprel = {}
    l2l = {}
    for act1 in alph:
        for act2 in alph:
            if act1 != act2:
                deprel[(act1,act2)] = ((directsucc[(act1,act2)]-directsucc[(act2,act1)])/
                        (1.0*directsucc[(act1,act2)]+directsucc[(act2,act1)]+1))
                l2l[(act1,act2)] = ((twoloop[(act1,act2)]+twoloop[(act2,act1)])/
                        (1.0*twoloop[(act1,act2)]+twoloop[(act2,act1)]+1))
            else:
                deprel[(act1,act2)] = 1.0*directsucc[(act1,act2)]/(directsucc[(act1,act2)]+1)
    print 'deprel:', deprel
    dr_th = 0.9
    selected_deprel = [rel for rel, freq in deprel.iteritems() if 
        rel[0]==rel[1] and freq >= l1loop or
        rel[0]!=rel[1] and freq >= gen_th]
    print 'relevant relation:', selected_deprel
    return selected_deprel

