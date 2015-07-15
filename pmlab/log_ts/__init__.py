from .. log import Log
from .. ts import TransitionSystem, IndeterminedTsError

def cases_included_in_ts(log, ts, uniq_cases=False):
    """Returns a log containing only the cases (and parts of cases) that fit 
    in the TS. Prints information on how the cases of a log can be reproduced by
    a TS or not.
    
    [uniq_cases] If True, consider only unique cases."""
    partially_included=0
    totally_included=0
    excluded_traces=0
    ratio=0
    s0 = ts.get_state(ts.get_initial_state())
    cases = log.get_uniq_cases() if uniq_cases else log.get_cases()
    saved_cases = {}
    for (case, occ) in log.get_uniq_cases().iteritems():
        s = s0
        if uniq_cases:
            occ = 1
        i = 0
        for i, activity in enumerate(case):
            #compute destination state
            edges = [e for e in s.out_edges() 
                    if ts.ep_edge_label[e] == activity]
            if len(edges) == 0:
                break
            if len(edges) > 1:
                raise IndeterminedTsError, "Ambiguous TS!"
            s = edges[0].target()
            i += 1
        if i == 0:
            excluded_traces += occ
        elif i == len(case):
            totally_included += occ
        else:
            ratio += i/((1.0)*len(case))*occ
            partially_included += occ
        if i != 0:
            saved_cases[tuple(case[:i])] = occ
    num_cases = len(cases)
    width=len(str(num_cases))
    print "Total cases in log:  {0:{width}}".format(num_cases, width=width)
    print "Excluded:            {0:{width}} {1:7.2%}".format(excluded_traces, 
                                                            excluded_traces / (1.0*num_cases),
                                                            width=width )
    print "Partially Included:  {0:{width}} {1:7.2%}".format(partially_included, 
                                                partially_included / (1.0*num_cases),
                                                width=width),
    if partially_included:
        print "average included length {0:5.2%}".format(ratio/(1.0*partially_included))
    else:
        print
    print "Totally Included:    {0:{width}} {1:7.2%}".format(totally_included, 
                                                            totally_included / (1.0*num_cases),
                                                            width=width )
    return Log(uniq_cases=saved_cases)
