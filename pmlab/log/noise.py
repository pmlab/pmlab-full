import random
from .. log import Log

def log_from_noise(log, noise='single', perror=0.05):
    """Generates a log from [log] by injecting errors into the cases.
    
    [noise] Defines the type of noise introduced. 
            Valid values: 'single', 'maruster'
            'single': Use single edits noise up to 30% of trace length. A single
                edit is either an insertion / deletion / swap of events.
            'maruster': Use Maruster's noise. A trace can be removed from a 
                        third of its events, either at the begining, the end or 
                        the middle part. Besides that, two random events can be 
                        swapped.
    [perror] Probability of error injection for each case.
    """
    alphabet=list(log.get_alphabet())
    cases = log.get_cases()
    new_cases = []
    for case in cases:
        words = case[:] # a copy to avoid modifying the original log
        if random.random() <= perror:
            #modify trace    
            if noise == "single":
                modification = random.randint(0,2)
                if modification == 0: #suppression
                    words.pop( random.randint(0,len(words)-1) )
                elif modification == 1: #swap
                    positions = range(len(words))
                    random.shuffle( positions )
                    words[positions[0]], words[positions[1]] = words[positions[1]], words[positions[0]]
                elif modification == 2: #insertion
                    words.insert( random.randint(0, len(words)), random.choice( alphabet ) )
            elif noise == 'maruster':
                # Maruster's noise
                modification = random.randint(0,3)
                if modification < 3: #suppressions
                    if modification == 0: #suppression in first third of trace
                        interval = range(0, len(words)/3 )
                    elif modification == 1: #suppression in middle third of trace
                        interval = range(len(words)/3, 2*len(words)/3 )
                    elif modification == 2: #suppression in last third of trace
                        interval = range(2*len(words)/3, len(words) )
                    random.shuffle( interval )
                    start = min(interval[0:2])
                    end = max(interval[0:2])
                    del words[start:end+1]
                else:
                    #swap
                    positions = range(len(words))
                    random.shuffle( positions )
                    words[positions[0]], words[positions[1]] = words[positions[1]], words[positions[0]]
            else:
                raise TypeError, "Unknown type of noise '{0}'".format(noise)
        new_cases.append(words)
    return Log(cases=new_cases)
