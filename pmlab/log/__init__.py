"""Module to represent a log (sequences of activities plus additional 
information) in the pmlab package"""
import os.path
from collections import defaultdict
#from xml.dom.minidom import parse
import xml.etree.ElementTree as xmltree
from copy import deepcopy
import gzip
import reencoders
import csv
import re
#import projectors
#import filters
#import clustering
#import tempfile
#import subprocess
#import pmlab.ts

__all__=['reencoders','projectors','filters','clustering']

def log_from_file(filename, format=None, universal_newline=False, 
                    uniq_cases=False, reencoder=None, comment_marks=None):
    """Loads a log from the file [filename]. 
    
    [filename] can be either a filename or directly a file.
    [format] format of the file. Valid values: 'raw', 'xes', None. If None, the
        filename extension is used to try to infer the format.
        'raw': The file is in 'raw' format. i.e. each line contains a case, and 
            each activity is separated by means of a space from the next.
        'xes': XML standard format. In this case the rest of the parameters is
            ignored (no reencodings, comments, etc.). Extracts only activity 
            names.
        'xes_all': XML standard format. In this case the rest of the parameters 
            is ignored (no reencodings, comments, etc.). Extracts ALL activity 
            information, returning an enhanced log.
    [universal_newline]: if cross-platform universal newline must be used when
        opening the filename.
    See function 'log_from_iterable' for the rest of the parameters.
    """
    own_fid = False
    name = None
    if isinstance(filename, basestring): #a filename
        open_mode = 'rU' if universal_newline else 'r'
        if filename.endswith('.gz'):
            file = gzip.open(filename, 'rb')
        else:
            file = open(filename, open_mode)
        own_fid = True #we own this file and we must close it
        name = filename
    else:
        file = filename # a file
        name = file.name
    if format==None:
        base, ext = os.path.splitext(name)
        if ext == '.gz':
            base, ext = os.path.splitext(base)
        if ext == '.tr':
            format = 'raw'
        elif ext == '.xes':
            format = 'xes'
        else:
            raise TypeError, ('Could not determine the format of the file. '
                                'Specify manually')
    if format=='raw':
        log = log_from_iterable(file, name, 'raw', uniq_cases, 
                                reencoder, comment_marks)
    elif format=='xes':
        log = log_from_xes(file, all_info=False, only_uniq_cases=uniq_cases)
    elif format=='csv':
        log = log_from_csv(file, all_info=False, only_uniq_cases=uniq_cases)
    elif format=='xes_all':
        log = log_from_xes(file, all_info=True, only_uniq_cases=uniq_cases)
    else:
        raise ValueError, 'Unknown log format.'
    if own_fid:
        file.close()
    return log

def log_from_iterable( file, filename=None, format=None, uniq_cases=False, 
                        reencoder=None, comment_marks=None):
    """Loads a log from an iterable (i.e. an opened file, a list, etc.)
    
    [filename] file name if the log was obtained from a file.
    [format] only meaningful if filename is not None, since it is the format
    of the original file. Valid values: 'raw', 'raw_uniq', 'xes.
    [uniq_cases] determines if all cases have to be kept, or just the unique ones.
    [reencoder] is a function that receives each word in the file and must return
        a transformed version of it. If None, the same word is used. If a 
        reencoding function is provided, the encoding dictionary is stored in the
        reencoder_on_load field of the log (a DictionaryReencoder).
    [comment_marks] is the iterable containing the characters or strings that 
    identify comments (at the begining of a line).
    
    Example:
    >>> test2 = ['# Reading file: a12f0n00_1.filter.tr', '.state graph', 's0 S s1']
    >>> log2 = pmlab.log.log_from_iterable(test2,
                                        reencoder=lambda x: x.translate(None,'.'), 
                                        comment_marks='#')    
    [['state', 'graph'], ['s0', 'S', 's1']]
    """
    log = Log(filename=filename, format=format)
    encoded_act = {}
    for line in file:
    #print line
        if reencoder:
            orig_words = line.split()
            words = map(reencoder,orig_words)
            for origw, encw in zip(orig_words, words):
                if (origw in encoded_act and
                    encoded_act[origw] != encw):
                    print ("Warning! Two same original activities are being "
                        "encoded differently! "
                        "('{0}' as '{1}' and '{2}')").format( origw, encw, 
                                                            encoded_act[origw])
                encoded_act[origw] = encw
        else:
            words = line.split()
        if len(words) == 0:
            continue
        #ignore if it is a comment
        if comment_marks and words[0][0] in comment_marks:
            continue
        if uniq_cases:
            log.uniq_cases[tuple(words)] += 1
        else:
            log.cases.append( words )
        case_alphabet = set( words )
        log.alphabet |= case_alphabet
    log.reencoder_on_load = reencoders.DictionaryReencoder(encoded_act)
    return log

def log_from_xes(file, all_info=False, only_uniq_cases=False):
    """Load a log in the XES format.
    
    [filename] can be a file or a filename.
    If [all_info] then all XES information for the events is stored in a 
    dictionary. This option is incompatible with [only_uniq_cases], and returns
    an EnhancedLog.
    If [only_uniq_cases] is True, then we discard all other information and we
    keep only the unique cases."""
    if isinstance(file, basestring): #a filename
        filename=file
        if filename.endswith('.gz'):
            file=gzip.open(filename, 'rb')
        else:
            pass # Just send the filename to xmltree.parse
    else:
        filename=file.name
    if all_info and only_uniq_cases:
        raise ValueError, 'Incompatible arguments in log_from_xes'
    tr = {'concept:name':'name', 'lifecycle:transition':'transition',
            'time:timestamp':'timestamp'}
    tree = xmltree.parse(file)
    root = tree.getroot()
    traces = root.findall('{http://www.xes-standard.org/}trace')
    cases = []
    uniq_cases = defaultdict(int)
    for t in traces:
        case = []
        for c in t:
            if c.tag == '{http://www.xes-standard.org/}event':
                if all_info:
                    dict = {tr.get(s.attrib['key'],s.attrib['key']):s.attrib['value'] 
                            for s in c}
                    case.append(dict)
                else:
                    for s in c:
                        if s.attrib['key'] == 'concept:name':
                            case.append(s.attrib['value'])
        if only_uniq_cases:
            uniq_cases[ tuple(case) ] += 1
        else:
            cases.append(case)
    if all_info:
        log = EnhancedLog(filename=filename, format='xes', cases=cases)
    else:
        log = Log(filename=filename, format='xes', cases=cases,
                uniq_cases=uniq_cases)
    return log

def log_from_csv(filename, cols_to_read=None,all_info=False, only_uniq_cases=False,delimiter=None):
    """Load a log in the CSV format.
    
    [filename] can be a file or a filename.
    If [all_info] then all CSV information for the events is stored in a 
    dictionary. This option is incompatible with [only_uniq_cases], and returns
    an EnhancedLog.
    If [only_uniq_cases] is True, then we discard all other information and we
    keep only the unique cases."""
    
    if isinstance(filename, basestring): #a filename
        name=filename
    else:
        name=filename.name
    if all_info and only_uniq_cases:
        raise ValueError, 'Incompatible arguments in log_from_csv'
    with open(name, 'r') as f:        
        cases = []
        #uniq_cases = defaultdict(int)
        dict_csv = {}
        if delimiter:
            reader = csv.reader(f,delimiter=delimiter)
        else: 
            reader = csv.reader(f)
        if not cols_to_read:
            cols_to_read = [0,1,2,3]
        for row in reader:
            if (re.search("#",row[cols_to_read[0]])):
                continue
            #assuming row[0] is the case id, and row[1:4] is [activity,time_ini, time_end]
            if (len(cols_to_read) == 4):
                if (row[cols_to_read[0]] in dict_csv):
                    dict_csv[row[cols_to_read[0]]].append(tuple([row[cols_to_read[1]],row[cols_to_read[2]],row[cols_to_read[3]]]))
                else:
                    dict_csv[row[cols_to_read[0]]] = [tuple([row[cols_to_read[1]],row[cols_to_read[2]],row[cols_to_read[3]]])]
            elif (len(cols_to_read) == 3):
                if (row[cols_to_read[0]] in dict_csv):
                    dict_csv[row[cols_to_read[0]]].append(tuple([row[cols_to_read[1]],row[cols_to_read[2]]]))
                else:
                    dict_csv[row[cols_to_read[0]]] = [tuple([row[cols_to_read[1]],row[cols_to_read[2]]])]
            else:
                raise ValueError, 'Wrong columns to read'
                
                
        #sorting the activities of each case by the timestamps and create a case in cases var
        for mykey in dict_csv:
            if (len(cols_to_read) == 4):
                dict_csv[mykey].sort(key=lambda tup: tup[1:2])
            elif (len(cols_to_read) == 3):
                dict_csv[mykey].sort(key=lambda tup: tup[1])
            cases.append(map(lambda x: x[0],dict_csv[mykey]))
            
    if (only_uniq_cases):
         uniq_cases = defaultdict(int)
         for case in cases:
            uniq_cases[ tuple(case) ] += 1
         log = Log(filename=name, format='csv', cases=cases, 
                uniq_cases=uniq_cases)  
    else:
         log = Log(filename=name, format='csv', cases=cases)
    return log   

def activity_positions(log):
    """Computes the activity positions of each unique case in [log]. Returns a
    list of dictionaries (one per unique case). Each dictionary maps each 
    activity to the ordered list of positions in which it appears in that case."""
    #For each trace, for each activity, we must store the positions 
    # where it executes
    activity_positions = [] 
    # list of dictionaries, one per trace. 
    # Each entry contains an ordered list of position
    cases = log.get_uniq_cases()
    for case in cases:
        position_dictionary = defaultdict(list)
        for i, act in enumerate(case):
            position_dictionary[act].append(i)
        activity_positions.append( position_dictionary )
    return activity_positions

class Log:
    """Class representing a basic log"""
    def __init__(self, filename=None, format=None, cases=None, uniq_cases=None):
        """Initializes a plain log from a list of cases or unique cases.
        
        [filename] file name if the log was obtained from a file.
        [format] only meaningful if filename is not None, since it is the format
        of the original file. Valid values: 'raw', 'raw_uniq', 'xes'.
        If [cases] or [uniq_cases] are given, constructs a log with those
        (unique) cases. Otherwise return an empty log."""
        self.filename = filename
        #contains the filename of the file containing the log (if log was laoded
        #from a file), or the filename were the log has been written
        self.modified_since_last_write = False
        #indicates if log has been modified since it was last written (or 
        #initially loaded)
        self.last_write_format = format
        self.alphabet = set()
        self.reencoder_on_load = None
        #DictionaryReencoder produced by the reencoding function during load
        
        self.cases = cases if cases else []
        self.uniq_cases = uniq_cases if uniq_cases else defaultdict(int)
        #self.uniq_cases = defaultdict(int)
        self.activity_positions = None
        
    def get_cases(self):
        """Returns the list of cases of the log. If the log was stored
        as a set of unique cases, then the log is 'rehydratated' """
        if not self.cases and self.uniq_cases:
            #compute non unique cases by replicating each unique case its 
            # occurrence times
            for ucase, occ in self.uniq_cases.iteritems():
                self.cases += [ucase]*occ
        return self.cases
    
    def get_uniq_cases(self):
        """Returns the list of unique cases of the log. If the log was 
        stored as a list of cases, then the log is 'compressed' and unique cases
        are computed (and permanently stored)."""
        if self.cases and not self.uniq_cases:
            for case in self.cases:
                self.uniq_cases[tuple(case)] += 1
        return self.uniq_cases
    
    def get_alphabet(self):
        """Returns the alphabet of the log.
        
        Example:
        >>> log = pmlab.log.log_from_xes('mergenet/ProM6/exercise1.xes')
        >>> log.get_alphabet()
        set(['A', 'C', 'B', 'E', 'D'])"""
        if not self.alphabet:
            self.alphabet = set()
            uniq_cases = self.get_uniq_cases()
            for case in uniq_cases:
                self.alphabet |= set(case)
        return self.alphabet
    
    def get_activity_positions(self):
        """Returns the positions of each activity in each case."""
        if not self.activity_positions:
            self.activity_positions = activity_positions(self)
        return self.activity_positions
    
    def mark_as_modified(self, modified=True):
        """Marks the log as modified (so that operations on this log that 
        require a file are not forwarded the corresponding file (if any)), 
        instead they will create a new suitable file.
        """
        self.modified_since_last_write = modified
        
    def __add__(self, log):
        """Returns the log obtained by merging the two logs."""
        return Log(cases=deepcopy(self.get_cases()+log.get_cases()))
    
    def has_unique_start_activity(self):
        """Return True if the log has a unique start activity that fires 
        only once per case"""
        start_act_ok = True
        uniq_cases = self.get_uniq_cases()
        start_activities = set([w[0] for w in uniq_cases])
        if len(start_activities) > 1:
            start_act_ok = False
            print 'More than one initial activity:', start_activities
        if start_act_ok:
            start_act = start_activities.pop()
            for words in uniq_cases:
                start_act_ok &= start_act not in words[1:-1]
        if start_act_ok:
            print 'Log has a unique start activity that fires only once per case'
        return start_act_ok
    
    def add_dummy_start_activity(self, candidates=['S','start','begin']):
        """Adds a dummy start activity to all cases, using the first element
        in candidates list that does not appear in the current log alphabet. If
        no candidates are available, None is returned. Otherwise the name of the
        dummy activity is returned."""
        possible_candidates = [cand for cand in candidates 
                                if cand not in self.get_alphabet()]
        if not possible_candidates:
            print ('All candidates for initial activity where already used, '
                'please enlarge candidate list and rerun.')
            return None
        start_act = possible_candidates[0]
        for case in self.cases:
            case[0:0] = [start_act]
        if self.uniq_cases:
            new_uniq_cases = defaultdict(int)
            for case,occ in self.uniq_cases.iteritems():
                new_case = (start_act,)+case
                new_uniq_cases[new_case] = occ
            self.uniq_cases = new_uniq_cases
        if self.alphabet:
            self.alphabet.add(start_act)
        self.activity_positions = None #to force recomputation
        self.mark_as_modified()
        return start_act
    
    def has_unique_end_activity(self):
        """Return True if the log has a unique end activity that fires 
        only once per case"""
        end_act_ok = True
        uniq_cases = self.get_uniq_cases()
        end_activities = set([w[-1] for w in uniq_cases])
        if len(end_activities) > 1:
            end_act_ok = False
            print 'More than one final activity:', end_activities
        if end_act_ok:
            end_act = end_activities.pop()
            for words in uniq_cases:
                end_act_ok &= end_act not in words[1:-1]
        if end_act_ok:
            print 'Log has a unique end activity that fires only once per case'
        return end_act_ok
    
    def add_dummy_end_activity(self, candidates=['E','final','end']):
        """Adds a dummy end activity to all cases, using the first element
        in candidates list that does not appear in the current log alphabet. If
        no candidates are available, None is returned. Otherwise the name of the
        dummy activity is returned."""
        possible_candidates = [cand for cand in candidates 
                                if cand not in self.get_alphabet()]
        if not possible_candidates:
            print ('All candidates for initial activity were already used, '
                'please enlarge candidate list and rerun.')
            return None
        end_act = possible_candidates[0]
        for case in self.cases:
            case.append( end_act )
        if self.uniq_cases:
            new_uniq_cases = defaultdict(int)
            for case,occ in self.uniq_cases.iteritems():
                new_case = case+(end_act,)
                new_uniq_cases[new_case] = occ
            self.uniq_cases = new_uniq_cases
        if self.alphabet:
            self.alphabet.add(end_act)
        self.activity_positions = None #to force recomputation
        self.mark_as_modified()
        return end_act
    
    def reencode(self, reencoder, write_dict=False, dict_file=None):
        """Reencodes the log activities using the given reencoder.
        [reencoder] object with a 'reencode(word)' function and a 'save'
        function that allows to save the encoding to a file.
        [write_dict] True if the reencoding dictionary must be written
        [dict_file] can be a file or a filename. If [write_dict] the dictionary
        will be written here. If None, the name of the log will be used to 
        store the dictionary, appending '.dict'.
        
        Example:
            log.reencode( pmlab.log.reencoders.AlphaReencoder() )
        """
        if self.cases:
            for case in self.cases:
                case[:] = [reencoder.reencode(word) for word in case]
        if self.uniq_cases:
            new_uniq = defaultdict(int)
            for case,occ in self.uniq_cases.iteritems():
                new_uniq[tuple(map(reencoder.reencode,case))] = occ
            self.uniq_cases = new_uniq
        self.alphabet = set() #to force recomputation
        self.activity_positions = None #to force recomputation
        self.mark_as_modified()
        if write_dict:
            own_fid = False
            if not dict_file:
                if self.filename:
                    dict_file = self.filename+'.dict'
                else:
                    dict_file = 'reencode.dict'
            if isinstance(dict_file, basestring): #a filename
                file = open(dict_file,'w')
                own_fid = True
            else:
                file = filename
            print 'Saving dictionary to', file.name
            reencoder.save(file)
            if own_fid:
                file.close()
    
    def case_length_histogram(self):
        """Returns a sorted list of tuples (x,y) where x is the case length and
        y is the number of cases with that length"""
        cases = self.get_uniq_cases()
        histo = defaultdict(int)
        for case, occ in cases.iteritems():
            histo[len(case)] += occ
        return sorted(histo.items(), key=lambda x: x[0])
    
    def case_frequency_histogram(self):
        """Returns a sorted list of tuples (x,y) where x is the case frequency and
        y is the number of unique cases with that frequency"""
        cases = self.get_uniq_cases()
        histo = defaultdict(int)
        for case, occ in cases.iteritems():
            histo[occ] += 1
        return sorted(histo.items(), key=lambda x: x[0])
    
    def statistics(self):
        print 'Alphabet size:', len(self.get_alphabet())
        all_cases = len(self.get_cases())
        print 'Number of cases:', all_cases
        print 'Number of unique cases:', len(self.get_uniq_cases())
        case_histo = self.case_length_histogram()
        print 'Length of shortest case:',case_histo[0][0]
        print 'Length of largest case:',case_histo[-1][0]
        total_length = sum([length*numcases for length, numcases in case_histo])
        print 'Average case length: {0:.1f}'.format(1.0*total_length/all_cases)
        
    def activity_frequencies(self, case_count=False):
        """Returns a dictionary maping each activity to the number of total
        occurrences in the log.
        
        [case_count] If True, count the number of cases in which each activity
            appears, not the total occurrences (each activity can appear more 
            than once per case).
        """
        uniq_cases = self.get_uniq_cases()
        act_freq = defaultdict(int)
        for case,occ in uniq_cases.iteritems():
            if case_count:
                case = set(case)
            for act in case:
                act_freq[act] += occ
        return act_freq
        
    def cases_per_activity(self, uniq_cases=False):
        """Returns a dictionary that maps each activity to a list of the 
        case indexes in which the activity appears.
        
        [uniq_cases] Determines if the indexes correspond to all the cases or
        just the unique cases."""
        cases = self.get_cases() if not uniq_cases else self.get_uniq_cases()
        cases_per_act = defaultdict(set)
        for i, case in enumerate(cases):
            for w in case:
                cases_per_act[w].add(i)
        return cases_per_act
    
    def save(self, filename, format='raw', uniq_cases=False):
        """Write the log in [filename] using the given format. 
        [filename]: file or filename in which the log has to be written
        Format values are:
            'raw': print all cases (with or without repetitions according to the
                [uniq_cases] parameter), just the activity names.
            'xes': use the XES format, just the activity names.
        [uniq_cases]: If True, then only the unique cases are written.
        """
        own_fid = False
        if isinstance(filename, basestring): #a filename
            file = open(filename,'w')
            self.filename = filename
            own_fid = True
        else:
            file = filename
            self.filename = file.name
        if format=='raw':
            cases = self.get_uniq_cases() if uniq_cases else self.get_cases()
            for case in cases:
                print >> file, ' '.join(case)
        elif format=='xes':
            root = xmltree.Element('log')
            root.attrib['xes.version']="1.0" 
            root.attrib['xes.features']="" 
            root.attrib['openxes.version']="1.0RC7" 
            root.attrib['xmlns']="http://www.xes-standard.org/"
            concept = xmltree.SubElement(root,'extension')
            concept.attrib['name']="Concept" 
            concept.attrib['prefix']="concept" 
            concept.attrib['uri']="http://www.xes-standard.org/concept.xesext"
            life = xmltree.SubElement(root,'extension')
            life.attrib['name']="Lifecycle" 
            life.attrib['prefix']="lifecycle" 
            life.attrib['uri']="http://www.xes-standard.org/lifecycle.xesext"
            lname = xmltree.SubElement(root,'string')
            lname.attrib['key'] = "concept:name"
            lname.attrib['value'] = self.filename
            cases = self.get_uniq_cases() if uniq_cases else self.get_cases()
            for i, case in enumerate(cases):
                trace = xmltree.SubElement(root,'trace')
                tname = xmltree.SubElement(trace,'string')
                tname.attrib['key'] = "concept:name"
                tname.attrib['value'] = 'case{0}'.format(i)
                for act in case:
                    event = xmltree.SubElement(trace,'event')
                    ename = xmltree.SubElement(event,'string')
                    ename.attrib['key'] = "concept:name"
                    ename.attrib['value'] = act
                    elf = xmltree.SubElement(event,'string')
                    elf.attrib['key'] = "lifecycle:transition"
                    elf.attrib['value'] = 'complete'
            print >> file, xmltree.tostring(root)
        else:
            if own_fid:
                file.close()
            raise TypeError, "Invalid format for the log.write function"
        self.last_write_format = format
        self.mark_as_modified(False)
        if own_fid:
            file.close()
    
class EnhancedLog(Log):
    """Class representing a log with enhanced information. Each activity is 
    represented by a dictionary. Dictionary keywords can be whatever, however
    we define some standard concepts:
        name: activity name
        start_time: initial time of the activity
        end_time: end time of the activity
    
    Since additional information is present, the support for unique cases in 
    this class is more limited than in plain logs."""
    def __init__(self, filename=None, format=None, cases=None):
        """ Constructs an enhanced log.
        
        [filename] file name if the log was obtained from a file.
        [format] only meaningful if filename is not None, since it is the format
        of the original file. Valid values: 'raw', 'raw_uniq', 'xes'.
        If [cases] are given, constructs a log with those cases. Otherwise 
        return an empty log."""
        Log.__init__(self, filename=filename, format=format, cases=cases)
    
    def get_cases(self, full_info=False):
        """Returns the list of cases of the log. 
        
        If [full_info] is True, then the cases with the full information are 
        returned (i.e., a list of sequences of dictionaries). Otherwise, only
        a plain log is returned (so that an enhanced log can be used without 
        any change with the available algorithms).
        """
        if full_info:
            return self.cases
        else:
            return [[act['name'] for act in case] for case in self.cases]
    
    def get_uniq_cases(self):
        """Returns the list of unique cases of the log. Unique cases are 
        computed from the cases (and permanently stored)."""
        if self.cases and not self.uniq_cases:
            for case in self.cases:
                self.uniq_cases[tuple([act['name'] for act in case])] += 1
        return self.uniq_cases

    def add_dummy_start_activity(self, candidates=['S','start','begin']):
        """Adds a dummy start activity to all cases, using the first element
        in candidates list that does not appear in the current log alphabet. If
        no candidates are available, None is returned. Otherwise the name of the
        dummy activity is returned."""
        possible_candidates = [cand for cand in candidates 
                                if cand not in self.get_alphabet()]
        if not possible_candidates:
            print ('All candidates for initial activity where already used, '
                'please enlarge candidate list and rerun.')
            return None
        start_act = possible_candidates[0]
        for case in self.cases:
            case[0:0] = [{'name':start_act}]
        if self.uniq_cases:
            new_uniq_cases = defaultdict(int)
            for case,occ in self.uniq_cases.iteritems():
                new_case = (start_act,)+case
                new_uniq_cases[new_case] = occ
            self.uniq_cases = new_uniq_cases
        if self.alphabet:
            self.alphabet.add(start_act)
        self.activity_positions = None #to force recomputation
        self.mark_as_modified()
        return start_act
    
#    
#    def add_dummy_end_activity(self, candidates=['E','final','end']):
#        """Adds a dummy end activity to all cases, using the first element
#        in candidates list that does not appear in the current log alphabet. If
#        no candidates are available, None is returned. Otherwise the name of the
#        dummy activity is returned."""
#        possible_candidates = [cand for cand in candidates 
#                                if cand not in self.get_alphabet()]
#        if not possible_candidates:
#            print ('All candidates for initial activity were already used, '
#                'please enlarge candidate list and rerun.')
#            return None
#        end_act = possible_candidates[0]
#        for case in self.cases:
#            case.append( end_act )
#        if self.uniq_cases:
#            new_uniq_cases = defaultdict(int)
#            for case,occ in self.uniq_cases.iteritems():
#                new_case = case+(end_act,)
#                new_uniq_cases[new_case] = occ
#            self.uniq_cases = new_uniq_cases
#        if self.alphabet:
#            self.alphabet.add(end_act)
#        self.activity_positions = None #to force recomputation
#        self.mark_as_modified()
#        return end_act
    
    def reencode(self, reencoder, write_dict=False, dict_file=None):
        """Reencodes the log activities using the given reencoder.
        [reencoder] object with a 'reencode(word)' function and a 'save'
        function that allows to save the encoding to a file.
        [write_dict] True if the reencoding dictionary must be written
        [dict_file] can be a file or a filename. If [write_dict] the dictionary
        will be written here. If None, the name of the log will be used to 
        store the dictionary, appending '.dict'.
        
        Example:
            log.reencode( pmlab.log.reencoders.AlphaReencoder() )
        """
        if self.cases:
            for case in self.cases:
                for act in case:
                    act['name'] = reencoder.reencode(act['name'])
        if self.uniq_cases:
            new_uniq = defaultdict(int)
            for case,occ in self.uniq_cases.iteritems():
                new_uniq[tuple(map(reencoder.reencode,case))] = occ
            self.uniq_cases = new_uniq
        self.alphabet = set() #to force recomputation
        self.activity_positions = None #to force recomputation
        self.mark_as_modified()
        if write_dict:
            own_fid = False
            if not dict_file:
                if self.filename:
                    dict_file = self.filename+'.dict'
                else:
                    dict_file = 'reencode.dict'
            if isinstance(dict_file, basestring): #a filename
                file = open(dict_file,'w')
                own_fid = True
            else:
                file = filename
            print 'Saving dictionary to', file.name
            reencoder.save(file)
            if own_fid:
                file.close()
                
    def cases_per_activity(self, uniq_cases=False):
        """Returns a dictionary that maps each activity to a list of the 
        case indexes in which the activity appears.
        
        [uniq_cases] Determines if the indexes correspond to all the cases or
        just the unique cases."""
        if not uniq_cases:
            cases = self.get_cases()
            cases_per_act = defaultdict(set)
            for i, case in enumerate(cases):
                for act in case:
                    cases_per_act[act['name']].add(i)
        else:
            cases = self.get_uniq_cases()
            cases_per_act = defaultdict(set)
            for i, case in enumerate(cases):
                for w in case:
                    cases_per_act[w].add(i)
        return cases_per_act
    
    def save(self, filename, format='json'):
        """Write the log in [filename] using the given format. 
        [filename]: file or filename in which the log has to be written
        Format values are:
            'raw': print all cases (with repetitions), just the activity names.
            'raw_uniq': print all unique cases, just the activity names.
            'xes': use the XES format, all the information.
        """
        own_fid = False
        if isinstance(filename, basestring): #a filename
            file = open(filename,'w')
            self.filename = filename
            own_fid = True
        else:
            file = filename
            self.filename = file.name
        if format=='raw':
            for case in self.get_cases():
                print >> file, ' '.join([act['name'] for act in case])
        elif format=='raw_uniq':
            for case in self.get_uniq_cases():
                print >> file, ' '.join(case)
        elif format=='xes':
            pass
        elif format=='json':
            json.dump(self.get_cases(), file)
        else:
            if own_fid:
                file.close()
            raise TypeError, "Invalid format for the log.write function"
#        self.last_write_format = format
#        self.mark_as_modified(False)
        if own_fid:
            file.close()
