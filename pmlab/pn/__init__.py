import tempfile
import subprocess
import os.path
from random import randint

from pyparsing import (ParserElement, Word, Optional, Literal, oneOf, LineEnd,
                        ZeroOrMore, OneOrMore, Suppress, Group, ParseException, 
                        alphas, nums, alphanums, pythonStyleComment)
import graph_tool.all as gt
import xml.etree.ElementTree as xmltree
from .. ts import ts_from_sis
from . tpn import pn_from_tpn

__all__ = ['pn_from_ts', 'ts_from_pn', 'pn_from_file', 'PetriNet']

def pn_from_ts(ts, method='rbminer', k=1, agg=0 ):
    """Uses the [method] to generate a TS out of the log.
    [method] describes which conversion method/tool must be used.
        'rbminer': use the rbminer application 
        'stp': use SMT method
    [k] k-boundedness of the regions found.
    [agg] aggregation factor (lower bound on the upper bound of arcs that a
    place can have). In many cases (e.g. acyclic TSs) it is the upper bound.
    0 represents unbounded. This parameter is ignored by 'stp' and should be
    quite small if the number of activities in the TS is large (4 or less is 
    usually a good option).
    """
    if method == 'rbminer':
        if (ts.modified_since_last_write or 
            ts.last_write_format != 'sis'):
            tmpfile = tempfile.NamedTemporaryFile(mode='w', delete=False)
            print "Saving TS to temporary file '{0}'".format( tmpfile.name )
            ts.save(tmpfile)
            tmpfile.close()
            ts_filename = tmpfile.name
        else:
            ts_filename = ts.filename
        params = ['rbminer', '--k', '{0}'.format(k)]
    #        return params
        if agg > 0:
            params += ['--agg','{0}'.format(agg)]
#        else:
#            if conversion=='seq':
#                pass
#            elif conversion in ('mset','set','cfm'):
#                params.append('--'+conversion)
        params.append( ts_filename )
        rbminer_output = subprocess.check_output( params )
        tmpfile2 = tempfile.NamedTemporaryFile(mode='w', delete=False)
        print "Saving PN to temporary file '{0}'".format( tmpfile2.name )
        print >>tmpfile2, rbminer_output
        tmpfile2.close()
        pn = pn_from_sis(tmpfile2.name)
        return pn
    elif method == 'stp':
        import stp_min_region
        pn = stp_min_region.pn_from_ts(ts, k)
        return pn
    else:
        raise TypeError, "Invalid discovery method for the pn_from_ts function"

def ts_from_pn(pn):
    args = ['write_sg', '-huge']
    need_to_write = pn.modified_since_last_write or pn.last_write_format != 'sis'
    if not need_to_write: # We can pass the file "as-is"
        args.append(pn.filename)

    proc = subprocess.Popen(args, stdin = subprocess.PIPE, stdout = subprocess.PIPE, bufsize = -1, close_fds = True)

    if need_to_write:
        pn.save_as_sis(proc.stdin, temporary=True)
    proc.stdin.close()

    # No deadlock problem because write2sg first reads everything, then writes the result

    ts = ts_from_sis(proc.stdout)
    ts.mark_as_modified(True) # Comes from a pipe, not a file
    proc.stdout.close()

    proc.wait()
    if proc.returncode != 0:
        raise EnvironmentError, "call to write_sg failed"

    return ts

# definition of PN grammar
ParserElement.setDefaultWhitespaceChars(" \t")
id = Word(alphanums+"_\"':.-")
number = Word(nums).setParseAction(lambda tokens: int(tokens[0]))
newlines = Suppress(OneOrMore(LineEnd()))
modelName = ".model" + id("modelName") + newlines
signalNames = ZeroOrMore( Suppress(oneOf(".inputs .outputs")) + OneOrMore( id ) + newlines)("signals")
dummyNames = Optional(Suppress(".dummy") + OneOrMore( id ) + newlines, default=[])("dummies")
arc = id + ZeroOrMore(Group(id + Optional(Suppress("(")+number+Suppress(")"), default=1))) + newlines
graph = Literal(".graph") + Suppress(OneOrMore(LineEnd())) + OneOrMore(Group(arc))("arcs")
capacity_list = ZeroOrMore(Group(id+Suppress("=")+number))
capacity = ".capacity" + capacity_list("capacities") + newlines
marking_list = ZeroOrMore(Group(id+Optional(Suppress("=")+number,default=1)))
marking = ".marking"+Suppress("{") + marking_list("marking") + Suppress("}") + newlines
pn = Optional(newlines) + Optional(modelName) + signalNames + dummyNames + graph + Optional(capacity) + Optional(marking) + ".end"
pn.ignore(pythonStyleComment)

def pn_from_file(filename, format=None):
    """Loads a PN stored in the [format] format in file [filename]. If [format]
    is None, then the extension is used to infer the correct format.
    
    Valid values for [format]: None, 'sis', 'pnml'
    """
    if not format:
        name, ext = os.path.splitext(filename)
        if ext=='.g':
            return pn_from_sis(filename)
        elif ext == '.tpn':
            return pn_from_tpn(filename)
        elif ext=='.pnml':
            return pn_from_pnml(filename)
        raise ValueError, 'Format could not be deduced from filename extension'
    if format == 'sis':
        return pn_from_sis(filename)
    elif format == 'tpn':
        return pn_from_tpn(filename)
    elif format == 'pnml':
        return pn_from_pnml(filename)
    raise ValueError, 'Invalid format'

def pn_from_sis(filename):
    """Loads a PN in SIS format.

    [file]: Can either be a filename or a file object."""
    net = PetriNet(filename=filename, format='sis')
    ast = pn.parseFile(filename)
    for t in ast.signals:
        net.add_transition(t)
    for t in ast.dummies:
        net.add_transition(t, dummy=True)
        
    net.set_name(ast.modelName)

    transitions = set(net.get_transitions())
    for a in ast.arcs:
        #print a[0]
        if a[0] not in transitions:
            # it's a place
            p = net.add_place(a[0])
            for t in a[1:]:
                if t[0] not in transitions:
                    raise ValueError, "place -> place arc"
                net.add_edge(p,t[0],t[1])
        else: # a[0] is a transition
            for t in a[1:]:
                if t[0] in transitions: # implicit place
                    p = net.add_place("ip%d" % net.g.num_vertices())
                    net.add_edge(a[0],p,t[1])
                    net.add_edge(p,t[0],t[1])
                else: # transition -> place arc
                    p = net.add_place(t[0])
                    net.add_edge(a[0],p,t[1])
    for m in ast.marking:
        net.set_initial_marking(m[0],m[1])
    for m in ast.capacities:
        net.set_capacity(m[0],m[1])
    net.to_initial_marking()
    return net

def pn_from_pnml(filename):
    """Loads a PN in PNML format."""
    pn = PetriNet(filename=filename, format='pnml')
    ns = '{http://www.pnml.org/version-2009/grammar/pnml}'
    tree = xmltree.parse(filename)
    root = tree.getroot()
    net = root.find('%snet' % ns)
    if net is None:
        # Try non namespaced version
        # "Be conservative in what you send, be liberal in what you accept"
        net = root.find('net')
        if net is None:
            # Nothing to do
            raise ValueError, 'invalid PNML format'
        # Otherwise assume entire file is non-namespaced
        ns = ''
        
    id_map = {}

    def has_name(element):
        node = element.find('%sname/%stext' % (ns, ns))
        return node is not None
    def get_name_or_id(element):
        node = element.find('%sname/%stext' % (ns, ns))
        if node is not None:
            return node.text
        else:
            return element.attrib['id']
    def remove_suffix(s, suffix):
        if s.endswith(suffix):
            return s[:-len(suffix)]
        else:
            return s

    # Recursively enumerate all nodes with tag = transition
    # They might be distributed in several <page> child tags

    for c in net.iterfind('.//%stransition' % ns):
        xml_id = c.attrib['id']
        name = remove_suffix(get_name_or_id(c), '+complete')

        # If it has no name, it's probably a dummy transition
        dummy = not has_name(c)

        id_map[xml_id] = pn.add_transition(name, dummy=dummy)

    for c in net.iterfind('.//%splace' % ns):
        xml_id = c.attrib['id']
        name = get_name_or_id(c)

        p = pn.add_place(name)
        id_map[xml_id] = p

        marking = c.find('%sinitialMarking/%stext' % (ns, ns))
        if marking is not None:
            pn.set_initial_marking(p,int(marking.text))

    for c in net.iterfind('.//%sarc' % ns):
        pn.add_edge(id_map[c.attrib['source']], id_map[c.attrib['target']])

    pn.to_initial_marking()
    return pn

class PetriNet:
    """ Class to represent a Petri Net."""
    def __init__(self, filename=None, format=None):
        """ Constructs an empty PN.
        [filename] file name if the PN was obtained from a file.
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
        self.gp_transitions = self.g.new_graph_property("vector<string>")
        self.g.graph_properties["transitions"] = self.gp_transitions
#        self.gp_initial_marking = self.g.new_graph_property("vector<string>")
#        self.g.graph_properties["initial_state"] = self.gp_initial_state
        #each place and transition has a name
        self.vp_elem_name = self.g.new_vertex_property("string")
        self.g.vertex_properties["name"] = self.vp_elem_name
        self.vp_elem_type = self.g.new_vertex_property("string")
        self.g.vertex_properties["type"] = self.vp_elem_type 
        #either place or transition
        self.vp_place_initial_marking = self.g.new_vertex_property("int")
        self.g.vertex_properties["initial_marking"] = self.vp_place_initial_marking
		# dummy transitions
        self.vp_transition_dummy = self.g.new_vertex_property('bool')
        self.g.vertex_properties["dummy"] = self.vp_transition_dummy
        #current marking is not stored when saving
        self.vp_current_marking = self.g.new_vertex_property("int")
        self.vp_place_capacity = self.g.new_vertex_property("int")
        self.g.vertex_properties["capacity"] = self.vp_place_capacity
        
        self.ep_edge_weight = self.g.new_edge_property("int")
        self.g.edge_properties["weight"] = self.ep_edge_weight
        self.name_to_elem = {} # reverse map: name->elem

    def mark_as_modified(self, modified=True):
        """Marks the PN as modified (so that operations on this PN that 
        require a file are not forwarded the corresponding file (if any)), 
        instead they will create a new suitable file.
        """
        self.modified_since_last_write = modified
    
    def set_name(self, name):
        self.gp_name[self.g] = name
        
    def get_name(self):
        return self.gp_name[self.g]

    def get_elem(self, elem):
        """Returns a vertex object representing the element. If [elem] is an 
        element name, then the corresponding element object (a vertex 
        representing either a place or a transition) is returned. If it is 
        already an object, the same object is returned."""
        return self.name_to_elem[elem] if isinstance(elem,str) else elem

    def add_transition(self, transition_name, dummy=False):
        """Adds the given transition to the graph, if not previously added. The 
        transition (either existent or new) is returned."""
        if transition_name in self.name_to_elem:
            return self.name_to_elem[transition_name]
        t = self.g.add_vertex()
        self.vp_elem_name[t] = transition_name
        self.vp_elem_type[t] = 'transition'
        self.vp_transition_dummy[t] = dummy
        self.name_to_elem[transition_name] = t
        self.mark_as_modified()
        return t
    
    def add_place(self, place_name):
        """Adds the given place to the graph, if not previously added. The 
        place (either existent or new) is returned."""
        if place_name in self.name_to_elem:
            return self.name_to_elem[place_name]
        p = self.g.add_vertex()
        self.vp_elem_name[p] = place_name
        self.vp_elem_type[p] = 'place'
        self.name_to_elem[place_name] = p
        self.mark_as_modified()
        return p

    def add_edge(self, source, target, weight=1):
        """Adds a weighted edge between source and target elements. 
        The edge is returned.
        """
        s = self.get_elem(source)
        t = self.get_elem(target)
        e = self.g.add_edge(s, t)
        self.ep_edge_weight[e] = weight
        self.mark_as_modified()
        return e

    def set_initial_marking(self, place, tokens):
        p = self.get_elem(place)
        self.vp_place_initial_marking[p] = tokens
        
    def to_initial_marking(self):
        """Copy initial marking to current marking"""
        for p in self.get_places(names=False):
            self.vp_current_marking[p] = self.vp_place_initial_marking[p]

    def is_transition_enabled(self, t):
        """Computes whether transition [t] is enabled in the current marking"""
        for e in self.get_elem(t).in_edges():
            p = e.source()
            if self.vp_current_marking[p] < self.ep_edge_weight[e]:
                return False # This precondition is not satisfied
        return True # All preconditions are satisfied

    def enabled_transitions(self, names=True):
        """Computes the set of enabled transitions in the current marking.
        If [names] then the set contains the transition names, otherwise
        it contains the objects."""
        set_enabled = []
        for t in self.get_transitions(names=False):
            if self.is_transition_enabled(t):
                if names:
                    set_enabled.append( self.vp_elem_name[t] )
                else:
                    set_enabled.append( t )
        return set_enabled
    
    def fire_transition(self, t):
        """Modifies the current marking to reflect the firing of t. 
        Precondition: t must be enabled"""
        t = self.get_elem(t)
        for e in t.in_edges():
            p = e.source()
            self.vp_current_marking[p] -= self.ep_edge_weight[e]
        for e in t.out_edges():
            p = e.target()
            self.vp_current_marking[p] += self.ep_edge_weight[e]

    def simulate(self, length, names=True):
        """Return a list of transitions of at most the given [length] obtained 
        by simulation of the PN from the current marking."""
#        enabled_transitions = self.enabled_transitions()
#        print "enabled transitions: ", enabled_transitions
        seq = []
        for i in range(length):
            enabled_transitions = self.enabled_transitions(names=False)
            #print "enabled transitions: ", enabled_transitions
            if len(enabled_transitions) == 0:
                break 
            selected = randint(0,len(enabled_transitions)-1)
            t = enabled_transitions[selected]
            if names:
                seq.append(self.vp_elem_name[t])
            else:
                seq.append(t)
            self.fire_transition(t)
            #print enabled_transitions[selected], 
        #print
        return seq
    
    def set_capacity(self, place, tokens):
        """Sets the capacity of [place] to [tokens]"""
        p = self.get_elem(place)
        self.vp_place_capacity[p] = tokens
    
    def get_transitions(self, names=True):
        """Returns the set of transitions of this PN. If [names], then
        the transition names are returned, rather than the objects"""
        if names:
            return [self.vp_elem_name[v] for v in self.g.vertices() 
                if self.vp_elem_type[v] == 'transition']
        else:
            return [v for v in self.g.vertices() 
                if self.vp_elem_type[v] == 'transition']
    
    def get_transitions_without_places(self, names=True):
        """Returns the set of unconnected transitions of this PN. If [names], 
        then the transition names are returned, rather than the objects"""
        if names:
            return [self.vp_elem_name[v] for v in self.g.vertices() 
                if self.vp_elem_type[v] == 'transition' and 
                v.in_degree() == 0 and v.out_degree()== 0]
        else:
            return [v for v in self.g.vertices() 
                if self.vp_elem_type[v] == 'transition' and 
                v.in_degree() == 0 and v.out_degree()== 0]
    
    def get_transitions_with_places(self, names=True):
        """Returns the set of connected transitions (i.e. transitions with 
        places) of this PN. If [names], then the transition names are returned,
        rather than the objects"""
        if names:
            return [self.vp_elem_name[v] for v in self.g.vertices() 
                if self.vp_elem_type[v] == 'transition' and 
                (v.in_degree() != 0 or v.out_degree()!= 0)]
        else:
            return [v for v in self.g.vertices() 
                if self.vp_elem_type[v] == 'transition' and 
                (v.in_degree() != 0 or v.out_degree()!= 0)]
    
    def get_places(self, names=True):
        """Returns the set of places of this PN. If [names], then
        the places names are returned, rather than the objects"""
        if names:
            return [self.vp_elem_name[v] for v in self.g.vertices() 
                if self.vp_elem_type[v] == 'place']
        else:
            return [v for v in self.g.vertices() 
                if self.vp_elem_type[v] == 'place']
    
    def draw(self, filename, engine='cairo'):
        """Draws the TS. The filename extension determines the format.
        [engine] Rendering engine used to draw the TS. Valid values:
            cairo, graphviz, astg (for draw_astg)
        If [use_graphviz] is False, then Cairo is used to draw the graf. In such
        a case, if [filename] is None, then the interactive window is used"""
        if engine == 'graphviz':
            pass
        elif engine=='cairo': #use cairo
            pos = gt.sfdp_layout(self.g)
            names = self.vp_elem_name.copy()
            shapes = self.vp_elem_type.copy()
            color = self.g.new_vertex_property("vector<double>")
            for v in self.g.vertices():
                if self.vp_elem_type[v] == 'place':
                    if self.vp_place_initial_marking[v] > 0:
                        names[v] = str(self.vp_place_initial_marking[v])
                    else:
                        names[v] = ''
                if shapes[v] == 'place':
                    shapes[v] = 'circle'
                else:
                    shapes[v] = 'square'
                if self.vp_elem_type[v] == 'place':
                    color[v] = [0.7,0.2,0.2,0.9]
                else:
                    color[v] = [0.2,0.2,0.7,0.9]
            vprops = {'text':names, 'shape':shapes, 'fill_color':color}
#            if 'frequency' in self.g.vertex_properties:
#                vp_width = self.g.new_vertex_property("float")
#                all_traces = self.vp_state_frequency[self.get_state(self.get_initial_state())]
#                #use numpy array access 
##                vp_widht.a = int(max(100.0*self.vp_state_frequency.a/all_traces)
#                for v in self.g.vertices():
#                    vp_width[v] = int(100.0*self.vp_state_frequency[v]/all_traces)
#                vprops['size'] = vp_width
            gt.graph_draw(self.g, pos=pos, vprops=vprops, output=filename)
        elif engine=='astg':
            if filename.endswith('.ps'):
                format = '-Tps'
            elif filename.endswith('.gif'):
                format = '-Tgif'
            elif filename.endswith('.dot'):
                format = '-Tdot'
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
            params = ['draw_astg', '-sg', '-nonames', '-noinfo', format, input_filename]
            output = subprocess.check_output( params )
            with open(filename,'w+b') as f:
                f.write(output)
        else:
            raise ValueError, "Unknown graphical engine"

    def save(self, filename, format='sis'):
        """Save PN in the specified format to [filename].
        
        [filename]: file or filename in which the PN has to be written
        [format]: supported formats are:
            'sis': SIS format (used by petrify, STG, etc.)
            'pnml': PNML format
        """
        if format == 'sis':
            return self.save_as_sis(filename)
        elif format == 'pnml':
            return self.save_as_pnml(filename)
        else:
            raise TypeError, "Invalid format for the PetriNet.save function"

    def save_as_sis(self, filename, temporary = False):
        """Save PN in SIS format to [filename].
        
        [filename]: file or filename in which the PN has to be written
        [temporary]: whether it is being saved temporarily (if True, keep dirty state)"""
        own_fid = False
        if isinstance(filename, basestring): #a filename
            file = open(filename,'w')
            own_fid = True
        else:
            file = filename
            filename = file.name
        if not self.gp_name[self.g]:
            self.gp_name[self.g] = "pn"

        def clean(name):
            cleaned = "".join(c for c in name if c.isalpha() or c.isdigit() or c in ('_'))
            assert len(cleaned) > 0
            if not cleaned[0].isalpha(): cleaned = "s" + cleaned
            return cleaned

        print >> file, ".model",self.gp_name[self.g]

        transitions = [v for v in self.g.vertices() if self.vp_elem_type[v] == 'transition']
        outputs = ' '.join(clean(self.vp_elem_name[v]) for v in transitions if not self.vp_transition_dummy[v])
        if outputs:
            print >> file, ".outputs", outputs
        dummy = ' '.join(clean(self.vp_elem_name[v]) for v in transitions if self.vp_transition_dummy[v])
        if dummy:
            print >> file, ".dummy", dummy

        print >> file, ".graph"
        used_transitions = set()
        for e in self.g.edges():
            print >> file, clean(self.vp_elem_name[e.source()]), clean(self.vp_elem_name[e.target()]),
            if self.ep_edge_weight[e] > 1:
                print >> file, "(%d)" % self.ep_edge_weight[e]
            else:
                print >> file
            t = (self.vp_elem_name[e.target()] if 
                    self.vp_elem_type[e.target()] == 'transition' else
                    self.vp_elem_name[e.source()])
            used_transitions.add(t)
        all_transitions = set(self.vp_elem_name[v] for v in transitions)
        for t in all_transitions - used_transitions:
            print >> file, clean(t)
        capacity = []
        for p in self.get_places(names=False):
            name = clean(self.vp_elem_name[p])
            tokens = self.vp_place_capacity[p]
            if tokens > 1:
                capacity.append("{0}={1}".format(name, tokens))
        if capacity:
            print >> file, ".capacity ",' '.join(capacity)
        marking = []
        for p in self.get_places(names=False):
            name = clean(self.vp_elem_name[p])
            tokens = self.vp_place_initial_marking[p]
            if tokens == 1:
                marking.append(name)
            elif tokens > 1:
                marking.append("{0}={1}".format(name, tokens))
        if marking:
            print >> file, ".marking {",' '.join(marking),"}"
        print >> file, ".end"
        if not temporary:
            self.filename = filename
            self.last_write_format = 'sis'
            self.mark_as_modified(False)
        if own_fid:
            file.close()

    def save_as_pnml(self, filename):
        """Save PN in PNML format to [filename].
        
        [filename]: file or filename in which the PN has to be written"""
        own_fid = False
        if isinstance(filename, basestring): #a filename
            file = open(filename,'w')
            self.filename = filename
            own_fid = True
        else:
            file = filename
            self.filename = file.name

        if not self.gp_name[self.g]:
            self.gp_name[self.g] = self.filename

        def add_text(element, text):
            xmltree.SubElement(element, '{http://www.pnml.org/version-2009/grammar/pnml}text').text = text

        def add_name(element, text):
            add_text(xmltree.SubElement(element, '{http://www.pnml.org/version-2009/grammar/pnml}name'), text)

        xmltree.register_namespace("pnml", "http://www.pnml.org/version-2009/grammar/pnml")
        root = xmltree.Element('{http://www.pnml.org/version-2009/grammar/pnml}pnml')
        net = xmltree.SubElement(root, '{http://www.pnml.org/version-2009/grammar/pnml}net', {
                '{http://www.pnml.org/version-2009/grammar/pnml}id': 'net1',
                '{http://www.pnml.org/version-2009/grammar/pnml}type': 'http://www.pnml.org/version-2009/grammar/pnmlcoremodel'
            })
        add_name(net, self.gp_name[self.g])
        page = xmltree.SubElement(net, '{http://www.pnml.org/version-2009/grammar/pnml}page', {
                '{http://www.pnml.org/version-2009/grammar/pnml}id': 'n0'
            })

        node_num = 1
        id_map = {}
        for p in self.get_places(names=False):
            name = self.vp_elem_name[p]
            xml_id = "n%d" % node_num
            node = xmltree.SubElement(page, '{http://www.pnml.org/version-2009/grammar/pnml}place',
                {'{http://www.pnml.org/version-2009/grammar/pnml}id': xml_id})
            add_name(node, name)

            tokens = self.vp_place_initial_marking[p]
            if tokens >= 1:
                marking = xmltree.SubElement(node, '{http://www.pnml.org/version-2009/grammar/pnml}initialMarking')
                add_text(marking, str(tokens))

            id_map[p] = xml_id
            node_num += 1

        for t in self.get_transitions(names=False):
            assert t not in id_map
            name = self.vp_elem_name[t]
            xml_id = "n%d" % node_num
            node = xmltree.SubElement(page, '{http://www.pnml.org/version-2009/grammar/pnml}transition',
                {'{http://www.pnml.org/version-2009/grammar/pnml}id': xml_id})
            add_name(node, name)

            id_map[t] = xml_id
            node_num += 1

        for e in self.g.edges():
            xml_id = "arc%d" % node_num
            node = xmltree.SubElement(page, '{http://www.pnml.org/version-2009/grammar/pnml}arc', {
                '{http://www.pnml.org/version-2009/grammar/pnml}id': xml_id,
                '{http://www.pnml.org/version-2009/grammar/pnml}source': id_map[e.source()],
                '{http://www.pnml.org/version-2009/grammar/pnml}target': id_map[e.target()]
                })
            add_name(node, "%d" % self.ep_edge_weight[e])

            node_num += 1

        tree = xmltree.ElementTree(root)
        tree.write(file, encoding='UTF-8', xml_declaration=True, default_namespace='http://www.pnml.org/version-2009/grammar/pnml')
        self.last_write_format = 'pnml'
        self.mark_as_modified(False)
        if own_fid:
            file.close()
