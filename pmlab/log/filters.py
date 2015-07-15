import copy
from collections import defaultdict
from .. log import Log


class RemoveImmediateRepetitionsFilter:
    """Removes immediate repetitions of activities (only one activity per
    repetition row is left)."""
    def filter(self, case):
        prev=""
        new_case = []
        for w in case:
            if w != prev:
                new_case.append(w)
            prev = w
        return new_case

class InitActivityFilter:
    """Keeps the cases whose initial activity is the most frequent."""
    def __init__(self, log):
        """Keep the cases whose initial activity has is the most frequent.
        """
        uniq_cases = log.get_uniq_cases()
        histogram = defaultdict(int)
        for cases in uniq_cases.iterkeys():
            histogram[cases[0]] += uniq_cases[cases]
        self.max_act = histogram.keys()[0]
        for act in histogram.iterkeys():
            if histogram[act] > histogram[self.max_act]:
                self.max_act = act
            
    def filter(self, case):
        if case[0] == self.max_act:
            return case



class CaseLengthFilter:
    """Keeps the cases whose length satisfy the conditions specified in the
    constructor."""
    def __init__(self, above=0, below=None):
        """Construct a filter that keeps only cases whose length is in the
        interval [above,below]. If [below] is None, it is considered infinity""" 
        self.below = below
        self.above = above
        
    def filter(self, case):
        if len(case) >= self.above:
            if not self.below or len(case) <= self.below:        
                return copy.copy(case) 

class PrefixerFilter:
    """Prefixes each activity with some given prefix."""
    def __init__(self, prefix='e'):
        self.prefix = prefix
    
    def filter(self, case):
        return [self.prefix+w for w in case]

class FrequencyFilter:
    """Only the cases above a given frequency threshold are kept.
    """
    def __init__(self, log, case_min_freq=None, log_min_freq=None):
        """Keep the cases that have a frequency over (or equal) [case_min_freq]
        if [case_min_freq] is an integer. If it is a float, then the limit is
        computed as a fraction of the total cases: e.g. case_min_freq=0.20 will
        keep only cases that represent at least 20% of the total.
        Similarly, if [log_min_freq] is an integer, then the most frequent cases
        are preserved until a total number of cases equal or greater than 
        [log_min_freq] is preserved. If it is a float, then the value is the
        fraction of the log to be kept.
        If both [case_min_freq] and [log_min_freq] are specified, the most
        restrictive threshold is used.
        """
        threshold = None
        uniq_cases = log.get_uniq_cases()
        all_cases = sum(uniq_cases.itervalues())
        if case_min_freq:
            if case_min_freq == int(case_min_freq):
                #explicit threshold
                threshold = case_min_freq
            else:
                #threshold as a fraction
                threshold = int(all_cases*case_min_freq)
        if log_min_freq:
            histogram = defaultdict(int)
            for cases in uniq_cases.itervalues():
                histogram[cases] += 1
            sorted_hist = sorted([(cases,uniqs) 
                                    for cases,uniqs in histogram.iteritems()],
                                key=lambda x: x[0])

            saved_cases = 0
            saved_uniqs = 0
            log_th = (log_min_freq if log_min_freq == int(log_min_freq) else
                    int(log_min_freq*all_cases))
            #determine new minimum number of cases per sequence    
            for cases, uniqs in reversed(sorted_hist):
                saved_cases += cases*uniqs
                saved_uniqs += uniqs
                if saved_cases >= log_th:
                    if not threshold:
                        threshold = cases
                    else:
                        threshold = max(threshold, cases)
                    break
        if not threshold:
            raise TypeError, ("Either 'case_min_freq' or 'log_min_freq' must be "
                                "different from None")
        print 'All unique cases with at least {0} cases will be kept'.format(threshold)
        self.kept_cases = set([case for case, occ in uniq_cases.iteritems()
                                if occ >= threshold])
        saved_cases = sum([occ for occ in uniq_cases.itervalues()
                                if occ >= threshold])
        saved_uniqs = len(self.kept_cases)
        print 'Filter will save', saved_cases, 
        print 'cases ({0:.1%})'.format(saved_cases/(1.0*all_cases))
        print 'Filter will save', saved_uniqs, 
        print 'unique sequences ({0:.1%})'.format(saved_uniqs/(1.0*len(uniq_cases)))
    
    def filter(self, case):
        if tuple(case) in self.kept_cases:
            return case
    
def filter_log( log, filter ):
    """Returns a filtered version of [log].
    
    Examples:
        fl = pm.log.filters.filter_log(l, pm.log.filters.PrefixerFilter('pre') )
        or
        fl = pm.log.filters.filter_log(l, pm.log.filters.RemoveImmediateRepetitionsFilter() )
        """
    cases = log.get_cases()
    new_cases = []
    for case in cases:
        new_case = filter.filter( case )
        if new_case:
            new_cases.append(new_case)
    filtered_log = Log(cases=new_cases)
    return filtered_log
