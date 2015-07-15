import csv
import re
import pydot
import collections
import copy
import os.path
from datetime import datetime
import simplejson as json
from .. log.reencoders import StpReencoder
from lxml import etree
from Tkinter import Tk
from __bpmn_diagram import bpmndi_model, dc_model, di_model
from __draw import BPMN_Draw
from __edit import BPMN_Edit
from __simulate import BPMN_Simulate
import __simulate as sim
from .. log import EnhancedLog

_root_graphics = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'graphics')

bpmn_model          = "http://www.omg.org/spec/BPMN/20100524/MODEL"
definitionsTag      = "{%s}definitions"%bpmn_model
processTag          = "{%s}process"%bpmn_model
startEventTag       = "{%s}startEvent"%bpmn_model
endEventTag         = "{%s}endEvent"%bpmn_model
intermCatchEventTag = "{%s}intermediateCatchEvent"%bpmn_model
intermThrowEventTag = "{%s}intermediateThrowEvent"%bpmn_model
taskTag             = "{%s}task"%bpmn_model
incomingTag         = "{%s}incoming"%bpmn_model
outgoingTag         = "{%s}outgoing"%bpmn_model
laneSetTag          = "{%s}laneSet"%bpmn_model
laneTag             = "{%s}lane"%bpmn_model
flowNodeRefTag      = "{%s}flowNodeRef"%bpmn_model
subProcessTag       = "{%s}subProcess"%bpmn_model
sequenceFlowTag     = "{%s}sequenceFlow"%bpmn_model
parallelGatewayTag  = "{%s}parallelGateway"%bpmn_model
exclusiveGatewayTag = "{%s}exclusiveGateway"%bpmn_model
inclusiveGatewayTag = "{%s}inclusiveGateway"%bpmn_model
bpmn_namespace = {"bpmn"   : bpmn_model,
                  "bpmndi" : bpmndi_model,
                  "dc"     : dc_model,
                  "di"     : di_model}

class BPMN:
    def __init__(self):
        self.name = "BPMN"
        self.filename = None # the filename if loaded or saved to disk
        self.targetNamespace = None
        self.processes = []
        self.diagrams  = [] # contains BPMNDI_Diagram
        self.internalname_to_elem = {} #maps each internal name to its element

    def new_process(self):
        proc = Process(self)
        self.processes.append(proc)
        self.internalname_to_elem[proc.internal_name] = proc
        return proc

    def del_process(self, proc):
        if proc in self.processes:
            self.processes.remove(proc)
            del self.internalname_to_elem[proc.internal_name]

    def add_diagram(self, diagram):
        if diagram not in self.diagrams:
            self.diagrams.append(diagram)
        return diagram

    def del_diagram(self, diagram):
        if diagram in self.diagrams:
            self.diagrams.remove(diagram)

    def duplicate(self):
        """Create a new instance of BPMN with exactly the same elements and
        connections than self"""
        return copy.deepcopy(self)

    def save(self, filename, format="xml"):
        """Stores the BPMN model in a file with the specified format."""
        if format == "xml":
            self._xml_serialize(filename)

    def _xml_serialize(self, filename):
        """Serializes the BPMN in the XML format"""
        root = etree.Element(definitionsTag, nsmap = bpmn_namespace)
        tgtNs = "default" if self.targetNamespace is None else self.targetNamespace
        root.set("targetNamespace", tgtNs)
        root.set("name", self.name)
        for proc in self.processes:
            proc_xml = proc._xml_serialize()
            root.extend(proc_xml)
        for diag in self.diagrams:
            xml_diag = diag._xml_serialize()
            root.append(xml_diag)
        with open(filename, "w") as xmlfile:
            xmlfile.write(etree.tostring(root, pretty_print=True))

    def draw(self):
        """Shows the BPMN in a new window"""
        root = Tk()
        app  = BPMN_Draw(root, self)
        root.mainloop()
        del app
        del root

    def edit(self):
        """Allows to edit the BPMN in a graphical interface"""
        root = Tk()
        app  = BPMN_Edit(root, self)
        root.mainloop()
        del app
        del root

    def simulate(self, log, start_key, end_key, time_format):
        """Simulate a log when the each event has a defined start time and end
        time.
        [log] must be an EnhancedLog with the needed data (start time and end time)
        [start_key] is the key-string of the field in which the start time is stored
        [end_key] is the key-string of the field in which the end time is stored
        [time_format] is a regular expression defining the format of the time. Look at
        https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior for more information"""
        if not isinstance(log, EnhancedLog):
            print "Error: The log must be an EnhancedLog to be able to simulate it"
            return
        valid, cases = sim.format_data(self, log, start_key, end_key, time_format)
        if not valid:
            print "Error: There are no cases with the needed data. Check the log and the parameters to the simulate function"
            return
        root  = Tk()
        app   = BPMN_Simulate(root, self, cases)
        root.mainloop()
        del app
        del root

    def simulate2(self, log, time_key, state_key, time_format, start_w="start", end_w="complete"):
        """Simulate a log when the each event has a defined start time and end
        time and, also, the start of the event and the end of the event are stored as
        separate events in the log.
        [log] must be an EnhancedLog with the needed data (start time and end time)
        [time_key] is the key-string of the field in which the time is stored
        [state_key] is the key-string of the field in which the state of the event is stored (state meaning if the event starts or ends)
        [time_format] is a regular expression defining the format of the time. Look at
        https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior for more information
        [start_w] is the word found in the state field defining an starting event
        [end_w] is the word found in the state field defining a finishing event"""
        if not isinstance(log, EnhancedLog):
            print "Error: The log must be an EnhancedLog to be able to simulate it"
            return
        valid, cases = sim.format_data2(self, log, time_key, state_key, time_format, start_w, end_w)
        if not valid:
            print "Error: There are no cases with the needed data. Check the log and the parameters to the simulate method"
            return
        root = Tk()
        app  = BPMN_Simulate(root, self, cases)
        root.mainloop()
        del app
        del root

class Process:
    """ Class for a BPMN diagram. The idea is that first all elements are declared
    and then their connections."""
    static_counter = 0
    def __init__(self, parent):
        self.parent = parent
        self.internal_name = "proc"+'{0}'.format(Process.static_counter)
        Process.static_counter += 1
        self.elements = []
        self.pools = []
        self.name = "Unnamed_Process"
        self.name_to_elem = {} #maps each given name to its element
        self.internalname_to_elem = {} #maps each internal name to its element
        #create Start and End events
        self.start_event = Event('start')
        self.end_event = Event('end')
        self.add_element(self.start_event)
        self.add_element(self.end_event)
        self.edge_info = collections.defaultdict(dict)
        #maps each edge (src,trg) to a dictionary in which edge info like edge
        #frequency) is stored
        self.node_info = collections.defaultdict(dict)
        #maps each node to a dictionary in which node info (like activity
        #durations) is stored

    def add_element(self, elem):
        """Add an element to the BPMN"""
        if elem.process is self:
            return elem
        if elem.parent is not None:
            elem.parent.del_element(elem)
        self.elements.append(elem)
        elem.parent  = self
        elem.process = self
        if elem.name is not None:
            self.name_to_elem[elem.name] = elem
        self.internalname_to_elem[elem.internal_name] = elem
        return elem

    def del_element(self, elem):
        """Deletes an element from the process and all its connections"""
        if elem.process is self:
            self.del_connection(elem.inset, elem)
            self.del_connection(elem, elem.outset)
            self.name_to_elem.pop(elem.name, None)
            self.internalname_to_elem.pop(elem.internal_name, None)
            self.elements.remove(elem)
            if elem.parent is not self:
                elem.parent.del_element(elem)
            elem.parent  = None
            elem.process = None

    def new_pool(self):
        """Add a pool to the process"""
        pool = Pool()
        self.pools.append(pool)
        pool.parent  = self
        pool.process = self
        self.internalname_to_elem[pool.internal_name] = pool
        return pool

    def del_pool(self, pool):
        """Deletes a pool from the process"""
        if pool in self.pools:
            for lane in pool.lanes:
                for elem in lane.elements:
                    elem.parent = elem.process
            self.pools.remove(pool)
            pool.parent  = None
            pool.process = None

    def del_pool_with_elements(self, pool):
        """Deletes a pool from the process and all the elements belonging to that pool"""
        if pool in self.pools:
            for lane in pool.lanes:
                for elem in lane.elements:
                    elem.process.del_element(elem)
            self.pools.remove(pool)
            pool.parent  = None
            pool.process = None

    def get_gateways(self, subtype=None):
        """Returns the list of gateway elements in the BPMN"""
        if subtype is None:
            return [elem for elem in self.elements if elem.type == 'gateway']
        return [elem for elem in self.elements if elem.type == 'gateway' and elem.subtype == subtype]

    def get_activities(self):
        """Returns the list of activity elements in the BPMN"""
        return [elem for elem in self.elements if elem.type == 'activity']

    def get_events(self):
        """Returns the list of event elements in the BPMN"""
        return [elem for elem in self.elements if elem.type == 'event']

    def elem_with_name(self, elem_name):
        """Returns the object with the given name. If not found, then
        it is searched using the internal name"""
        return self.name_to_elem.get(elem_name, None)

    def add_connection(self, source, target):
        """Connects source to target. Updates the data of both elements
        accordingly. If they are strings, the element is searched by name first.
        [source] and [target] can be iterables containing elements or element names
        too."""
        ns = self.name_to_elem[source] if isinstance(source,str) else source
        nt = self.name_to_elem[target] if isinstance(target,str) else target
        if not isinstance(ns, collections.Iterable):
            ns = [ns]
        if not isinstance(nt, collections.Iterable):
            nt = [nt]
        for src in ns:
            if src not in self.elements:
                continue
            nsrc = self.name_to_elem[src] if isinstance(src,str) else src
            for trg in nt:
                if trg not in self.elements:
                    continue
                ntrg = self.name_to_elem[trg] if isinstance(trg,str) else trg
                if ntrg not in nsrc.outset:
                    nsrc.outset.append(ntrg)
                if nsrc not in ntrg.inset:
                    ntrg.inset.append(nsrc)

    def del_connection(self, source, target):
        """Disconnects source to target. Updates the data of both elements accordingly.
        If they are strings, the element is searched by name first. [source] and [target]
        can be iterables containing elements or element names too."""
        ns = self.name_to_elem[source] if isinstance(source,str) else source
        nt = self.name_to_elem[target] if isinstance(target,str) else target
        if not isinstance(ns, collections.Iterable):
            ns = [ns]
        if not isinstance(nt, collections.Iterable):
            nt = [nt]
        for src in ns:
            if src not in self.elements:
                continue
            nsrc = self.name_to_elem[src] if isinstance(src,str) else src
            for trg in nt:
                if trg not in self.elements:
                    continue
                ntrg = self.name_to_elem[trg] if isinstance(trg,str) else trg
                if ntrg in nsrc.outset:
                    nsrc.outset.remove(ntrg)
                if nsrc in ntrg.inset:
                    ntrg.inset.remove(nsrc)

    def clear(self):
        """Erases all the contents of the bpmn"""
        self.elements = []
        self.name_to_elem = {}
        self.internalname_to_elem = {}
        self.start_event = Event('start')
        self.end_event = Event('end')
        self.add_element(self.start_event)
        self.add_element(self.end_event)
        self.edge_info = collections.defaultdict(dict)
        self.node_info = collections.defaultdict(dict)

    def add_duration_info(self, log,cols_to_read=None):
        """ Adds the mean duration found in the log. """
        if not('.csv' in log.filename):
            raise ValueError, 'Log is not in .csv format'
        orig_alp = list(log.get_alphabet())
        stp_enc = StpReencoder()
        enc_alp = map(stp_enc.reencode, orig_alp)
        same_alphabet = (orig_alp==enc_alp)

        reader = csv.reader(log.filename)
        # restricted format for the time being
        date_format = "%d.%m.%y %H:%M"
        if not cols_to_read:
            cols_to_read = [0,1,2,3]
        durations = {}
        with open(log.filename, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if (re.search("#",row[cols_to_read[0]]) or row[cols_to_read[1]] not in log.alphabet):
                    continue
                duration = datetime.strptime(row[cols_to_read[3]],date_format) - datetime.strptime(row[cols_to_read[2]],date_format)
                if (row[cols_to_read[1]] in durations):
                    durations[row[cols_to_read[1]]]['rep'] =  durations[row[cols_to_read[1]]]['rep'] + 1
                    durations[row[cols_to_read[1]]]['sum'] =  durations[row[cols_to_read[1]]]['sum'] + duration.total_seconds()
                else:
                    durations[row[cols_to_read[1]]] = {'rep':1,'sum':duration.total_seconds()}

            for act in durations.iterkeys():
                print act,':',durations[act]['sum']/durations[act]['rep'], ' seconds'

            d = collections.defaultdict(dict)
            for act,dact in durations.iteritems():
                dd = collections.defaultdict(float)
                dd['avg_duration'] = dact['sum']/dact['rep']
                d[stp_enc.reencode(act)] = dd
            self.add_activity_info(d)

    def add_frequency_info(self, log, bind_freq, case_level=True):
        """ Adds frequency information to the edges of the BPMN based on the
        number of cases going through each C-net binding.
        [log] log for which binding frequencies were computed.
        [bind_freq] 2-Tuple. Dictionary mapping each input/outupt binding to the
        set of unique cases IDs that make use of that binding. Allows computing
        edge percentages so that most frequent paths can be spot. Code assumes
        'multiset' binding frequencies are given (for case_level=True, 'set'
        frequencies should also work, but code does not expect it).
        [case_level] If True considers only the set of cases going through each
        activity, regardless of the number of times it is executed in the case.
        In this case, exclusive gateways percentages do not necessarily add at
        most 100%, since exclusive branches can be visited in the same case if
        there is a loop.
        If False, every decision is considered independently so exclusive
        gateways add 100%."""
        #compute first the number of cases that corresponds to each set of
        #unique cases
        num_cases = log.get_uniq_cases().values()
        #now num_cases[i] contains the number of cases associated to unique case i
        if case_level:
            act_set_cases = collections.defaultdict(set)
            oblig_set_cases = collections.defaultdict(set)
            #act_cases[act][0] is the number of cases in which this activity produces
            #   an obligation (act, _)
            #act_cases[act][1] is the number of cases in which this activity consumes
            #   an obligation (_, act)
            act_cases = collections.defaultdict(lambda : [0,0])
            oblig_cases = collections.defaultdict(int)
            for binding, occ_map in bind_freq[1].iteritems():
                case_set = set(occ_map.keys())
                act_set_cases[binding[0]] |= case_set
                for outact in binding[1]:
                    oblig_set_cases[(binding[0], outact)] |= case_set
            # to avoid problems with last activity (which does not appear in previous mapping
            for binding, occ_map in bind_freq[0].iteritems():
                case_set = set(occ_map.keys())
                act_set_cases[binding[0]] |= case_set

            for act, case_set in act_set_cases.iteritems():
                act_cases[act][0] = sum(num_cases[case] for case in case_set)
                act_cases[act][1] = act_cases[act][0] # not correct for S and E, but not a problem
            for obl, case_set in oblig_set_cases.iteritems():
                oblig_cases[obl] = sum(num_cases[case] for case in case_set)
        else:
            pr_bind_cases = {}
            for binding, case_set in bind_freq[1].iteritems():
                pr_bind_cases[binding] = sum(num_cases[case]*case_set[case] for case in case_set)
            #count, for each obligation (a,b), the fraction it represents over
            # (i) all obligations (a,_) and (ii) all obligations (_,b)
            oblig_cases = collections.defaultdict(int)
            act_cases = collections.defaultdict(lambda : [0,0])

            #we need to count only input or output bindings
            for binding, occ in pr_bind_cases.iteritems():
    #            if isinstance(binding[0], basestring):
                    #output binding
                for outact in binding[1]:
                    oblig_cases[(binding[0], outact)] += occ
                act_cases[binding[0]][0] += occ
            #print oblig_cases
            cn_bind_cases = {}
            for binding, case_set in bind_freq[0].iteritems():
                cn_bind_cases[binding] = sum(num_cases[case]*case_set[case] for case in case_set)
            for binding, occ in cn_bind_cases.iteritems():
                act_cases[binding[0]][1] += occ
        print 'act_cases:', act_cases
        #count the obligations for each activity act,
        #[0] is (act,_) [1] is (_,act)
#        for obl, occ in oblig_cases.iteritems():
#            act_cases[obl[0]][0] += occ
#            act_cases[obl[1]][1] += occ
        #print sorted(act_cases.items(), key=lambda x:x[1])
#            else:
#                #input binding
#                for inact in binding[0]:
#                    oblig_cases[(, binding[1])] += occ
        #now annotate each gateway (only the side in which there is more than
        #one edge)
        activities = self.get_activities()
        for act in activities:
            print 'Checking', act.name
            #check output edges, this should cover everything
#            ei_gateways = (elem for elem in act.outset if elem.type == 'gateway'
#                            and elem.subtype in ('exclusive','inclusive'))
            for elem in act.outset:#ei_gateways:
                if elem.type == 'gateway':
#                    #add info only to exclusive/inclusive
#                    if elem.subtype in ('exclusive','inclusive'):
                        #find next activity
                    for e2 in elem.outset:
                        if e2.type == 'activity':
                            obl = (act.name, e2.name)
                            print '\twith {0}: {3} {1:.1%} (for source) {2:.1%} (for target)'.format(e2.name,
                                                    1.0*oblig_cases[obl]/act_cases[act.name][0],
                                                    1.0*oblig_cases[obl]/act_cases[e2.name][1],
                                                    oblig_cases[obl])
                            einfo = self.edge_info[(act.internal_name, elem.internal_name)]
                            einfo['frequency'] = act_cases[act.name][0]
                            einfo = self.edge_info[(elem.internal_name, e2.internal_name)]
                            einfo['frequency'] = act_cases[e2.name][1]
                        else:
                            for e3 in e2.outset:
                                if e3.type == 'activity':
                                    obl = (act.name, e3.name)
                                    print '\twith {0}: {3} {1:.1%} {2:.1%}'.format(e3.name,
                                                            1.0*oblig_cases[obl]/act_cases[act.name][0],
                                                            1.0*oblig_cases[obl]/act_cases[e3.name][1],
                                                            oblig_cases[obl])
                                    einfo = self.edge_info[(act.internal_name,
                                                            elem.internal_name)]
                                    einfo['frequency'] = act_cases[act.name][0]
                                    einfo = self.edge_info[(elem.internal_name,
                                                            e2.internal_name)]
                                    einfo['frequency'] = oblig_cases[obl]
                                    einfo = self.edge_info[(e2.internal_name,
                                                            e3.internal_name)]
                                    einfo['frequency'] = act_cases[e3.name][1]
                elif elem.type == 'activity':
                    einfo = self.edge_info[(act.internal_name, elem.internal_name)]
                    einfo['frequency'] = act_cases[act.name][0]

    def add_activity_info(self, actinfo):
        """Adds activity information for each activity.

        [actinfo] a dictionary that maps each activity to a dictionary
        containing information of the activity. e.g. min/max/average durations.
        If it is a string, it is assumed that it is a filename containing the
        previous information in JSON format."""
        if isinstance(actinfo, basestring):
            with open(actinfo) as f:
                info = json.load(f)
        else:
            info = actinfo
        for act, d in info.iteritems():
            self.node_info[act].update(d)

    def translate_activity_names(self, dictionary):
        """Changes the names of the activities according to the mapping in
        [dictionary], which is a dictionary from strings to strings.
        Activity names not present in the dictionary, will remain unchanged."""
        activities = self.get_activities()
        for act in activities:
            if self.name_to_elem[act.name] is act:
                self.name_to_elem[act.name] = None
            act.name = dictionary.get(act.name, act.name)
            self.name_to_elem[act.name] = act

    def print_debug(self):
        for e in self.elements:
            e.print_debug()

    def print_dot(self, filename, use_graphics=True):
        """Saves BPMN in dot format.
        [use_graphics] Use special ps images to generate the gateway symbols
            (the files must be reachable)."""
        try:
            max_cases = max(einfo['frequency'] for einfo in self.edge_info.itervalues()
                        if 'frequency' in einfo)
        except Exception:
            pass #no frequency information
        try:
            avg_durations = [ninfo['avg_duration'] for ninfo in self.node_info.itervalues()
                        if 'avg_duration' in ninfo]
            global_avg = sum(avg_durations)/len(avg_durations)
            print 'Activity average duration:', global_avg
        except Exception:
            pass #no frequency information
        g = pydot.Dot(graph_type='digraph', splines="ortho") #ranksep="4.0",
        for e in self.elements:
            n = e.dot_node(use_graphics)
            if e.type == 'activity' and 'avg_duration' in self.node_info[e.name]:
                avg = self.node_info[e.name]['avg_duration']
                h = max(0.15+0.15*(global_avg-avg)/(1.0*global_avg),0)
                n.set_fillcolor('"{0} 0.9 1.0"'.format(h))
                n.set_label('"{0} ({1:.1f})"'.format(n.get_label()[1:-1],avg))
                #print n.get_label(),' ',h
            g.add_node(n)
            for out in e.outset:
                einfo = self.edge_info[(e.internal_name, out.internal_name)]
                if 'frequency' in einfo:
                    edge = pydot.Edge(e.internal_name, out.internal_name,
                                    penwidth=str(20.0*einfo['frequency']/max_cases))
                else:
                    edge = pydot.Edge(e.internal_name, out.internal_name)
                g.add_edge(edge)
        g.write(filename,format='raw')

    def _xml_serialize(self):
        process_xml = etree.Element(processTag)
        process_xml.set("id", self.internal_name)
        process_xml.set("name", self.name)
        for pool in self.pools:
            pool_xml = pool._xml_serialize()
            process_xml.extend(pool_xml)
        for elem in self.elements:
            elem_xml = elem._xml_serialize()
            process_xml.extend(elem_xml)
        return [process_xml]

class BPMN_Element(object):
    def __init__(self, name=None):
        self.type = 'bpmn_element'
        self.inset = [] # set of elements connected to its input
        self.outset = [] # set of elements connected to its output
        self.internal_name = ''
        self.name = name
        self.parent  = None
        self.process = None

    def _xml_serialize(self):
        raise NotImplementedError("The XML serializer function has not been implemented")

    def print_debug(self):
        if hasattr(self,'name'):
            print 'name:', self.name
        print 'internal name:', self.internal_name
        print 'inset:', ' '.join([e.internal_name for e in self.inset])
        print 'outset:', ' '.join([e.internal_name for e in self.outset])

class Event(BPMN_Element):
    width  = 25
    height = 25
    color  = "#FF8928"
    start_color = "#55AA55"
    end_color   = "#AA3939"
    static_counter = 0
    allowed_subtypes = ['intermediate','start','end']
    def __init__(self, subtype, name=None, catch=True):
        super(Event,self).__init__(name)
        self.type = 'event'
        self.subtype = subtype
        if self.subtype == "start":
            self.color = self.start_color
        elif self.subtype == "end":
            self.color = self.end_color
        self.internal_name = self.type+'{0}'.format(Event.static_counter)
        self.catch = True if catch else False
        Event.static_counter += 1

    def change_subtype(self, newsubtype):
        self.subtype = newsubtype
        if self.subtype == "start":
            self.color = self.start_color
        elif self.subtype == "end":
            self.color = self.end_color
        else:
            self.color = Event.color

    def _xml_serialize(self):
        if self.subtype not in self.allowed_subtypes:
            raise RuntimeError("Element has a non-allowed atribute")
        if self.subtype == "start":
            xml_node = etree.Element(startEventTag)
        elif self.subtype == "end":
            xml_node = etree.Element(endEventTag)
        elif self.subtype == "intermediate":
            if self.catch:
                xml_node = etree.Element(intermCatchEventTag)
            else:
                xml_node = etree.Element(intermThrowEventTag)
        retnodes = [xml_node]
        xml_node.set("id", self.internal_name)
        if self.name is not None:
            xml_node.set("name", self.name)
        for inelem in self.inset: # generate the sequenceFlow nodes for its input edges
            seq_flow    = etree.Element(sequenceFlowTag)
            seq_flow_id = inelem.internal_name+"_"+self.internal_name
            seq_flow.set("sourceRef", inelem.internal_name)
            seq_flow.set("targetRef", self.internal_name)
            seq_flow.set("id", seq_flow_id)
            retnodes.append(seq_flow)
            incoming = etree.Element(incomingTag)
            incoming.text = seq_flow_id
            xml_node.append(incoming)
        for outelem in self.outset:
            seq_flow_id = self.internal_name+"_"+outelem.internal_name
            outgoing = etree.Element(outgoingTag)
            outgoing.text = seq_flow_id
            xml_node.append(outgoing)
        return retnodes

    def print_debug(self):
        print self.subtype+' '+self.type
        super(Event,self).print_debug()

    def dot_node(self, use_graphics=False):
        style = 'filled'
        if self.subtype == 'end':
            style += ', bold'
            fillcolor = "0.0 0.2 1.0"
        else:
            fillcolor = "0.3 0.2 1.0"
        return pydot.Node('{0}'.format(self.internal_name), shape='circle', style=style,
                                label=" ",fillcolor=fillcolor)

class Activity(BPMN_Element):
    width  = 25
    height = 25
    color  = "#FCCDA6"
    static_counter = 0
    allowed_subtypes = ['task']
    def __init__(self, name=None, subtype="task"):
        super(Activity,self).__init__(name)
        self.type = 'activity'
        self.subtype = 'task'
        self.internal_name = self.type+'{0}'.format(Activity.static_counter)
        Activity.static_counter += 1

    def change_subtype(self, newsubtype):
        self.subtype = newsubtype

    def _xml_serialize(self):
        if self.subtype not in self.allowed_subtypes:
            raise RuntimeError("Element has a non-allowed atribute")
        if self.subtype == "task":
            xml_node = etree.Element(taskTag)
        retnodes = [xml_node]
        xml_node.set("id", self.internal_name)
        if hasattr(self,'name') and self.name is not None:
            xml_node.set("name", self.name)
        for inelem in self.inset: # generate the sequenceFlow nodes for its input edges
            seq_flow    = etree.Element(sequenceFlowTag)
            seq_flow_id = inelem.internal_name+"_"+self.internal_name
            seq_flow.set("sourceRef", inelem.internal_name)
            seq_flow.set("targetRef", self.internal_name)
            seq_flow.set("id", seq_flow_id)
            retnodes.append(seq_flow)
            incoming = etree.Element(incomingTag)
            incoming.text = seq_flow_id
            xml_node.append(incoming)
        for outelem in self.outset:
            seq_flow_id = self.internal_name+"_"+outelem.internal_name
            outgoing = etree.Element(outgoingTag)
            outgoing.text = seq_flow_id
            xml_node.append(outgoing)
        return retnodes

    def print_debug(self):
        print self.subtype+' '+self.type
        super(Activity,self).print_debug()

    def dot_node(self, use_graphics=False):
        return pydot.Node('{0}'.format(self.internal_name), shape='box', style='rounded, filled',
                                label='"{0}"'.format(self.name),
                                fillcolor="0.2 0.2 1.0")

class Gateway(BPMN_Element):
    width  = 25
    height = 25
    color  = "#A1AECB"
    static_counter = 0
    allowed_subtypes = ['exclusive','inclusive','parallel']
    #sequential execution is implicit when two activities are immediately
    #one after the other
    def __init__(self, subtype, name=None):
        super(Gateway,self).__init__(name)
        self.type = 'gateway'
        self.subtype = subtype
        self.internal_name = self.type+'{0}'.format(Gateway.static_counter)
        Gateway.static_counter += 1

    def change_subtype(self, newsubtype):
        self.subtype = newsubtype

    def _xml_serialize(self):
        if self.subtype not in self.allowed_subtypes:
            raise RuntimeError("Element has a non-allowed atribute")
        elif self.subtype == "exclusive":
            xml_node = etree.Element(exclusiveGatewayTag)
        elif self.subtype == "inclusive":
            xml_node = etree.Element(inclusiveGatewayTag)
        elif self.subtype == "parallel":
            xml_node = etree.Element(parallelGatewayTag)
        retnodes = [xml_node]
        xml_node.set("id", self.internal_name)
        if hasattr(self,'name') and self.name is not None:
            xml_node.set("name", self.name)
        for inelem in self.inset: # generate the sequenceFlow nodes for its input edges
            seq_flow    = etree.Element(sequenceFlowTag)
            seq_flow_id = inelem.internal_name+"_"+self.internal_name
            seq_flow.set("sourceRef", inelem.internal_name)
            seq_flow.set("targetRef", self.internal_name)
            seq_flow.set("id", seq_flow_id)
            retnodes.append(seq_flow)
            incoming = etree.Element(incomingTag)
            incoming.text = seq_flow_id
            xml_node.append(incoming)
        for outelem in self.outset:
            seq_flow_id = self.internal_name+"_"+outelem.internal_name
            outgoing = etree.Element(outgoingTag)
            outgoing.text = seq_flow_id
            xml_node.append(outgoing)
        return retnodes

    def print_debug(self):
        print self.subtype+' '+self.type
        super(Gateway,self).print_debug()

    def dot_node(self, use_graphics=True):
        if self.subtype == 'exclusive':
            sign = 'X'
            file = os.path.join(_root_graphics, 'bpmn_exclusive.eps')
        elif self.subtype == 'inclusive':
            sign = 'O'
            file = os.path.join(_root_graphics, 'bpmn_inclusive.eps')
        elif self.subtype == 'parallel':
            sign = '+'
            file = os.path.join(_root_graphics, 'bpmn_parallel.eps')
        else:
            sign = 'unknown'
        if use_graphics:
            return pydot.Node('{0}'.format(self.internal_name), image=file, shape='diamond',
                            style='filled', label=" ", fillcolor="0.5 0.1 0.8",
                            fixedsize="true", width="0.7", height="0.7", margin="0.0")
        return pydot.Node('{0}'.format(self.internal_name), shape='diamond', style='filled',
                                label='"{0}"'.format(sign), fillcolor="0.5 0.1 0.8")

class Pool:
    width  = 100
    height = 5
    color  = "blue"
    static_counter = 0
    def __init__(self):
        self.type = 'pool'
        self.parent  = None
        self.process = None
        self.internal_name = self.type+'{0}'.format(Pool.static_counter)
        Pool.static_counter += 1
        self.lanes = []

    def new_lane(self, name=None):
        lane = Lane(name)
        lane.parent  = self
        lane.process = self.process
        self.lanes.append(lane)
        self.process.internalname_to_elem[lane.internal_name] = lane
        return lane

    def del_lane(self, lane):
        if lane in self.lanes:
            for elem in lane.elements:
                elem.parent = elem.process
            self.lanes.remove(lane)
            lane.parent  = None
            lane.process = None

    def del_lane_with_elements(self, lane):
        """Deletes a lane from the pool and all the elements belonging to that pool"""
        if lane in self.lanes:
            for elem in lane.elements:
                elem.process.del_element(elem)
            self.lanes.remove(lane)
            lane.parent  = None
            lane.process = None

    def _xml_serialize(self):
        xml_node = etree.Element(laneSetTag)
        xml_node.set("id", self.internal_name)
        for lane in self.lanes:
            lane_xml = lane._xml_serialize()
            xml_node.extend(lane_xml)
        return [xml_node]

class Lane:
    width  = 100
    height = 5
    color  = "#7878FD"
    static_counter = 0
    def __init__(self, name=None):
        self.name = name
        self.type = 'lane'
        self.parent  = None
        self.process = None
        self.internal_name = self.type+'{0}'.format(Lane.static_counter)
        Lane.static_counter += 1
        self.name_to_elem = {}
        self.internalname_to_elem = {}
        self.elements = []

    def add_element(self, elem):
        """Add an element to the lane"""
        if elem.parent is self:
            return elem
        if elem.parent is not None:
            elem.parent.del_element(elem)
        self.process.add_element(elem)
        self.elements.append(elem)
        elem.parent = self
        if elem.name is not None:
            self.name_to_elem[elem.name] = elem
        self.internalname_to_elem[elem.internal_name] = elem
        return elem

    def del_element(self, elem):
        """Deletes an element from the lane"""
        if elem.parent is self:
            self.name_to_elem.pop(elem.name, None)
            self.internalname_to_elem.pop(elem.internal_name, None)
            self.elements.remove(elem)
            elem.parent = self.process

    def get_gateways(self, subtype=None):
        """Returns the list of gateway elements in the lane"""
        if subtype is None:
            return [elem for elem in self.elements if elem.type == 'gateway']
        return [elem for elem in self.elements if elem.type == 'gateway' and elem.subtype == subtype]

    def get_activities(self):
        """Returns the list of activity elements in the lane"""
        return [elem for elem in self.elements if elem.type == 'activity']

    def get_events(self):
        """Returns the list of event elements in the lane"""
        return [elem for elem in self.elements if elem.type == 'event']

    def _xml_serialize(self):
        xml_node = etree.Element(laneTag)
        xml_node.set("id", self.internal_name)
        if self.name is not None:
            xml_node.set("name", self.name)
        for elem in self.elements:
            elem_xml = etree.Element(flowNodeRefTag)
            elem_xml.text = elem.internal_name
            xml_node.append(elem_xml)
        return [xml_node]

class Subprocess(BPMN_Element, Process):
    width  = 25
    height = 25
    color  = "#FCCDA6"
    static_counter = 0
    def __init__(self, name=None):
        BPMN_Element.__init__(self, name)
        Process.__init__(self)
        self.type = 'subprocess'
        self.internal_name = self.type+'{0}'.format(Subprocess.static_counter)
        Subprocess.static_counter += 1

    def _xml_serialize(self):
        subprocess_xml = etree.Element(subProcessTag)
        retnodes = [subprocess_xml]
        subprocess_xml.set("id", self.internal_name)
        if hasattr(self,'name') and self.name is not None:
            subprocess_xml.set("name", self.name)
        for inelem in self.inset:
            seq_flow    = etree.Element(sequenceFlowTag)
            seq_flow_id = inelem.internal_name+"_"+self.internal_name
            seq_flow.set("sourceRef", inelem.internal_name)
            seq_flow.set("targetRef", self.internal_name)
            seq_flow.set("id", seq_flow_id)
            retnodes.append(seq_flow)
            incoming = etree.Element(incomingTag)
            incoming.text = seq_flow_id
            subprocess_xml.append(incoming)
        for outelem in self.outset:
            seq_flow_id = inelem.internal_name+"_"+self.internal_name
            outgoing = etree.Element(outgoingTag)
            outgoing.text = seq_flow_id
            subprocess_xml.append(outgoing)
        elems = list(self.elements)
        for elem in self.elements:
            if elem.type == "pool":
                elems.extend(elem.get_elements())
            elem_xml = elem._xml_serialize()
            subprocess_xml.extend(elem_xml)
        return retnodes
