from __bpmn import *
from __bpmn_diagram import read_bpmndi_diagram_from_xml, bpmndiDiagramTag
from .. import cnet
from lxml import etree

_xsd_file   = "http://www.omg.org/spec/BPMN/20100501/BPMN20.xsd"

def bpmn_from_cnet(net):
    """Converts a Cnet to a BPMN diagram."""
    bp = BPMN()
    b = bp.new_process()
    print net.activities
    for act in net.activities:
        b.add_element(Activity(act))
    start_act = net.starting_activities()
    if len(start_act) == 1:
        b.add_connection(b.start_event, start_act[0])
    else:
        #TODO: create a parallel
        pass
    #each activity has a single pre and post element that can be eiter a gw or another activity
    #depending on the structure of its bindings
    elem_out = {}
    elem_in = {}
    for act in net.activities:
        #creation of gateways
        ##outsets
        if len(net.outset[act]) == 1:
            for oset in net.outset[act]:
                #print 'oset:', oset, 'len:', len(oset)
                if len(oset) == 1:
                    elem_out[act] = act
                else:
                    elem_out[act] = b.add_element( Gateway('parallel') )
                    b.add_connection(act, elem_out[act])
        elif len(net.outset[act]) > 1:
            outsets = list(net.outset[act])
            pairwise_disjoint = True
            for i, oset1 in enumerate(outsets):
                for oset2 in outsets[i+1:]:
                    if len(oset1 & oset2) > 0:
                        pairwise_disjoint = False
                        break
            if pairwise_disjoint:
                #print act, 'has pairwise disjoint outsets'
                elem_out[act] = b.add_element( Gateway('exclusive') )
                b.add_connection(act, elem_out[act])
            else:
#                common = outsets[0].intersection(outsets[1:])
#                if len(common) == 0:
                elem_out[act] = b.add_element( Gateway('inclusive') )
                b.add_connection(act, elem_out[act])
#                else:
#                    print "Common outset elements for '{0}':".format(act), commmon
        ##insets
        if len(net.inset[act]) == 1:
            for iset in net.inset[act]:
                #print 'oset:', oset, 'len:', len(oset)
                if len(iset) == 1:
                    elem_in[act] = act
                else:
                    elem_in[act] = b.add_element( Gateway('parallel') )
                    b.add_connection( elem_in[act], act)
        elif len(net.inset[act]) > 1:
            insets = list(net.inset[act])
            pairwise_disjoint = True
            for i, iset1 in enumerate(insets):
                for iset2 in insets[i+1:]:
                    if len(iset1 & iset2) > 0:
                        pairwise_disjoint = False
                        break
            if pairwise_disjoint:
                #print act, 'has pairwise disjoint outsets'
                elem_in[act] = b.add_element( Gateway('exclusive') )
                b.add_connection(elem_in[act], act)
            else:
#                common = insets[0].intersection(insets[1:])
#                if len(common) == 0:
                elem_in[act] = b.add_element( Gateway('inclusive') )
                b.add_connection(elem_in[act], act)
#                else:
#                    print "Common inset elements for '{0}':".format(act), commmon

    for act in net.activities:
        for oset in net.outset[act]:
            for opp in oset:
                b.add_connection(elem_out[act], elem_in[opp])

    end_act = net.final_activities()
    if len(end_act) == 1:
        b.add_connection(end_act[0], b.end_event )
    else:
        #TODO: create a parallel
        pass
    return bp

def bpmn_from_log(log,log_percentage=None,minimal_case_length=None,add_frequency=None):
	if (minimal_case_length):
		log = pmlab.log.filters.filter_log(log,pmlab.log.filters.CaseLengthFilter(above=minimal_case_length))
	if (log_percentage):
		log = pmlab.log.filters.filter_log(log,pmlab.log.filters.FrequencyFilter(log,log_min_freq=log_percentage))
	clog = cnet.condition_log_for_cnet(log)
	skeleton = cnet.flexible_heuristic_miner(clog)
	cn,bf = cnet.cnet_from_log(clog,skeleton=skeleton)
	bp = bpmn_from_cnet(cn)
	if (add_frequency):
		bp.add_frequency_info(clog,bf)
	return bp

_isProcess          = lambda node : node.tag == processTag
_isStartEvent       = lambda node : node.tag == startEventTag
_isEndEvent         = lambda node : node.tag == endEventTag
_isIntermCatchEvent = lambda node : node.tag == intermCatchEventTag
_isIntermThrowEvent = lambda node : node.tag == intermThrowEventTag
_isTask             = lambda node : node.tag == taskTag
_isLaneSet          = lambda node : node.tag == laneSetTag
_isLane             = lambda node : node.tag == laneTag
_isFlowNodeRef      = lambda node : node.tag == flowNodeRefTag
_isSubProcess       = lambda node : node.tag == subProcessTag
_isSequenceFlow     = lambda node : node.tag == sequenceFlowTag
_isParallelGateway  = lambda node : node.tag == parallelGatewayTag
_isExclusiveGateway = lambda node : node.tag == exclusiveGatewayTag
_isInclusiveGateway = lambda node : node.tag == inclusiveGatewayTag
_isBPMNDIDiagram    = lambda node : node.tag == bpmndiDiagramTag

_isIncoming = lambda connection : connection.tag == incomingTag
_isOutgoing = lambda connection : connection.tag == outgoingTag

def _deserialize_process(process, process_node, id_to_elem, edges):
    # edges is used for storing the edge_id - edge_pair relations needed in the
    # deserialization of the BPMN diagram

    proc_id   = process_node.get("id")
    proc_name = process_node.get("name")
    id_to_elem[proc_id] = process
    if proc_name is not None:
        process.name = proc_name

    # first iteration: creates all the elements and stores the map between
    # the xml id and the bpmn element
    for node in process_node.getchildren():
        node_id = node.get("id")
        node_name = node.get("name")
        if _isStartEvent(node):
            process.start_event.name = node_name
            id_to_elem[node_id] = process.start_event

        elif _isEndEvent(node):
            process.end_event.name = node_name
            id_to_elem[node_id] = process.end_event

        elif _isIntermCatchEvent(node):
            event = Event("intermediate", node_name, catch=True)
            id_to_elem[node_id] = event
            process.add_element(event)

        elif _isIntermThrowEvent(node):
            event = Event("intermediate", node_name, catch=False)
            id_to_elem[node_id] = event
            process.add_element(event)

        elif _isTask(node):
            task = Activity(node_name)
            id_to_elem[node_id] = task
            process.add_element(task)

        elif _isParallelGateway(node):
            gateway = Gateway("parallel", node_name)
            id_to_elem[node_id] = gateway
            process.add_element(gateway)

        elif _isExclusiveGateway(node):
            gateway = Gateway("exclusive", node_name)
            id_to_elem[node_id] = gateway
            process.add_element(gateway)

        elif _isInclusiveGateway(node):
            gateway = Gateway("inclusive", node_name)
            id_to_elem[node_id] = gateway
            process.add_element(gateway)

        elif _isLaneSet(node):
            pool = process.new_pool()
            id_to_elem[node_id] = pool
            for lane_node in node.getchildren():
                if _isLane(lane_node):
                    lane_id = lane_node.get("id")
                    lane    = pool.new_lane(node_name)
                    id_to_elem[lane_id] = lane

        elif _isSequenceFlow(node):
            src_id = node.get("sourceRef")
            tgt_id = node.get("targetRef")
            id_to_elem[node_id] = (src_id, tgt_id)

        else: # unknown tag
            print "Warning: element not supported with tag", node.tag

    # second iteration: sets the connections between the bpmn elements
    for node in process_node.getchildren():
        node_id = node.get("id")
        for connection in node.getchildren():
            conn_id = connection.text
            if _isIncoming(connection):
                src_id, tgt_id = id_to_elem[conn_id]
                conn_start = id_to_elem[src_id]
                conn_end   = id_to_elem[tgt_id]
                process.add_connection(conn_start, conn_end)
                edges[conn_id] = (conn_start, conn_end)
            elif _isOutgoing(connection):
                src_id, tgt_id = id_to_elem[conn_id]
                conn_start = id_to_elem[src_id]
                conn_end   = id_to_elem[tgt_id]
                process.add_connection(conn_start, conn_end)
            elif _isLane(connection):
                lane_id = connection.get("id")
                lane    = id_to_elem[lane_id]
                for ref_node in connection.getchildren():
                    if _isFlowNodeRef(ref_node):
                        elem = id_to_elem[ref_node.text]
                        lane.add_element(elem)

def bpmn_from_xml(filename, validate=True):
    """Load a BPMN from an XML file"""
    bpmn = BPMN()
    id_to_elem = {}
    tree = etree.parse(filename)
    if validate:
        xmlschema = etree.XMLSchema(etree.parse(_xsd_file))
        if not xmlschema.validate(tree):
            print "Error validating the XML File. Errors found:"
            for error in xmlschema.error_log:
                print "   ERROR ON LINE %s: %s" % (error.line, error.message.encode("utf-8"))
    bpmn.filename = filename
    root = tree.getroot()
    name = root.get("name")
    if name is not None:
        bpmn.name = name
    bpmn.targetNamespace = root.get("targetNamespace")
    edges = {}
    for node in root.getchildren():
        if _isProcess(node):
            _deserialize_process(bpmn.new_process(), node, id_to_elem, edges)
    for node in root.getchildren():
        if _isBPMNDIDiagram(node):
            diagram = read_bpmndi_diagram_from_xml(node, bpmn, edges)
            if diagram is not None:
                bpmn.add_diagram(diagram)
    return bpmn
