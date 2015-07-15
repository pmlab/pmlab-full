from collections import deque
from random import randint

from .. log import Log

def simulate( pn, method='rnd', num_cases=100, length=10):
    """Simulates [cases] cases of [length] length of the PN [pn] using the 
    simulation method [method]. Valid value for [method]: rnd, bfs.
    Returns a log containing the cases."""
    cases = []
    if method == 'rnd':
        for i in xrange(num_cases):
            pn.to_initial_marking()
            case = pn.simulate(length)
            cases.append(case)
    elif method == 'bfs':
        for i in xrange(num_cases):
            pn.to_initial_marking()
            case = simulateBFS(pn, length)
            cases.append(case)
    else:
        raise TypeError, 'Unknown simulation method'
    return Log(cases=cases)
 
def simulateBFS(pn, length, names=True):
    seq = []
    enabled_transition_list = deque()
    enabled_transition_set = set()
    for i in range(length):
        enabled_transitions = pn.enabled_transitions(names=False)
        new_enabled_transitions = set(enabled_transitions) - enabled_transition_set
        disabled_transitions = enabled_transition_set - set(enabled_transitions)
        enabled_transition_set -= disabled_transitions
        for d in disabled_transitions:
            for evset in enabled_transition_list:
                if d in evset:
                    evset.remove(d)
        if len(new_enabled_transitions) > 0:
            enabled_transition_list.append( list(new_enabled_transitions) )
            enabled_transition_set |= new_enabled_transitions
        while len(enabled_transition_list) > 0 and len(enabled_transition_list[0]) == 0:
            enabled_transition_list.popleft()
        #print "new enabled transitions: ", new_enabled_transitions
        #print "enabled transition queue:", enabled_transition_list
        if len(enabled_transition_list) == 0:
            break 
        selected = randint(0,len(enabled_transition_list[0])-1)
        t = enabled_transition_list[0][selected]
        pn.fire_transition(t)
        enabled_transition_set.remove(t)        
        if names:
            seq.append(pn.vp_elem_name[t])
        else:
            seq.append(t)
        enabled_transition_list[0].pop(selected)        
    return seq