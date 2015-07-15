from collections import deque
import tempfile
import subprocess

from pyparsing import (ParserElement, Word, Optional, Literal, oneOf, LineEnd,
                        ZeroOrMore, OneOrMore, Suppress, Group, ParseException, 
                        alphas, nums, alphanums, pythonStyleComment)
import graph_tool.all as gt 

class IndeterminedTsError(Exception):
    """This error is raised whenever there is non determinism in the TS and this is
    not expected"""
    pass

class UnfitTsError(Exception):
    """Raised whether the logs are not reproduced by the TS."""
    pass

def ts_from_log(log, conversion, tail=0, folding=0):
    """Uses the log2ts application to generate a TS out of the log.
    [conversion] describes which conversion method must be used.
        'seq': sequential conversion
        'mset': multiset conversion
        'set': set conversion
        'cfm': common final marking conversion
        This parameter is ignored if [folding] > 0.
    [tail] consider the last [tail] elements only (0 is unbounded)
    """
    if (log.modified_since_last_write or 
        log.last_write_format not in ('raw','raw_uniq')):
        tmpfile = tempfile.NamedTemporaryFile(mode='w', delete=False)
        print "Saving log to temporary file '{0}'".format( tmpfile.name )
        log.save(tmpfile)
        tmpfile.close()
        log_filename = tmpfile.name
    else:
        log_filename = log.filename
    params = ['log2ts', '--tail', '{0}'.format(tail)]

    if folding > 0:
        params += ['--fold','{0}'.format(folding),'--modulo']
    else:
        if conversion=='seq':
            pass
        elif conversion in ('mset','set','cfm'):
            params.append('--'+conversion)
        else:
            raise TypeError, "Invalid conversion for the log.convert_to_ts function"
    params.append( log_filename )
    log2ts_output = subprocess.check_output( params )
    tmpfile2 = tempfile.NamedTemporaryFile(mode='w', delete=False)
    print "Saving TS to temporary file '{0}'".format( tmpfile2.name )
    print >>tmpfile2, log2ts_output
    tmpfile2.close()
    ts = ts_from_file(tmpfile2.name)
    return ts

#        return params
# definition of TS grammar
ParserElement.setDefaultWhitespaceChars(" \t")
id = Word(alphanums+"_\"'.:-")
#place = Literal("p") + Word(nums)
number = Word(nums).setParseAction(lambda tokens: int(tokens[0]))
newlines = Suppress(OneOrMore(LineEnd()))
modelName = ".model" + id("modelName") + newlines
signalNames = ZeroOrMore(Suppress(oneOf(".inputs .outputs")) + OneOrMore( id ) + newlines)("signals")
dummyNames = Optional(Suppress(".dummy") + OneOrMore( id ) + newlines, default=[])("dummies")
arc = id + id + id + newlines
graph = Literal(".state graph") + newlines + OneOrMore(Group(arc))("arcs")
frequency_list = ZeroOrMore(Group(id+number)+newlines)
frequency = ".frequencies" + Suppress(OneOrMore(LineEnd())) + frequency_list("frequencies")
marking_list = ZeroOrMore(id)
marking = ".marking" + Suppress("{") + marking_list("marking") + Suppress("}") + newlines
ts_grammar = Optional(newlines) + Optional(modelName) + signalNames + dummyNames + graph + marking + Optional(frequency) + ".end"
ts_grammar.ignore(pythonStyleComment)

def ts_from_sis(file_or_filename):
    """Loads a TS (possibly extended with state frequencies) in SIS format."""
    if isinstance(file_or_filename, basestring): #a filename
        filename = file_or_filename
    else: # a file object
        try:
            filename = file_or_filename.filename
        except AttributeError:
            filename = ''

    ast = ts_grammar.parseFile(file_or_filename)
    ts = TransitionSystem(filename=filename, format='sis')
    ts.set_name( ast.modelName )
    ts.set_signals( ast.signals )
    ts.set_dummies( ast.dummies )

    for a in ast.arcs:
        s1 = ts.add_state(a[0])
        s2 = ts.add_state(a[2])
        ts.add_edge(s1,a[1],s2)

    ts.set_initial_state( ast.marking[0] )

    if ast.frequencies:
        ts.add_state_frequencies()
        for f in ast.frequencies:
            ts.set_state_frequency(f[0], f[1])

    if len(filename) > 0:
		ts.mark_as_modified( False )
    return ts

def ts_from_file(filename):
	return ts_from_sis(filename)

class TransitionSystem:
    """ Class representing a Transitions System. Uses a graph_tool graph as 
    underlying representation."""
    def __init__(self, filename=None, format=None):
        """ Constructs an empty TS.
        [filename] file name if the TS was obtained from a file.
        [format] only meaningful if filename is not None, since it is the format
        of the original file. Valid values: 'sis', 'xml', 'gml', 'dot'.
        """
        self.filename = filename
        #contains the filename of the file containing the TS (if TS was loaded
        #from a file), or the filename were the TS has been written
        self.modified_since_last_write = False
        #indicates if TS has been modified since it was last written (or 
        #initially loaded)
        self.last_write_format = format

        self.g = gt.Graph()
        self.gp_name = self.g.new_graph_property("string")
        self.g.graph_properties["name"] = self.gp_name
        self.gp_signals = self.g.new_graph_property("vector<string>")
        self.g.graph_properties["signals"] = self.gp_signals
        self.gp_dummies = self.g.new_graph_property("vector<string>")
        self.g.graph_properties["dummies"] = self.gp_dummies
        self.gp_initial_state = self.g.new_graph_property("string")
        self.g.graph_properties["initial_state"] = self.gp_initial_state
        self.vp_state_name = self.g.new_vertex_property("string")
        self.g.vertex_properties["name"] = self.vp_state_name
        
        self.ep_edge_label = self.g.new_edge_property("string")
        self.g.edge_properties["label"] = self.ep_edge_label
        self.name_to_state = {} # reverse map: name->state
        self.initial_state = []

    def add_state_frequencies(self):
        """Prepares the TS to store frequency information on vertices. This way
        TSs not using this information are smaller."""
        self.vp_state_frequency = self.g.new_vertex_property("int")
        self.g.vertex_properties["frequency"] = self.vp_state_frequency
    
    def add_edge_frequencies(self):
        """Prepares the TS to store frequency information on vertices. This way
        TSs not using this information are smaller."""
        self.ep_edge_frequency = self.g.new_edge_property("int")
        self.g.edge_properties["frequency"] = self.ep_edge_frequency
        
    def add_state_cases(self):
        """Prepares the TS to store cases going through each state information 
        on vertices. This way TSs not using this information are smaller."""
        self.vp_state_cases = self.g.new_vertex_property("vector<int>")
        self.g.vertex_properties["cases"] = self.vp_state_cases
    
    def mark_as_modified(self, modified=True):
        """Marks the TS as modified (so that operations on this TS that 
        require a file are not forwarded the corresponding file (if any)), 
        instead they will create a new suitable file.
        """
        self.modified_since_last_write = modified
        
    def set_name(self, name):
        self.gp_name[self.g] = name
        
    def get_name(self):
        return self.gp_name[self.g]
    
    def set_signals(self, signals):
        self.gp_signals[self.g] = signals
        
    def get_signals(self):
        return self.gp_signals[self.g]

    def set_dummies(self, dummies):
        self.gp_dummies[self.g] = dummies

    def get_dummies(self):
        return self.gp_dummies[self.g]

    def set_initial_state(self, istate):
        """Sets the name of the TS's initial state."""
        self.gp_initial_state[self.g] = istate
        
    def get_initial_state(self):
        """Returns the name initial state of the TS."""
        return self.gp_initial_state[self.g]
    
    def get_state_names(self):
        """Returns a list of the state names"""
        return self.name_to_state.keys()
    
    def get_state(self, state):
        """Returns a vertex object representing the state. If [state] is a state
        name, then the corresponding state object is returned. If it is already
        an object, the same object is returned."""
        return self.name_to_state[state] if isinstance(state,str) else state

    def get_edge(self, source, label, target):
        """Returns a edge object representing the transition. [source] and
        [target] can be states or state names. If the transition is not found,
        None is returned."""
        s = self.get_state(source)
        t = self.get_state(target)
        for e in self.g.edge(s, t, all_edges=True):
            if self.ep_edge_label[e] == label:
                return e
        return None

    def get_edges(self):
        """Returns all the transitions in the TS as a list of triples."""
        return [(self.vp_state_name[e.source()], self.ep_edge_label[e], 
                    self.vp_state_name[e.target()])
                for e in self.g.edges()]

    def set_state_frequency(self, state, freq):
        s = self.get_state(state)
        self.vp_state_frequency[s] = freq
        
    def get_state_frequency(self, state):
        """Returns the frequency (number of cases going through) of [state]."""
        s = self.get_state(state)
        return self.vp_state_frequency[s]
    
    def get_state_cases(self, state):
        """Returns the list of cases going through [state]."""
        s = self.get_state(state)
        return self.vp_state_cases[s]
    
    def set_edge_frequency(self, source, label, target, freq):
        e = self.get_edge(source, label, target)
        self.ep_edge_frequency[e] = freq
        
    def get_edge_frequency(self, source, label, target):
        """Returns the frequency (number of cases going through) the edge
        (source,label,target)."""
        e = self.get_edge(source, label, target)
        return self.ep_edge_frequency[e]
        
    def add_state(self, state_name):
        """Adds the given state to the graph, if not previously added. The state
        (either existent or new) is returned."""
        if state_name in self.name_to_state:
            return self.name_to_state[state_name]
        state = self.g.add_vertex()
        self.vp_state_name[state] = state_name
        self.name_to_state[state_name] = state
        self.mark_as_modified()
        return state

    def remove_state(self, state):
        """Removes state [state] and all incident edges.
        Note that this is a O(n) operation, where n is the number of states.
        Use filtering if you need to delete more than one state.
        """
        s = self.get_state(state)
        del self.name_to_state[self.vp_state_name[s]]
        self.g.remove_vertex(s)
        self.mark_as_modified()

    def rename_state(self, state, name):
        s = self.get_state(state)
        del self.name_to_state[self.vp_state_name[s]]
        self.vp_state_name[s] = name
        self.name_to_state[name] = s
        self.mark_as_modified()
    
    def add_edge(self, source, label, target):
        """Adds a labeled edge between source and target. The edge is returned.
        """
        s = self.get_state(source)
        t = self.get_state(target)
        e = self.g.add_edge(s, t)
        self.ep_edge_label[e] = label
        self.mark_as_modified()
        return e

    def remove_edge(self, edge):
        """Removes edge [edge]."""
        self.g.remove_edge(edge)
        self.mark_as_modified()
    
    def number_of_states(self):
        """Returns the number of states in the TS."""
        return self.g.num_vertices()
    
    def find_output_edges(self, state, label):
        """Returns an iterable over all output arcs from [state] with label [label]."""
        s = self.get_state(state)
        return (e for e in s.out_edges() if self.ep_edge_label[e] == label)

    def find_input_edges(self, state, label):
        """Returns an iterable over all input arcs to [state] with label [label]."""
        s = self.get_state(state)
        return (e for e in s.in_edges() if self.ep_edge_label[e] == label)

    def follow_label(self, state, label):
        """Returns an iterable over states that are reachable from [state] following
        transitions with label [label]."""
        return (e.target() for e in self.find_output_edges(self, state, label))

    def self_loop_labels(self):
        """Returns the set of labels of the self loop transitions."""
        selfloops = (e for e in self.g.edges() if e.source() == e.target())
        return set(self.ep_edge_label[e] for e in selfloops)
    
    def map_log_frequencies(self, log, state_freq=True, edge_freq=True, 
                            state_cases=False):
        """Given a log, maps the frequency for which each case visits each state
        (if [state_freq] is True) and each edge (if [edge_freq] is True).
        
        If [state_cases] is true, then a list of case indexes going through each
        state is also kept."""
        if state_freq and 'frequency' not in self.g.vertex_properties:
            self.add_state_frequencies()
        if state_cases and 'cases' not in self.g.vertex_properties:
            self.add_state_cases()
        if edge_freq and 'frequency' not in self.g.edge_properties:
            self.add_edge_frequencies()
        s0 = self.get_state(self.get_initial_state())
        for i, (case, occ) in enumerate(log.get_uniq_cases().iteritems()):
            s = s0
            self.set_state_frequency(s, self.get_state_frequency(s)+occ)
            if state_cases:
                self.vp_state_cases[s].append(i)
            for activity in case:
                #compute destination state
                edges = list(self.find_output_edges(s, activity))
                if len(edges) > 1:
                    raise IndeterminedTsError, "Ambiguous TS! Cannot map frequencies."
                elif len(edges) == 0:
                    raise UnfitTsError, "Unfit TS"
                if edge_freq:
                    self.ep_edge_frequency[edges[0]] += occ
                s = edges[0].target()
                if state_freq:
                    self.vp_state_frequency[s] += occ
                if state_cases:
                    self.vp_state_cases[s].append(i)

    def save(self, filename, format='sis'):
        """Saves the TS. 
        [filename] file or filename where the TS will be saved.
        [format] string representing the output format. Valid formats:
                    sis, xml, gml, dot"""
        if format=='sis':
            own_fid = False
            if isinstance(filename, basestring):
                file = open(filename,'w')
                self.filename = filename
                own_fid = True
            else:
                file = filename
                self.filename = file.name
            if self.get_name():
                print >>file, '.model',self.get_name()
            print >>file, '.outputs', ' '.join(self.get_signals())
            if self.get_dummies():
                print >>file, '.dummy', ' '.join(self.get_dummies())
            print >>file, '.state graph', '#', self.g.num_vertices(), 'states'
            for e in self.g.edges():
                print >>file, self.vp_state_name[e.source()], self.ep_edge_label[e], self.vp_state_name[e.target()]
            print >> file, '.marking {',self.get_initial_state(),'}'
            print >> file, '.end'
            if own_fid:
                file.close()
        else:
            self.g.save( filename, format )
        self.last_write_format = format
        self.mark_as_modified(False)
            
    def draw(self, filename, engine='graphviz'):
        """Draws the TS. The filename extension determines the format.
        [engine] Rendering engine used to draw the TS. Valid values:
            cairo, graphviz, astg (for draw_astg)
        If [filename] is None and engine is 'cairo', then the interactive 
        window is used"""
        if engine == 'graphviz':
            vprops = {'label':self.vp_state_name}
            eprops = {'label':self.ep_edge_label}
            if 'frequency' in self.g.vertex_properties:
    #            vp_width = self.g.new_vertex_property("float")
                all_traces = self.vp_state_frequency[self.get_state(self.get_initial_state())]
    #            for v in self.g.vertices():
    #                vp_width[v] = 3.0*self.vp_state_frequency[v]/all_traces
    #            vprops['width'] = vp_width
                vsize=(self.vp_state_frequency, 2.0/all_traces)
            else:
                vsize=0.105
            if 'frequency' in self.g.edge_properties:
                all_traces = self.vp_state_frequency[self.get_state(self.get_initial_state())]
                penwidth=(self.ep_edge_frequency, 10.0/all_traces)
            else:
                penwidth=1.0
            print vprops
            if self.g.num_vertices() < 150:
                layout = 'dot'
                overlap = False
            else:
                layout = None
                overlap = 'Prism'
            gt.graphviz_draw(self.g, ratio='auto', vprops=vprops, splines=True,
                            eprops=eprops, sep=1.0, overlap=overlap, vsize=vsize, 
                            penwidth=penwidth, layout=layout, output=filename)
        elif engine=='cairo': #use cairo
            pos = gt.sfdp_layout(self.g)
            vprops = {'text':self.vp_state_name}
            if 'frequency' in self.g.vertex_properties:
                vp_width = self.g.new_vertex_property("float")
                all_traces = self.vp_state_frequency[self.get_state(self.get_initial_state())]
                #use numpy array access 
#                vp_widht.a = int(max(100.0*self.vp_state_frequency.a/all_traces)
                for v in self.g.vertices():
                    vp_width[v] = int(100.0*self.vp_state_frequency[v]/all_traces)
                vprops['size'] = vp_width
            gt.graph_draw(self.g, pos=pos, vprops=vprops, output=filename)
        elif engine=='astg':
            if filename.endswith('.ps'):
                format = '-Fps'
            elif filename.endswith('.gif'):
                format = '-Fgif'
            elif filename.endswith('.dot'):
                format = '-Fdot'
            elif filename.endswith('.png'):
                format = '-Fpng'
            elif filename.endswith('.svg'):
                format = '-Fsvg'
            else:
                raise TypeError, 'Unsupported output for draw_astg'
            #check if file can be forwarded as input_filename 
            if self.filename and not self.modified_since_last_write:
                input_filename = self.filename
            else:
            # or create tmp file with save
                tmpfile = tempfile.NamedTemporaryFile(mode='w', delete=False)
                print "Saving TS to temporary file '{0}'".format( tmpfile.name )
                self.save(tmpfile)
                tmpfile.close()
                input_filename = tmpfile.name
            params = ['draw_astg', '-sg', '-noinfo', format, input_filename]
            output = subprocess.check_output( params )
            with open(filename,'w+b') as f:
                f.write(output)

