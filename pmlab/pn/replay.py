import numpy as np
from .. log import Log

class UnfitLogError(Exception):
    """This error is raised whenever there is a log that does not fit the model"""
    pass

def replay(pn, case):
    """Simulates trace [case] in petri net [pn].
    Note: this method invalidates the current marking of [pn].
    If trace [case] is not covered by [pn], returns None.
    Otherwise returns a 2-dimensional array where every row is a marking."""

    places = pn.get_places(names = False)
    trace = np.empty([1 + len(case), len(places)], dtype=np.int)

    # Start from the initial marking
    pn.to_initial_marking()
    for i, p in enumerate(places):
        trace[0, i] = pn.vp_current_marking[p]

    for i, act in enumerate(case, start=1):
        try:
            t = pn.get_elem(act)
        except KeyError:
            return None
        if not pn.is_transition_enabled(t):
            return None
        pn.fire_transition(t)
        for j, p in enumerate(places):
            trace[i, j] = pn.vp_current_marking[p]

    return trace

def fitness(pn, log):
    """Returns the fitness of the given log with respect to net [pn]."""
    num_cases = 0
    num_fitting_cases = 0
    for (case, reps) in log.get_uniq_cases().iteritems():
        if replay(pn, case) is not None:
            num_fitting_cases += reps
        num_cases += reps

    return num_fitting_cases / float(num_cases)

def compute_capacity(pn, log):
    """Compute the capacity of the places in [pn] that would be required to
    replay all the traces from [log].
    Modifies the capacities of [pn], but never decreases an existing capacity."""
    places = pn.get_places(names = False)

    curmax = np.empty([len(places)], dtype=np.int)
    for i, p in enumerate(places):
        curmax[i] = pn.vp_place_capacity[p]

    for case in log.get_uniq_cases():
        trace = replay(pn, case)
        if trace is None:
            raise UnfitLogError, case
        tracemax = np.amax(trace, axis=0)
        curmax = np.maximum(curmax, tracemax)

    for i, p in enumerate(places):
        pn.set_capacity(p, curmax[i])

