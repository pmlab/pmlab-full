from lxml import etree

bpmndi_model = "http://www.omg.org/spec/BPMN/20100524/DI"
dc_model     = "http://www.omg.org/spec/DD/20100524/DC"
di_model     = "http://www.omg.org/spec/DD/20100524/DI"

bpmndiDiagramTag    = "{%s}BPMNDiagram"%bpmndi_model
bpmndiPlaneTag      = "{%s}BPMNPlane"%bpmndi_model
bpmndiShapeTag      = "{%s}BPMNShape"%bpmndi_model
bpmndiLabelStyleTag = "{%s}BPMNLabelStyle"%bpmndi_model
bpmndiLabelTag      = "{%s}BPMNLabel"%bpmndi_model
bpmndiEdgeTag       = "{%s}BPMNEdge"%bpmndi_model
dcBoundsTag         = "{%s}Bounds"%dc_model
diWaypoingTag       = "{%s}waypoint"%di_model
dcFontTag           = "{%s}Font"%dc_model

LANE_OFFSET = 10

class BPMNDI_Diagram:
    """A Diagram is a kind of diagram that depicts all or a part of a BPMN model."""
    static_counter = 0
    def __init__(self):
        self.id = "bpmndi_diagram_"+'{0}'.format(BPMNDI_Diagram.static_counter)
        BPMNDI_Diagram.static_counter += 1
        self.plane = BPMNDI_Plane(self)
        self.labelstyles = []

    def new_labelstyle(self):
        newlabelstyle = BPMNDI_LabelStyle(self)
        self.labelstyles.append(newlabelstyle)
        return newlabelstyle

    def del_labelstyle(self, labelstyle):
        if labelstyle in self.labelstyles:
            self.labelstyles.remove(labelstyle)

    def _xml_serialize(self):
        xml_diag  = etree.Element(bpmndiDiagramTag)
        xml_diag.set("id", self.id)
        xml_plane = self.plane._xml_serialize()
        xml_diag.append(xml_plane)
        return xml_diag

class BPMNDI_Plane:
    """A Plane is the container for the Shapes and Edges of a Diagram.
    The referenced BPMN of a Plane should be a Process or a Subprocess"""
    static_counter = 0
    def __init__(self, diagram):
        self.id = "bpmndi_plane"+'{0}'.format(BPMNDI_Plane.static_counter)
        BPMNDI_Plane.static_counter += 1
        self.diagram = diagram
        self.bpmn_element = None
        self.shapes = []
        self.edges  = []
        self.elem_to_shape = {}
        self.elem_to_edge  = {}

    def new_shape(self, element):
        newshape = BPMNDI_Shape(self, element)
        self.shapes.append(newshape)
        self.elem_to_shape[element] = newshape
        return newshape

    def del_shape(self, shape):
        if shape in self.shapes:
            self.shapes.remove(shape)
            del self.elem_to_shape[shape.bpmn_element]

    def new_edge(self, element):
        newedge = BPMNDI_Edge(self, element)
        self.edges.append(newedge)
        self.elem_to_edge[element] = newedge
        return newedge

    def del_edge(self, edge):
        if edge in self.edges:
            self.edges.remove(edge)
            del self.elem_to_edge[edge.bpmn_element]

    def _xml_serialize(self):
        xml_plane = etree.Element(bpmndiPlaneTag)
        xml_plane.set("id", self.id)
        xml_plane.set("bpmnElement", self.bpmn_element.internal_name)
        for shape in self.shapes:
            xml_shape = shape._xml_serialize()
            xml_plane.append(xml_shape)
        for edge in self.edges:
            xml_edge = edge._xml_serialize()
            xml_plane.append(xml_edge)
        return xml_plane

class BPMNDI_Shape:
    """A Shape represents a depiction of a BPMN model element (typically a node), but
    also a pool, a lane, etc."""
    static_counter = 0
    def __init__(self, plane, element=None):
        self.id = "bpmndi_shape"+'{0}'.format(BPMNDI_Shape.static_counter)
        BPMNDI_Shape.static_counter += 1
        self.plane = plane
        self.bpmn_element      = element
        self.is_marker_visible = True
        self.is_horizontal = True
        self.is_expanded   = True
        self.label         = BPMNDI_Label(self)
        self.bounds        = None # required

    def _xml_serialize(self):
        xml_shape = etree.Element(bpmndiShapeTag)
        xml_shape.set("id", self.id)
        xml_bound = self.bounds._xml_serialize()
        xml_shape.append(xml_bound)
        if self.label is not None:
            xml_label = self.label._xml_serialize()
            xml_shape.append(xml_label)
        xml_shape.set("bpmnElement", self.bpmn_element.internal_name)
        if self.bpmn_element.type == "pool" or self.bpmn_element.type == "lane":
            xml_shape.set("isHorizontal", str(self.is_horizontal).lower())
        if self.bpmn_element.type == "gateway" and self.bpmn_element.subtype == "exclusive":
            xml_shape.set("isMarkerVisible", str(self.is_marker_visible).lower())
        if self.bpmn_element.type == "subprocess":
            xml_shape.set("isExpanded", str(self.is_expanded).lower())
        return xml_shape

class BPMNDI_Edge:
    """An Edge is a kind of edge that can depict a relationship between two BPMN model elements."""
    static_counter = 0
    def __init__(self, plane, element=None):
        self.id = "bpmndi_edge"+'{0}'.format(BPMNDI_Edge.static_counter)
        BPMNDI_Edge.static_counter += 1
        self.plane = plane
        self.bpmn_element = element # a pair with the nodes: (src, tgt)
        self.label = BPMNDI_Label(self)
        self.waypoints = []

    def set_waypoints(self, waypoint_list):
        self.waypoints = []
        for i in range(0, len(waypoint_list), 2):
            waypoint = BPMNDI_Waypoint(waypoint_list[i], waypoint_list[i+1])
            self.waypoints.append(waypoint)

    def _xml_serialize(self):
        xml_edge = etree.Element(bpmndiEdgeTag)
        xml_edge.set("id", self.id)
        src_id   = self.bpmn_element[0].internal_name
        tgt_id   = self.bpmn_element[1].internal_name
        xml_edge.set("bpmnElement", src_id+"_"+tgt_id)
        for waypoint in self.waypoints:
            xml_waypoint = waypoint._xml_serialize()
            xml_edge.append(xml_waypoint)
        if self.label is not None:
            xml_label = self.label._xml_serialize()
            xml_edge.append(xml_label)
        return xml_edge

class BPMNDI_Label:
    """A Label is a kind of label that depicts textual info about a BPMN element."""
    def __init__(self, parent):
        self.parent = None # always a BPMNDI_Edge or BPMNDI_Shape
        self.labelstyle = None
        self.bounds = None

    def _xml_serialize(self):
        xml_label = etree.Element(bpmndiLabelTag)
        if self.labelstyle is not None:
            xml_label.set("labelStyle", self.labelstyle.id)
        if self.bounds is not None:
            xml_label.append(self.bounds._xml_serialize())
        return xml_label

class BPMNDI_LabelStyle:
    """Defines the font, fontsize, etc. of one or more labels."""
    static_counter = 0
    def __init__(self, diagram):
        self.id = "bpmndi_labelstyle"+'{0}'.format(BPMNDI_LabelStyle.static_counter)
        BPMNDI_LabelStyle.static_counter += 1
        self.diagram = diagram
        self.fontname = None # must be the name of the font
        self.fontsize = None # if fontname is not None, a fontsize must be provided
        self.is_bold        = False
        self.is_italic      = False
        self.is_underline   = False
        self.strike_through = False

    def _xml_serialize(self):
        xml_labelstyle = etree.Element(bpmndiLabelStyleTag)
        xml_labelstyle.set("id", self.id)
        if self.fontname is not None:
            xml_font = etree.Element(dcFontTag)
            xml_font.set("name", self.fontname)
            xml_font.set("size", str(self.fontsize))
            xml_font.set("isBold", str(self.is_bold).lower())
            xml_font.set("isItalic", str(self.is_italic).lower())
            xml_font.set("isUnderline", str(self.is_underline).lower())
            xml_font.set("isStrikeThrough", str(self.strike_through).lower())
            xml_labelstyle.append(xml_font)
        return xml_labelstyle

class BPMNDI_Bounds:
    """Simple class that defines the bounds of a Shape"""
    def __init__(self, x, y, width, height):
        self.x = float(x)
        self.y = float(y)
        self.width  = float(width)
        self.height = float(height)

    def _xml_serialize(self):
        xml_bound = etree.Element(dcBoundsTag)
        xml_bound.set("width",  str(self.width))
        xml_bound.set("height", str(self.height))
        xml_bound.set("x", str(self.x))
        xml_bound.set("y", str(self.y))
        return xml_bound

class BPMNDI_Waypoint:
    """Simple class that defines a waypoint of a Edge"""
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def _xml_serialize(self):
        xml_waypoint = etree.Element(diWaypoingTag)
        xml_waypoint.set("x", str(self.x))
        xml_waypoint.set("y", str(self.y))
        return xml_waypoint

_isPlane      = lambda node : node.tag == bpmndiPlaneTag
_isLabelStyle = lambda node : node.tag == bpmndiLabelStyleTag
_isShape      = lambda node : node.tag == bpmndiShapeTag
_isEdge       = lambda node : node.tag == bpmndiEdgeTag
_isBounds     = lambda node : node.tag == dcBoundsTag
_isLabel      = lambda node : node.tag == bpmndiLabelTag
_isWaypoint   = lambda node : node.tag == diWaypoingTag
_isFont       = lambda node : node.tag == dcFontTag

def read_bpmndi_diagram_from_xml(diagram_root, bpmn, edges):
    """Takes an XML element with its root being a BPMNDiagram and returns the
    proper structure of the diagram.
    Edges must be a map from edge_id (as read in the XML) to a pair (src, tgt)."""
    diagram = BPMNDI_Diagram()
    plane   = diagram.plane
    labelstyles = {} # maps a labelstyle id to the labelstyle instance
    # first we read the labelstyle nodes, because will be referenced in the plane
    for labelstyle_node in diagram_root.getchildren():
        if _isLabelStyle(labelstyle_node):
            labelstyle = diagram.new_labelstyle()
            labelstyle_id = labelstyle_node.get("id")
            labelstyles[labelstyle_id] = labelstyle
            for font_node in labelstyle_node.getchildren():
                labelstyle.fontname = font_node.get("name")
                labelstyle.fontsize = float(font_node.get("size"))
                labelstyle.is_bold  = True if font_node.get("isBold", "false").lower() == "true" else False
                labelstyle.is_italic      = True if font_node.get("isItalic", "false").lower() == "true" else False
                labelstyle.is_underline   = True if font_node.get("isUnderline", "false").lower() == "true" else False
                labelstyle.strike_through = True if font_node.get("isStrikeThrough", "false").lower() == "true" else False

    # next, we read the plane and create the diagram structure
    for node in diagram_root.getchildren():
        if _isPlane(node):
            plane_elem_id = node.get("bpmnElement")
            plane.bpmn_element = bpmn.internalname_to_elem.get(plane_elem_id, None)
            if plane.bpmn_element is None:
                print "Error: Element not found with id", plane_elem_id
                return None
            for element in node.getchildren():

                if _isShape(element):
                    shape_elem_id = element.get("bpmnElement")
                    shape = plane.new_shape(plane.bpmn_element.internalname_to_elem.get(shape_elem_id))
                    if shape.bpmn_element is None:
                        print "Error: Element not found with id", shape_elem_id
                        return None
                    if shape.bpmn_element.type == "pool" or shape.bpmn_element.type == "lane":
                        is_horizontal = element.get("isHorizontal", "true").lower()
                        shape.is_horizontal = True if is_horizontal == "true" else False
                    elif shape.bpmn_element.type == "subprocess":
                        is_expanded = element.get("isExpanded", "true").lower()
                        shape.is_expanded = True if is_expanded == "true" else False
                    elif shape.bpmn_element.type == "gateway":
                        is_marker_visible = element.get("isMarkerVisible", "true").lower()
                        shape.is_marker_visible = True if is_marker_visible == "true" else False
                    for shape_child in element.getchildren():
                        if _isBounds(shape_child):
                            x = float(shape_child.get("x", "0.0"))
                            y = float(shape_child.get("y", "0.0"))
                            width  = float(shape_child.get("width", "0.0"))
                            height = float(shape_child.get("height", "0.0"))
                            shape.bounds = BPMNDI_Bounds(x, y, width, height)
                            shape.bpmn_element.width  = width
                            shape.bpmn_element.height = height
                        elif _isLabel(shape_child):
                            __read_label(shape_child, shape.label, labelstyles)

                elif _isEdge(element):
                    edge_elem_id = node.get("bpmnElement")
                    edge = plane.new_edge(edges.get(edge_elem_id))
                    if edge.bpmn_element is None:
                        print "Error: Element not found with id", edge_elem_id
                        return None
                    for edge_child in element.getchildren():
                        if _isWaypoint(edge_child):
                            x = float(edge_child.get("x", "0.0"))
                            y = float(edge_child.get("y", "0.0"))
                            edge.waypoints.append(BPMNDI_Waypoint(x, y))
                        elif _isLabel(edge_child):
                            __read_label(edge_child, edge.label, labelstyles)
    return diagram

def __read_label(label_node, label, labelstyles):
    labelstyle_id = label_node.get("labelStyle")
    labelstyle    = labelstyles.get(labelstyle_id)
    label.labelstyle = labelstyle
    for label_child in label_node.getchildren():
        if _isBounds(label_child):
            x = float(label_child.get("x", "0.0"))
            y = float(label_child.get("y", "0.0"))
            width  = float(label_child.get("width", "0.0"))
            height = float(label_child.get("height", "0.0"))
            label.bounds = BPMNDI_Bounds(x, y, width, height)


class GenerateDiagramFromProcess:
    def __init__(self, process, supergrid, edges, parent2context):
        """self.supergrid = supergrid
        self.parent2context = parent2context
        supergrid.pack() # TODO: mover el pack y el set_geometry fuera de aqui para poder calcular los ejes antes de crear el diagrma
        supergrid.set_geometry()
        for process in bpmn.processes:
            diagram = self._create_diagram(process)
            self.bpmn.add_diagram(diagram)
        """
        self.parent2context = parent2context
        self.supergrid = supergrid
        self.edges     = edges
        self.width     = 0
        self.height    = 0
        self.diagram   = self._create_diagram(process)
        self.add_offset(30, 10)

    def _create_diagram(self, process):
        diagram = BPMNDI_Diagram()
        plane   = diagram.plane
        plane.bpmn_element = process

        # first, the pools and its lanes are created
        for pool in process.pools:
            poolshape = plane.new_shape(pool)
            poolminx = poolminy = poolmaxx = poolmaxy = 0
            for lane in pool.lanes:
                lanegrid = self.parent2context[lane].grid
                shape    = plane.new_shape(lane)
                bounds   = self.supergrid.geometry[lanegrid]
                shape.bounds = BPMNDI_Bounds(bounds.x, bounds.y, bounds.width, bounds.height)
                poolminx = min(poolminx, bounds.x)
                poolminy = min(poolminy, bounds.y)
                poolmaxx = max(poolmaxx, bounds.x+bounds.width)
                poolmaxy = max(poolmaxy, bounds.y+bounds.height)
                self.width  = max(self.width,  poolmaxx)
                self.height = max(self.height, poolmaxy)
            poolwidth  = poolmaxx - poolminx
            poolheight = poolmaxy - poolminy
            poolshape.bounds = BPMNDI_Bounds(poolminx - LANE_OFFSET, poolminy, poolwidth + LANE_OFFSET, poolheight)

        # second, the elements are created
        for element in process.elements:
            elemgrid = self.parent2context[element.parent].grid
            elemcell = elemgrid.item_to_cell[element]
            shape    = plane.new_shape(element)
            bounds   = self.supergrid.geometry[elemcell]
            shape.bounds = BPMNDI_Bounds(bounds.x, bounds.y, bounds.width, bounds.height)
            self.width   = max(self.width,  bounds.x + bounds.width)
            self.height  = max(self.height, bounds.y + bounds.height)
            for outelem in element.outset:
                edge = plane.new_edge((element, outelem))
                waypoint_list = self.edges[(element, outelem)]
                edge.set_waypoints(waypoint_list)

        return diagram

    def add_offset(self, x_offset=0, y_offset=0):
        plane = self.diagram.plane
        for shape in plane.shapes:
            shape.bounds.x += x_offset
            shape.bounds.y += y_offset

        for edge in plane.edges:
            for waypoint in edge.waypoints:
                waypoint.x += x_offset
                waypoint.y += y_offset