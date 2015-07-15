#! /usr/bin/python
from collections import defaultdict
from optparse import OptionParser
from bitstring import BitArray

class Place:
    def __init__(self):
        self.pos_gradient = {} #maps each event to its positive gradient
        self.neg_gradient = {} #maps each event to its positive gradient
        self.multiplicity = {} # maps each state to its multiplicity
        self.total_multiplicity = 0 #sum of all the multiplicities
        
    def __str__(self):
        events = sorted(self.pos_gradient.keys() )
        str = 'Gradient:'
        for ev in events:
            if self.pos_gradient[ev] == 0 and self.neg_gradient[ev] == 0: 
                continue
            str += ev+' '
            if self.pos_gradient[ev] > 0:
                str += '{0} '.format(self.pos_gradient[ev])
            if self.neg_gradient[ev] > 0:
                str += '{0} '.format(-self.neg_gradient[ev])
        str += 'Total multiplicity: {0}'.format( self.total_multiplicity )
        return str
        
def build_place_from_stp( stpfile ):
    """Reads the content of an output STP file and returns a Place object.
    """
    place = Place()
    for line in stpfile:
        words = line.split()
        if len(words) == 5:
            if words[1][0] == 's': #state
                if words[3][1] == 'b':
                    place.multiplicity[words[1]] = int(words[3][2:],2)
                elif words[3][1] == 'x':
                    place.multiplicity[words[1]] = int(words[3][2:],16)
                else:
                    print 'Unknown base:', words[3]
            elif words[1][0:2] == 'dp': #positive gradient
                place.pos_gradient[words[1][3:]] = int(words[3][2:],2)
            elif words[1][0:2] == 'dn': #positive gradient
                place.neg_gradient[words[1][3:]] = int(words[3][2:],2)
            elif words[1][0:2] == 'd_': # single gradient
                grad = BitArray(words[3]).int#int(words[3][2:],2)
                if grad < 0:
                    place.neg_gradient[words[1][2:]] = -grad
                    place.pos_gradient[words[1][2:]] = 0
                else:
                    place.pos_gradient[words[1][2:]] = grad
                    place.neg_gradient[words[1][2:]] = 0
            #elements = words[1].split('_')
    
    place.total_multiplicity = sum(place.multiplicity.values())
    return place

if __name__ == "__main__":
    parser = OptionParser(usage="%prog [options] filename",
                        version="%prog 0.1", 
                        description="Builds a place out of the output of the STP solver.")
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("incorrect number of arguments. Type -h for help.")
    try:
        stpfile = open(args[0])
    except Exception as ex:
        print("Error. Cannot open file '%s'. %s" % (args[0], ex))
        quit()
    place = build_place_from_stp( stpfile )
    stpfile.close()
    print place
