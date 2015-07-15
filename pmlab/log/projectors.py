#from operator import itemgetter
#import pickle
import copy
from .. log import Log

def most_frequent(act_dict, n, extend_same_freq=False):
    """Returns the [n] most frequent activities in the given activity dictionary
    that maps each activity to its frequency.
    [extend_same_freq] if True include additionally all activities whose 
    frequency is the same as the last one selected."""
    sorted_list = sorted(act_dict.iteritems(), key=lambda x: x[1], reverse=True)
    if extend_same_freq:
        if n >= len(sorted_list):
            return act_dict
        return above_threshold(act_dict, sorted_list[n][1])
    else:
        return dict(sorted_list[:n])

def above_threshold(act_dict, threshold):
    """Returns the activities with a frequency above (or equal) to [threshold]
    in the given activity dictionary that maps each activity to its frequency"""
    return dict([(act,occ) for act, occ in act_dict.iteritems() 
                if occ >= threshold])

def project_log( log, activities, action='keep', whole_case=False ):
    """Returns a projected version of [log].
    
    [activities] set/dict/list of activities to keep or to suppress.
    [action] Valid values: keep, suppress, keep_if_any, suppress_if_any,
        keep_if_all, suppress_if_all.
        'keep': only activities in the list will be kept.
        'suppress': only activities in the list will be suppressed.
        'keep_if_any': only cases containing at least one activity in the list
            will be kept.
        'suppress_if_any': only cases containing at least one activity in the 
            list will be removed.
        'keep_if_all': only cases containing all activities in the list
            will be kept.
        'suppress_if_all': only cases containing all activities in the 
            list will be removed.
    """
    if action not in ('keep','suppress', 'keep_if_any','suppress_if_any',
                    'keep_if_all','suppress_if_all' ):
        raise TypeError, ("action can only be 'keep', 'suppress', 'keep_if_any'"
                        "'suppress_if_any', 'keep_if_all' or 'suppress_if_all'")
    cases = log.get_cases()
    new_cases = []
    for case in cases:
        if action=='keep':
            new_case = [act for act in case if act in activities]
            if new_case:
                new_cases.append(new_case)
        elif action=='suppress':
            new_case = [act for act in case if act not in activities]
            if new_case:
                new_cases.append(new_case)
        elif action=='keep_if_any':
            if any([act in activities for act in case]):
                new_cases.append(copy.copy(case))
        elif action=='suppress_if_any':
            if all([act not in activities for act in case]):
                new_cases.append(copy.copy(case))
        elif action=='keep_if_all':
            all_activities = all([act in activities for act in case])
            if all_activities:
                new_cases.append(copy.copy(case))
        elif action=='suppress_if_all':
            all_activities = all([act in activities for act in case])
            if not all_activities:
                new_cases.append(copy.copy(case))
    proj_log = Log(cases=new_cases)
    return proj_log
