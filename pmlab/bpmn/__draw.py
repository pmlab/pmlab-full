from Tkinter import *
from __layouting import *
from __bpmn_diagram import GenerateDiagramFromProcess, BPMNDI_Bounds, BPMNDI_Waypoint
import math


class PopupMenu:
    def __init__(self, parent, tearoff=0):
        self.parent = parent
        self.menu = Menu(None, tearoff=tearoff)

    def tk_popup(self, x, y):
        self.menu.tk_popup(x, y)

    def add_separator(self):
        self.menu.add_separator()

    def add_command(self, label, command):
        self.menu.add_command(label=label, command=command)

    def add_cascade(self, label, menu):
        self.menu.add_cascade(label=label, menu=menu)


class BPMN_Draw:
    class VisualElement:
        def __init__(self, shape=None, edge=None, elem=None):
            # shape must be a BPMNDI_Shape and edge a BPMNDI_Edge, elem is then BPMN element
            self.shape   = shape
            self.di_edge = edge  # BPMNDI_Edge
            self.elem    = elem
            self.type    = "shape" if shape is not None else "edge"
            self.body    = None
            self.name    = None
            self.edge    = None  # canvas id for the edge
            self.showname    = True
            self.decorations = []

    def __init__(self, master, bpmn):
        self.master = master
        self.bpmn   = bpmn
        frame       = Frame(master)
        master.wm_title("BPMN Visualization")

        # Some variables needed for the class behavior
        self.undo_stack = []  # stores the actions that can be undone
        self.redo_stack = []  # stores the actions that can be redone

        self.visual_elements = {}
        self.id_to_velem     = {}  # id = any canvas-id
        self.scale           = 1.0
        self.total_width     = 0
        self.total_height    = 0
        self.mouse_pos       = (0, 0)
        self.lockvar         = BooleanVar()
        self.move_action     = None
        self.resize_action   = None
        self.selected_velem  = None
        self.create_fn = {
            "pool"       : self._create_pool,
            "lane"       : self._create_lane,
            "event"      : self._create_event,
            "gateway"    : self._create_gateway,
            "activity"   : self._create_activity,
            "subprocess" : self._create_subprocess
        }
        self.redraw_fn = {
            "pool"       : self._redraw_pool,
            "lane"       : self._redraw_lane,
            "event"      : self._redraw_event,
            "gateway"    : self._redraw_gateway,
            "activity"   : self._redraw_activity,
            "subprocess" : self._redraw_subprocess
        }

        # Adding menus to the window
        menu = Menu(master, tearoff=0)
        master.config(menu=menu)

        viewmenu = Menu(menu, tearoff=0)
        viewmenu.add_command(label="Show all names", command=self.show_all_names)
        viewmenu.add_command(label="Hide all names", command=self.hide_all_names)
        viewmenu.add_separator()
        viewmenu.add_command(label="Zoom in", command=self.zoom_in)
        viewmenu.add_command(label="Zoom out", command=self.zoom_out)
        viewmenu.add_separator()
        viewmenu.add_command(label="Relayout model", command=self.relayout)

        editmenu = Menu(menu, tearoff=0)
        editmenu.add_command(label="Undo", command=self.undo_action, state=DISABLED)
        editmenu.add_command(label="Redo", command=self.redo_action, state=DISABLED)
        editmenu.add_separator()
        editmenu.add_checkbutton(label="Lock", variable=self.lockvar, onvalue=True, offvalue=False)
        menu.add_cascade(label="View", menu=viewmenu)
        menu.add_cascade(label="Edit", menu=editmenu)

        self.menu = menu
        self.viewmenu = viewmenu
        self.editmenu = editmenu

        # Adding the widgets to the window
        self.canvas = Canvas(frame, width=self.total_width, height=self.total_height)
        self.canvas.grid(row=0, column=0, sticky=N+W+E+S)

        self.xscrollbar = Scrollbar(frame, orient=HORIZONTAL)
        self.xscrollbar.grid(row=1, column=0, sticky=E+W)
        self.xscrollbar.config(command=self.canvas.xview)

        self.yscrollbar = Scrollbar(frame, orient=VERTICAL)
        self.yscrollbar.grid(row=0, column=1, sticky=N+S)
        self.yscrollbar.config(command=self.canvas.yview)

        self.canvas.config(xscrollcommand=self.xscrollbar.set, yscrollcommand=self.yscrollbar.set)
        self.canvas.config(scrollregion=(0, 0, self.total_width, self.total_height))

        # Needed for the automatic resize of the widgets
        frame.pack(expand=True, fill=BOTH)
        frame.rowconfigure(0, weight=1, minsize=10)
        frame.rowconfigure(1, weight=0, minsize=10)
        frame.columnconfigure(0, weight=1, minsize=10)
        frame.columnconfigure(1, weight=0, minsize=10)
        master.rowconfigure(0, weight=1)
        master.rowconfigure(1, weight=0)
        master.columnconfigure(0, weight=1)
        master.columnconfigure(1, weight=0)

        # Event bindings
         # mouse wheel
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)
        self.canvas.bind("<Control-Button-4>", self.on_mouse_wheel_ctrl)
        self.canvas.bind("<Control-Button-5>", self.on_mouse_wheel_ctrl)
        self.xscrollbar.bind("<Button-4>", self.on_mouse_wheel)
        self.xscrollbar.bind("<Button-5>", self.on_mouse_wheel)
        self.yscrollbar.bind("<Button-4>", self.on_mouse_wheel)
        self.yscrollbar.bind("<Button-5>", self.on_mouse_wheel)
         # left and right clic
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<ButtonRelease-1>", self.on_stop_left_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
         # ctrl+right clic
        self.canvas.bind("<Control-Button-1>", self.on_ctrl_left_click)

        self.master.bind("<Control-z>", self.undo_action)
        self.master.bind("<Control-y>", self.redo_action)
        self.master.bind("<Control-l>", self.toggle_lock)
        self.master.protocol("WM_DELETE_WINDOW", self.exit_handler)

        # finally, create the visual elements and draw them
        if len(bpmn.diagrams) == 0:
            self.layout_model()
        for diagram in bpmn.diagrams:
            self._create_canvas_elements(diagram)
        self.redraw(resize=True)

    def exit_handler(self):
        if len(self.undo_stack) > 0: # when at least one change is made
            self.save_diagram_changes()
        self.master.destroy()

    def on_mouse_wheel(self, event):
        if event.widget is self.canvas or event.widget is self.yscrollbar:
            if event.num == 4:    # scroll up
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:  # scroll down
                self.canvas.yview_scroll( 1, "units")
        elif event.widget is self.xscrollbar:
            if event.num == 4:    # scroll up
                self.canvas.xview_scroll(-1, "units")
            elif event.num == 5:  # scroll down
                self.canvas.xview_scroll( 1, "units")

    def on_mouse_wheel_ctrl(self, event):
        if event.widget is self.canvas:
            if event.num == 4:    # scroll up
                self.zoom_in()
            elif event.num == 5:  # scroll down
                self.zoom_out()

    def on_right_click(self, event):
        if event.widget is self.canvas and not self.lockvar.get():
            if self.move_action is not None:
                self.move_action.undo()
                self.move_action    = None
                self.selected_velem = None
            elif self.resize_action is not None:
                self.resize_action.undo()
                self.resize_action  = None
                self.selected_velem = None
            else:
                self.mouse_pos = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
                obj_id = self.canvas.find_withtag(CURRENT)
                obj_id = obj_id[0] if len(obj_id) > 0 else None
                velem  = self.id_to_velem.get(obj_id)
                elem   = velem.elem if velem is not None else None
                popup_menu = self.get_popup_menu(velem, elem)
                popup_menu.tk_popup(event.x_root, event.y_root)

    def on_left_click(self, event):
        if event.widget is self.canvas and not self.lockvar.get():
            self.mouse_pos = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            obj_id = self.canvas.find_withtag(CURRENT)
            obj_id = obj_id[0] if len(obj_id) > 0 else None
            self.selected_velem = self.id_to_velem.get(obj_id)
            if self.selected_velem is not None and self.selected_velem.type == "shape":
                self.move_action = MoveShapeAction(self, self.selected_velem, self.mouse_pos)
            elif self.selected_velem is not None and self.selected_velem.type == "edge":
                wp_pos, last_wp = self._get_nearest_waypoint(self.mouse_pos, self.selected_velem)
                if wp_pos != 0 and wp_pos != last_wp:
                    self.move_action = MoveWaypointAction(self, self.selected_velem, wp_pos)

    def on_stop_left_click(self, event):
        if event.widget is self.canvas and not self.lockvar.get():
            self.mouse_pos = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            if self.move_action is not None:
                self.move_action.end_x, self.move_action.end_y = self.mouse_pos
                self.do_action(self.move_action)
                self.move_action = None
            elif self.resize_action is not None:
                self.resize_action.end_x, self.resize_action.end_y = self.mouse_pos
                self.do_action(self.resize_action)
                self.resize_action = None

    def on_drag(self, event):
        if event.widget is self.canvas and not self.lockvar.get():
            self.mouse_pos = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            if self.move_action is not None:
                self.move_action.show(self.mouse_pos)
            elif self.resize_action is not None:
                self.resize_action.show(self.mouse_pos)

    def on_ctrl_left_click(self, event):
        if event.widget is self.canvas and not self.lockvar.get():
            self.mouse_pos = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            obj_id = self.canvas.find_withtag(CURRENT)
            obj_id = obj_id[0] if len(obj_id) > 0 else None
            self.selected_velem = self.id_to_velem.get(obj_id)
            if self.selected_velem is not None and self.selected_velem.type == "shape":
                self.resize_action = ResizeAction(self, self.selected_velem, self.mouse_pos)

    def get_popup_menu(self, velem, elem):
        popup_menu = PopupMenu(self.master, tearoff=0)
        if velem is None and elem is None:
            return popup_menu

        if velem.type == "edge":
            popup_menu.add_command(label="Add wapoint", command=self.add_waypoint(velem, self.mouse_pos))
            wp_pos, last_wp = self._get_nearest_waypoint(self.mouse_pos, velem, mindist=20)
            if wp_pos != 0 and wp_pos != last_wp:
                popup_menu.add_command(label="Del waypoint", command=self.del_waypoint(velem, wp_pos))

        if velem.type == "shape":
            if not velem.showname:
                popup_menu.add_command(label="Show name", command=self.show_name(velem))
            else:
                popup_menu.add_command(label="Hide name", command=self.hide_name(velem))
        return popup_menu

    def zoom_in(self):
        prevscale = self.scale
        self.scale += 0.1
        self.apply_scale(prevscale)

    def zoom_out(self):
        prevscale = self.scale
        self.scale -= 0.1
        if self.scale < 0.1:
            self.scale = 0.1
        self.apply_scale(prevscale)

    def toggle_lock(self, event=None):
        self.editmenu.invoke(3)

    def add_waypoint(self, velem, pos):
        def do():
            self.do_action(AddWaypointAction(self, velem, pos))
        return do

    def del_waypoint(self, velem, waypoint_pos):
        def do():
            self.do_action(DelWaypointAction(self, velem, waypoint_pos))
        return do

    def show_name(self, velem):
        def do():
            velem.showname = True
            self.canvas.itemconfigure(velem.name, state=NORMAL)
            #self.do_action(ShowNameAction(self, velem))
        return do

    def hide_name(self, velem):
        def do():
            velem.showname = False
            self.canvas.itemconfigure(velem.name, state=HIDDEN)
            #self.do_action(HideNameAction(self, velem))
        return do

    def show_all_names(self):
        for velem in self.visual_elements.values():
            velem.showname = True
            self.canvas.itemconfigure(velem.name, state=NORMAL)

    def hide_all_names(self):
        for velem in self.visual_elements.values():
            velem.showname = False
            self.canvas.itemconfigure(velem.name, state=HIDDEN)

    def relayout(self):
        self.do_action(RelayoutModelAction(self))

    def apply_scale(self, prevscale):
        self.canvas.scale(ALL, 0, 0, 1.0/prevscale, 1.0/prevscale)
        self.canvas.scale(ALL, 0, 0, self.scale, self.scale)
        self.canvas.config(scrollregion=(0, 0, int(self.total_width*self.scale), int(self.total_height*self.scale)))

    def undo_action(self, event=None):
        if len(self.undo_stack) > 0:
            action = self.undo_stack.pop()
            action.undo()
            self.redo_stack.append(action)
            self.editmenu.entryconfigure(1, state=ACTIVE)
            if len(self.undo_stack) == 0:
                self.editmenu.entryconfigure(0, state=DISABLED)

    def redo_action(self, event=None):
        if len(self.redo_stack) > 0:
            action = self.redo_stack.pop()
            action.redo()
            self.undo_stack.append(action)
            self.editmenu.entryconfigure(0, state=ACTIVE)
            if len(self.redo_stack) == 0:
                self.editmenu.entryconfigure(1, state=DISABLED)

    def do_action(self, action):
        action.redo()
        self.undo_stack.append(action)
        self.redo_stack = []
        self.editmenu.entryconfigure(0, state=ACTIVE)
        self.editmenu.entryconfigure(1, state=DISABLED)

    def _get_nearest_waypoint(self, pos, velem, mindist=maxint):
        edge_coords = self.canvas.coords(velem.edge)
        min_dist = mindist
        wp_pos   = 0
        for i in range(0, len(edge_coords), 2):
            x_dif = pos[0] - edge_coords[i]
            y_dif = pos[1] - edge_coords[i+1]
            dist  = int(math.sqrt(x_dif**2 + y_dif**2))
            if dist < min_dist:
                min_dist = dist
                wp_pos   = i // 2
        return wp_pos, len(edge_coords) // 2 - 1

    def _create_canvas_elements(self, diagram):
        plane = diagram.plane
        for shape in plane.shapes:
            velem = self._create_new_shape(shape)
            self.visual_elements[shape.bpmn_element] = velem
        for edge in plane.edges:
            velem = self._create_new_edge(edge, edge.bpmn_element)
            self.visual_elements[edge.bpmn_element] = velem

    def _create_new_shape(self, shape):
        elem  = shape.bpmn_element
        velem = self.VisualElement(shape=shape, elem=elem)
        create_fn = self.create_fn[elem.type]
        create_fn(velem, elem)
        return velem

    # created elements have to be redrawn to get the right coordinates
    def _create_pool(self, velem, pool):
        velem.body = self.canvas.create_rectangle(0, 0, 0, 0, fill=pool.color)
        velem.name = self.canvas.create_text(0, 0, text="")
        self.id_to_velem[velem.body] = velem
        self.id_to_velem[velem.name] = velem

    def _create_lane(self, velem, lane):
        self._create_pool(velem, lane)  # lanes are created the same way as pools

    def _create_event(self, velem, event):
        velem.body = self.canvas.create_oval(0, 0, 0, 0, fill=event.color)
        velem.name = self.canvas.create_text(0, 0, text=event.name, state=HIDDEN)
        self.id_to_velem[velem.body] = velem
        self.id_to_velem[velem.name] = velem

    def _create_gateway(self, velem, gateway):
        velem.body = self.canvas.create_polygon(0, 0, 0, 0, 0, 0, 0, 0, fill=gateway.color, outline="black")
        velem.name = self.canvas.create_text(0, 0, text=gateway.name, state=HIDDEN)
        self.id_to_velem[velem.body] = velem
        self.id_to_velem[velem.name] = velem
        if gateway.subtype == "exclusive" and velem.shape.is_marker_visible:
            first_line  = self.canvas.create_line(0, 0, 0, 0)
            second_line = self.canvas.create_line(0, 0, 0, 0)
            velem.decorations.append(first_line)
            velem.decorations.append(second_line)
            self.id_to_velem[first_line]  = velem
            self.id_to_velem[second_line] = velem
        if gateway.subtype == "inclusive":
            inner_circle = self.canvas.create_oval(0, 0, 0, 0)
            velem.decorations.append(inner_circle)
            self.id_to_velem[inner_circle] = velem
        elif gateway.subtype == "parallel":
            horizontal_line = self.canvas.create_line(0, 0, 0, 0)
            vertical_line   = self.canvas.create_line(0, 0, 0, 0)
            velem.decorations.append(horizontal_line)
            velem.decorations.append(vertical_line)
            self.id_to_velem[horizontal_line] = velem
            self.id_to_velem[vertical_line]   = velem

    def _create_activity(self, velem, activity):
        velem.body = self.canvas.create_rectangle(0, 0, 0, 0, fill=activity.color)
        velem.name = self.canvas.create_text(0, 0, text=activity.name, state=HIDDEN)
        self.id_to_velem[velem.body] = velem
        self.id_to_velem[velem.name] = velem

    def _create_subprocess(self, velem, subprocess):
        """TODO"""
        pass

    def _create_new_edge(self, di_edge, elem):
        velem = self.VisualElement(edge=di_edge, elem=di_edge.bpmn_element)
        velem.edge = self.canvas.create_line(0, 0, 0, 0, arrow=LAST)
        self.id_to_velem[velem.edge] = velem
        return velem

    def layout_model(self):
        layouter  = BPMN_Layouter(self.bpmn)
        supergrid = layouter.supergrid
        supergrid.pack()
        supergrid.set_geometry()
        offset = 0  # vertical offset to display the diagrams in diferent regions
        for process in self.bpmn.processes:
            diagramGen = GenerateDiagramFromProcess(process, supergrid, layouter.edges, layouter.parent2context)
            diagramGen.add_offset(y_offset=offset)
            offset += diagramGen.height
            self.bpmn.add_diagram(diagramGen.diagram)

    def redraw(self, resize=False):
        xmin = maxint
        ymin = maxint
        xmax = 0
        ymax = 0
        for diagram in self.bpmn.diagrams:
            plane = diagram.plane
            for shape in plane.shapes:
                redraw_fn = self.redraw_fn[shape.bpmn_element.type]
                redraw_fn(shape, shape.bpmn_element)
                xmin = min(xmin, shape.bounds.x)
                ymin = min(ymin, shape.bounds.y)
                xmax = max(xmax, shape.bounds.x + shape.bounds.width)
                ymax = max(ymax, shape.bounds.y + shape.bounds.height)

            for edge in plane.edges:
                self._redraw_edge(edge, edge.bpmn_element)

        self.total_width  = xmax + xmin
        self.total_height = ymax + ymin
        self.apply_scale(self.scale)
        if resize:
            self.canvas.config(width=int(self.total_width), height=int(self.total_height))

    def _redraw_pool(self, shape, pool):
        velem = self.visual_elements[pool]
        x0 = shape.bounds.x
        y0 = shape.bounds.y
        x1 = shape.bounds.x + shape.bounds.width
        y1 = shape.bounds.y + shape.bounds.height
        self.canvas.coords(velem.body, x0, y0, x1, y1)

    def _redraw_lane(self, shape, lane):
        self._redraw_pool(shape, lane)  # lanes are drawn like pools

    def _redraw_event(self, shape, event):
        self._redraw_activity(shape, event)

    def _redraw_gateway(self, shape, gateway):
        velem = self.visual_elements[gateway]
        x0 = shape.bounds.x
        y0 = shape.bounds.y
        x1 = shape.bounds.x + shape.bounds.width
        y1 = shape.bounds.y + shape.bounds.height
        xmid = (x0 + x1) // 2
        ymid = (y0 + y1) // 2
        self.canvas.coords(velem.body, x0, ymid, xmid, y0, x1, ymid, xmid, y1)
        self.canvas.coords(velem.name, x0 + shape.bounds.width // 2, y0 + shape.bounds.height // 2)
        center_x = x0 + shape.bounds.width  // 2
        center_y = y0 + shape.bounds.height // 2
        if gateway.subtype == "exclusive" and shape.is_marker_visible:
            cw = shape.bounds.width  // 4
            ch = shape.bounds.height // 4
            first_line  = velem.decorations[0]
            second_line = velem.decorations[1]
            self.canvas.coords(first_line,  center_x - cw, center_y - ch, center_x + cw, center_y + ch)
            self.canvas.coords(second_line, center_x + cw, center_y - ch, center_x - cw, center_y + ch)
        elif gateway.subtype == "inclusive":
            cw = shape.bounds.width  // 4
            ch = shape.bounds.height // 4
            inner_circle = velem.decorations[0]
            self.canvas.coords(inner_circle, center_x - cw, center_y - ch, center_x + cw, center_y + ch)
        elif gateway.subtype == "parallel":
            cw = shape.bounds.width  // 4
            ch = shape.bounds.height // 4
            horizontal_line = velem.decorations[0]
            vertical_line   = velem.decorations[1]
            self.canvas.coords(horizontal_line, center_x - cw, center_y, center_x + cw, center_y)
            self.canvas.coords(vertical_line, center_x, center_y - ch, center_x, center_y + ch)
        if velem.showname:
            self.canvas.itemconfigure(velem.name, state=NORMAL)

    def _redraw_activity(self, shape, activity):
        velem = self.visual_elements[activity]
        x0 = shape.bounds.x
        y0 = shape.bounds.y
        x1 = shape.bounds.x + shape.bounds.width
        y1 = shape.bounds.y + shape.bounds.height
        self.canvas.coords(velem.body, x0, y0, x1, y1)
        self.canvas.coords(velem.name, x0 + shape.bounds.width // 2, y0 + shape.bounds.height // 2)
        if velem.showname:
            self.canvas.itemconfigure(velem.name, state=NORMAL)

    def _redraw_subprocess(self, shape, subprocess):
        pass

    def _redraw_edge(self, di_edge, edge):
        velem  = self.visual_elements[edge]
        points = []
        for waypoint in di_edge.waypoints:
            points.append(waypoint.x)
            points.append(waypoint.y)
        self.canvas.coords(velem.edge, *points)

    def save_diagram_changes(self):
        for key in self.visual_elements:
            velem = self.visual_elements[key]
            if velem.type == "shape":
                body_coords = self.canvas.coords(velem.body)
                minx = miny = maxint
                maxx = maxy = 0
                for i in range(0, len(body_coords), 2):
                    minx = min(minx, body_coords[i])
                    miny = min(miny, body_coords[i+1])
                    maxx = max(maxx, body_coords[i])
                    maxy = max(maxy, body_coords[i+1])
                velem.shape.bounds = BPMNDI_Bounds(minx, miny, maxx-minx, maxy-miny)
                velem.shape.bpmn_element.width  = maxx-minx
                velem.shape.bpmn_element.height = maxy-miny
            if velem.type == "edge":
                edge_coords = self.canvas.coords(velem.edge)
                waypoints   = []
                for i in range(0, len(edge_coords), 2):
                    wp = BPMNDI_Waypoint(edge_coords[i], edge_coords[i+1])
                    waypoints.append(wp)
                velem.di_edge.waypoints = waypoints


class EditAction:
    # All EditorAction-derived classes must implement a redo method and an undo method
    # Parent must be a BPMN_Draw or a subclass of BPMN_Draw
    def __init__(self, parent):
        self.parent = parent

    def redo(self):
        raise NotImplementedError("The redo method must be implemented")

    def undo(self):
        raise NotImplementedError("The undo method must be implemented")

class MoveShapeAction(EditAction):
    def __init__(self, parent, velem, start_pos):
        EditAction.__init__(self, parent)

        self.body_start_coords = self.parent.canvas.coords(velem.body)
        self.dec_start_coords  = [self.parent.canvas.coords(dec) for dec in velem.decorations]
        self.name_start_coords = self.parent.canvas.coords(velem.name)
        self.velem   = velem
        self.start_x = start_pos[0]
        self.start_y = start_pos[1]
        self.end_x   = start_pos[0]
        self.end_y   = start_pos[1]
        self.body_end_coords = None
        self.dec_end_coords  = None
        self.name_end_coords = None
        self.move_edges      = None

    def redo(self):
        if self.body_end_coords is None:
            x_dif = self.end_x - self.start_x
            y_dif = self.end_y - self.start_y
            self.body_end_coords = [n+x_dif if ind%2==0 else n+y_dif for ind, n in enumerate(self.body_start_coords)]
        if self.dec_end_coords is None:
            x_dif = self.end_x - self.start_x
            y_dif = self.end_y - self.start_y
            self.dec_end_coords  = []
            for dec_start_coords in self.dec_start_coords:
                dec_end_coords = [n+x_dif if ind%2==0 else n+y_dif for ind, n in enumerate(dec_start_coords)]
                self.dec_end_coords.append(dec_end_coords)
        if self.name_end_coords is None:
            x_dif = self.end_x - self.start_x
            y_dif = self.end_y - self.start_y
            self.name_end_coords = [n+x_dif if ind%2==0 else n+y_dif for ind, n in enumerate(self.name_start_coords)]
        if self.move_edges is None:
            if not self.velem.elem.type == "pool" and not self.velem.elem.type == "lane":
                self.move_edges = []
                for inelem in self.velem.elem.inset:
                    edge_velem = self.parent.visual_elements[(inelem, self.velem.elem)]
                    start_pos  = (self.start_x, self.start_y)
                    move_edge_action = MoveWaypointAction(self.parent, edge_velem, -1, start_pos)
                    move_edge_action.end_x = self.end_x
                    move_edge_action.end_y = self.end_y
                    self.move_edges.append(move_edge_action)
                for outelem in self.velem.elem.outset:
                    edge_velem = self.parent.visual_elements[(self.velem.elem, outelem)]
                    start_pos  = (self.start_x, self.start_y)
                    move_edge_action = MoveWaypointAction(self.parent, edge_velem, 0, start_pos)
                    move_edge_action.end_x = self.end_x
                    move_edge_action.end_y = self.end_y
                    self.move_edges.append(move_edge_action)

        self.parent.canvas.coords(self.velem.body, *self.body_end_coords)
        for i in range(len(self.velem.decorations)):
            dec = self.velem.decorations[i]
            dec_end_coords = self.dec_end_coords[i]
            self.parent.canvas.coords(dec, *dec_end_coords)
        if self.move_edges is not None:
            for move_edge_action in self.move_edges:
                move_edge_action.redo()
        self.parent.canvas.coords(self.velem.name, *self.name_end_coords)
        self._change_shape(self.body_end_coords)

    def undo(self):
        self.parent.canvas.coords(self.velem.body, *self.body_start_coords)
        for i in range(len(self.velem.decorations)):
            dec = self.velem.decorations[i]
            dec_start_coords = self.dec_start_coords[i]
            self.parent.canvas.coords(dec, *dec_start_coords)
        if self.move_edges is not None:
            for move_edge_action in self.move_edges:
                move_edge_action.undo()
        self.parent.canvas.coords(self.velem.name, *self.name_start_coords)
        self._change_shape(self.body_start_coords)

    def show(self, new_pos):
        x_dif = new_pos[0] - self.start_x
        y_dif = new_pos[1] - self.start_y
        #body_coords = list(self.body_start_coords)
        body_coords = [n+x_dif if ind%2==0 else n+y_dif for ind, n in enumerate(self.body_start_coords)]
        self.parent.canvas.coords(self.velem.body, *body_coords)
        for i in range(len(self.velem.decorations)):
            dec = self.velem.decorations[i]
            dec_coords = [n+x_dif if ind%2==0 else n+y_dif for ind, n in enumerate(self.dec_start_coords[i])]
            self.parent.canvas.coords(dec, *dec_coords)
        name_coords = [n+x_dif if ind%2==0 else n+y_dif for ind, n in enumerate(self.name_start_coords)]
        self.parent.canvas.coords(self.velem.name, *name_coords)

    def _change_shape(self, body_coords):
        minx = miny = maxint
        maxx = maxy = 0
        for i in range(0, len(body_coords), 2):
            minx = min(minx, body_coords[i])
            miny = min(miny, body_coords[i+1])
            maxx = max(maxx, body_coords[i])
            maxy = max(maxy, body_coords[i+1])
        self.velem.shape.bounds.x = minx
        self.velem.shape.bounds.y = miny
        self.velem.shape.bounds.width  = maxx - minx
        self.velem.shape.bounds.height = maxy - miny


class MoveWaypointAction(EditAction):
    def __init__(self, parent, velem, waypoint_pos, start_pos=None):
        EditAction.__init__(self, parent)

        self.start_edge_coords = self.parent.canvas.coords(velem.edge)
        self.velem   = velem
        self.wp_pos  = waypoint_pos if waypoint_pos >= 0 else len(self.start_edge_coords) // 2 + waypoint_pos
        self.start_x = start_pos[0] if start_pos is not None else self.start_edge_coords[self.wp_pos*2]
        self.start_y = start_pos[1] if start_pos is not None else self.start_edge_coords[self.wp_pos*2+1]
        self.end_x   = start_pos[0] if start_pos is not None else self.start_edge_coords[self.wp_pos*2]
        self.end_y   = start_pos[1] if start_pos is not None else self.start_edge_coords[self.wp_pos*2+1]
        self.end_edge_coords = None
        self.new_waypoint    = None
        self.prev_waypoint   = self.velem.di_edge.waypoints[self.wp_pos]

    def redo(self):
        if self.end_edge_coords is None:
            self.end_edge_coords = list(self.start_edge_coords)
            x_dif = self.end_x - self.start_x
            y_dif = self.end_y - self.start_y
            self.end_edge_coords[self.wp_pos*2]   += x_dif
            self.end_edge_coords[self.wp_pos*2+1] += y_dif
            end_pos_x = self.end_edge_coords[self.wp_pos*2]
            end_pos_y = self.end_edge_coords[self.wp_pos*2+1]
            self.new_waypoint = BPMNDI_Waypoint(end_pos_x, end_pos_y)
        self.parent.canvas.coords(self.velem.edge, *self.end_edge_coords)
        self.velem.di_edge.waypoints[self.wp_pos] = self.new_waypoint

    def undo(self):
        self.parent.canvas.coords(self.velem.edge, *self.start_edge_coords)
        self.velem.di_edge.waypoints[self.wp_pos] = self.prev_waypoint

    def show(self, new_pos):
        new_edge_coords = list(self.start_edge_coords)
        new_edge_coords[self.wp_pos*2]   = new_pos[0]
        new_edge_coords[self.wp_pos*2+1] = new_pos[1]
        self.parent.canvas.coords(self.velem.edge, *new_edge_coords)


class AddWaypointAction(EditAction):
    def __init__(self, parent, velem, pos):
        EditAction.__init__(self, parent)

        self.prev_edge_coords = self.parent.canvas.coords(velem.edge)
        self.velem  = velem
        self.wp_pos = 0
        nearest  = 0
        min_dist = maxint
        # search in which waypoint pair is located the position
        for i in range(2, len(self.prev_edge_coords), 2):
            x1 = self.prev_edge_coords[i-2]
            x2 = self.prev_edge_coords[i]
            y1 = self.prev_edge_coords[i-1]
            y2 = self.prev_edge_coords[i+1]
            m  = (y2 - y1) / (x2 - x1) if x1 != x2 else 0
            if x2 == x1:
                self.wp_pos = i // 2
            else:
                line_eq = lambda x, y: m * (x - x1) - (y - y1)
                line_dist = abs(line_eq(*pos))
                if line_dist < min_dist:
                    min_dist = line_dist
                    nearest  = i // 2
        if self.wp_pos == 0:
            self.wp_pos = nearest
        self.new_edge_coords = list(self.prev_edge_coords)
        self.new_edge_coords.insert(self.wp_pos*2, pos[0])
        self.new_edge_coords.insert(self.wp_pos*2+1, pos[1])
        self.new_waypoint = BPMNDI_Waypoint(pos[0], pos[1])

    def redo(self):
        self.parent.canvas.coords(self.velem.edge, *self.new_edge_coords)
        self.velem.di_edge.waypoints.insert(self.wp_pos, self.new_waypoint)

    def undo(self):
        self.parent.canvas.coords(self.velem.edge, *self.prev_edge_coords)
        del self.velem.di_edge.waypoints[self.wp_pos]


class DelWaypointAction(EditAction):
    def __init__(self, parent, velem, wp_pos):
        EditAction.__init__(self, parent)

        self.velem = velem
        self.wp_pos = wp_pos
        self.prev_edge_coords = self.parent.canvas.coords(self.velem.edge)
        self.new_edge_coords  = list(self.prev_edge_coords)
        self.new_edge_coords.pop(self.wp_pos*2)
        self.new_edge_coords.pop(self.wp_pos*2)
        self.deleted_waypoint = self.velem.di_edge.waypoints[self.wp_pos]

    def redo(self):
        self.parent.canvas.coords(self.velem.edge, *self.new_edge_coords)
        del self.velem.di_edge.waypoints[self.wp_pos]

    def undo(self):
        self.parent.canvas.coords(self.velem.edge, *self.prev_edge_coords)
        self.velem.di_edge.waypoints.insert(self.wp_pos, self.deleted_waypoint)


class ShowNameAction(EditAction):
    def __init__(self, parent, velem):
        EditAction.__init__(self, parent)
        self.velem = velem

    def redo(self):
        self.velem.showname = True
        self.parent.canvas.itemconfigure(self.velem.name, state=NORMAL)

    def undo(self):
        self.velem.showname = False
        self.parent.canvas.itemconfigure(self.velem.name, state=HIDDEN)


class HideNameAction(ShowNameAction):
    def __init__(self, parent, velem):
        ShowNameAction.__init__(self, parent, velem)

    def redo(self):
        ShowNameAction.undo(self)

    def undo(self):
        ShowNameAction.redo(self)


class ResizeAction(EditAction):
    def __init__(self, parent, velem, start_pos):
        EditAction.__init__(self, parent)

        self.velem   = velem
        self.start_x = start_pos[0]
        self.start_y = start_pos[1]
        self.end_x   = start_pos[0]
        self.end_y   = start_pos[1]
        self.shape_bounds_start = velem.shape.bounds
        self.shape_bounds_end   = None
        self.move_edges = None

    def redo(self):
        if self.shape_bounds_end is None:
            # calculate the new bound of the shape
            x_dif  = self.end_x - self.start_x
            y_dif  = self.end_y - self.start_y
            minx   = self.shape_bounds_start.x - x_dif
            miny   = self.shape_bounds_start.y - y_dif
            maxx   = self.shape_bounds_start.x + self.shape_bounds_start.width  + x_dif
            maxy   = self.shape_bounds_start.y + self.shape_bounds_start.height + y_dif
            if maxx < minx:
                minx, maxx = maxx, minx
            if maxy < miny:
                miny, maxy = maxy, miny
            width  = maxx - minx
            height = maxy - miny
            self.shape_bounds_end = BPMNDI_Bounds(minx, miny, width, height)
            # calculate the new position of the edges
            if not self.velem.elem.type == "pool" and not self.velem.elem.type == "lane":
                self.move_edges = []
                cx = self.shape_bounds_start.x + self.shape_bounds_start.width  // 2
                cy = self.shape_bounds_start.y + self.shape_bounds_start.height // 2
                for inelem in self.velem.elem.inset:
                    edge_velem = self.parent.visual_elements[(inelem, self.velem.elem)]
                    move_edge_action = MoveWaypointAction(self.parent, edge_velem, -1, (cx, cy))
                    edge_pos = (move_edge_action.start_edge_coords[-2], move_edge_action.start_edge_coords[-1])
                    move_edge_action.end_x = cx + x_dif if edge_pos[0] > cx else cx - x_dif if edge_pos[0] < cx else cx
                    move_edge_action.end_y = cy + y_dif if edge_pos[1] > cy else cy - y_dif if edge_pos[1] < cy else cy
                    self.move_edges.append(move_edge_action)
                for outelem in self.velem.elem.outset:
                    edge_velem = self.parent.visual_elements[(self.velem.elem, outelem)]
                    move_edge_action = MoveWaypointAction(self.parent, edge_velem, 0, (cx, cy))
                    edge_pos = (move_edge_action.start_edge_coords[0], move_edge_action.start_edge_coords[1])
                    move_edge_action.end_x = cx + x_dif if edge_pos[0] > cx else cx - x_dif if edge_pos[0] < cx else cx
                    move_edge_action.end_y = cy + y_dif if edge_pos[1] > cy else cy - y_dif if edge_pos[1] < cy else cy
                    self.move_edges.append(move_edge_action)
        self.velem.shape.bounds = self.shape_bounds_end
        redraw_fn = self.parent.redraw_fn[self.velem.shape.bpmn_element.type]
        redraw_fn(self.velem.shape, self.velem.shape.bpmn_element)
        if self.move_edges is not None:
            for move_edge_action in self.move_edges:
                move_edge_action.redo()
        self.velem.shape.bpmn_element.width  = self.shape_bounds_end.width
        self.velem.shape.bpmn_element.height = self.shape_bounds_end.height

    def undo(self):
        self.velem.shape.bounds = self.shape_bounds_start
        redraw_fn = self.parent.redraw_fn[self.velem.shape.bpmn_element.type]
        redraw_fn(self.velem.shape, self.velem.shape.bpmn_element)
        if self.move_edges is not None:
            for move_edge_action in self.move_edges:
                move_edge_action.undo()
        self.velem.shape.bpmn_element.width  = self.shape_bounds_start.width
        self.velem.shape.bpmn_element.height = self.shape_bounds_start.height

    def show(self, new_pos):
        x_dif  = new_pos[0] - self.start_x
        y_dif  = new_pos[1] - self.start_y
        minx   = self.shape_bounds_start.x - x_dif
        miny   = self.shape_bounds_start.y - y_dif
        maxx   = self.shape_bounds_start.x + self.shape_bounds_start.width  + x_dif
        maxy   = self.shape_bounds_start.y + self.shape_bounds_start.height + y_dif
        width  = maxx - minx
        height = maxy - miny
        shape_bounds = BPMNDI_Bounds(minx, miny, width, height)
        self.velem.shape.bounds = shape_bounds
        redraw_fn = self.parent.redraw_fn[self.velem.shape.bpmn_element.type]
        redraw_fn(self.velem.shape, self.velem.shape.bpmn_element)


class RelayoutModelAction(EditAction):
    def __init__(self, parent):
        EditAction.__init__(self, parent)

        self.prev_diagram = self.parent.bpmn.diagrams

    def redo(self):
        #self.parent.save_diagram_changes()
        self.parent.bpmn.diagrams = []
        self.parent.layout_model()
        self._reset_velems()
        self.parent.redraw()

    def undo(self):
        self.parent.bpmn.diagrams = self.prev_diagram
        self._reset_velems()
        self.parent.redraw()

    def _reset_velems(self):
        for diagram in self.parent.bpmn.diagrams:
            plane = diagram.plane
            for shape in plane.shapes:
                elem = shape.bpmn_element
                velem = self.parent.visual_elements[elem]
                velem.shape = shape
            for diedge in plane.edges:
                edge = diedge.bpmn_element
                velem = self.parent.visual_elements[edge]
                velem.di_edge = diedge
