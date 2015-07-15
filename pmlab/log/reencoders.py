"""Provides some custom reencoders for the pmlab package."""
import pickle

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
    """Rencodes by transforming event names into a, b, c, ...
    If more than 27 event names exist, then it uses a, b, ..., aa, ab, ... is used."""
    def update_dictionary(self, word):
        base_letter = ord('a')
        num_letters = 1 + ord('z') - ord('a')
        n = len(self.dict) + 1
        name = ''
        while n > 0:
            name = chr(base_letter + ((n - 1) % num_letters)) + name
            n = ((n - 1) / num_letters)

        self.dict[word] = name

class EventNumberReencoder(DictionaryReencoder):
	"""Reencodes by transforming event names into e0, e1, e2, ..."""
    def update_dictionary(self, word):
        self.dict[word] = 'e{0}'.format(len(self.dict))

class StpReencoder(DictionaryReencoder):
    def update_dictionary(self, word):
        self.dict[word] = word.translate(None," '.\t_()-+&")

