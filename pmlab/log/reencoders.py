import pickle
"""Provides some custom reencoders for the pmlab package."""

#def reencode_for_stp(word):
#    """Identifiers cannot contain blanks nor underscores (since they interfere
#    with the variable naming scheme)"""
#    return word.translate(None,' \t_')

#def alpha_reencoder(word):
#    #use generators? yield
#    return
class NonInvertibleDictionaryError(Exception): pass

def reencoder_from_file(filename):
    """Builds a DictionaryReencoder using the information stored in [filename]
    using pickle."""
    own_fid = False
    if isinstance(filename, basestring): #a filename
        file = open(filename)
        own_fid = True
    else:
        file = filename
    encoder = DictionaryReencoder()
    encoder.dict = pickle.load(file)
    return encoder

class DictionaryReencoder():
    """Base class for reencoders based on dictionaries"""
    def __init__(self, dict=None):
        """Initializes the dictionary.
        
        [dict] Use this dictionary. If None, the empty dictionary is initially
            used."""
        if dict:
            self.dict = dict
        else:
            self.dict = {}
        
    def reencode(self, word):
        if word in self.dict:
            return self.dict[word]
        self.update_dictionary(word)
        return self.dict[word]
    
    def update_dictionary(self, word):
        #to be reimplemented in subclasses
        raise TypeError, "unknown key '{0}' in reencoder".format(word)
    
    def save(self, filename):
        """Saves the dictionary table in pickle format, that can later be 
        retrieved using the 'reencoder_from_file' function. 
        [filename] can be a file or a filename."""
        own_fid = False
        if isinstance(filename, basestring): #a filename
            file = open(filename,'w')
            own_fid = True
        else:
            file = filename
        pickle.dump(self.dict, file)
        if own_fid:
            file.close()
    
    def decoder(self):
        """Returns a DictionaryReencoder with the inverted dictionary (if 
        the dictionary is bijective). This reencoder can be used to decode
        a log and obtain the original activitry names"""
        inv_dict = {}
        for k, v in self.dict.iteritems():
            if v in inv_dict:
                raise NonInvertibleDictionaryError, 'Dictionary Reencoder is not invertible'
            else:
                inv_dict[v] = k
        return DictionaryReencoder(inv_dict)

class AlphaReencoder(DictionaryReencoder):
    def update_dictionary(self, word):
        #to be reimplemented in subclasses
        self.dict[word] = chr(ord('a')+len(self.dict))

#we cannot use global instance variables because they keep dictionary state
#between calls!!!
#alpha_reencoder = AlphaReencoder()

class EventNumberReencoder(DictionaryReencoder):
    def update_dictionary(self, word):
        #to be reimplemented in subclasses
        self.dict[word] = 'e{0}'.format(len(self.dict))

#event_number_reencoder = EventNumberReencoder()

class StpReencoder(DictionaryReencoder):
    def update_dictionary(self, word):
        #to be reimplemented in subclasses
        self.dict[word] = word.translate(None," '.\t_()-+&")

#stp_reencoder = StpReencoder()
