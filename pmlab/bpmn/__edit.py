from Tkinter import *
from __draw import BPMN_Draw, EditAction
import tkMessageBox
import __bpmn as mbpmn
from __bpmn_diagram import BPMNDI_Bounds, LANE_OFFSET


class BPMN_Edit(BPMN_Draw):
    def __init__(self, master, bpmn):
        BPMN_Draw.__init__(self, master, bpmn)
        master.wm_title("BPMN Edition")

    def exit_handler(self):
        if len(self.undo_stack) > 0 and tkMessageBox.askyesno(parent=self.master, title="Apply changes?", message="You want to keep the changes in the model?"):
            self.save_diagram_changes()
        else:
            while len(self.undo_stack) > 0:
                self.undo_action()
        self.master.destroy()

    def get_popup_menu(self, velem, elem):
        popup_menu = BPMN_Draw.get_popup_menu(self, velem, elem)

        if velem is None:
            popup_menu.add_command(label="New activity", command=self._new_activity())
            popup_menu.add_command(label="New event",    command=self._new_event())
            popup_menu.add_command(label="New gateway",  command=self._new_gateway())
            popup_menu.add_command(label="New pool",     command=self._new_pool())
            return popup_menu

        if velem.type == "shape":
            popup_menu.add_separator()
            popup_menu.add_command(label="Change name", command=self._change_element_name(elem))
            if isinstance(elem, mbpmn.BPMN_Element):
                popup_menu.add_command(label="Add connection", command=self._add_edge(velem))
                if isinstance(elem, mbpmn.Gateway):
                    subtype_menu = Menu(popup_menu.menu, tearoff=0)
                    if elem.subtype != "exclusive":
                        subtype_menu.add_command(label="Exclusive gateway", command=self._change_element_subtype(elem, "exclusive"))
                    if elem.subtype != "inclusive":
                        subtype_menu.add_command(label="Inclusive gateway", command=self._change_element_subtype(elem, "inclusive"))
                    if elem.subtype != "parallel":
                        subtype_menu.add_command(label="Parallel gateway",  command=self._change_element_subtype(elem, "parallel"))
                    popup_menu.add_cascade(label="Change subtype to", menu=subtype_menu)
                if isinstance(elem, mbpmn.Event):
                    subtype_menu = Menu(popup_menu.menu, tearoff=0)
                    if elem.subtype != "intermediate":
                        subtype_menu.add_command(label="Intermediate event", command=self._change_element_subtype(elem, "intermediate"))
                    if elem.subtype != "start":
                        subtype_menu.add_command(label="Start event", command=self._change_element_subtype(elem, "start"))
                    if elem.subtype != "end":
                        subtype_menu.add_command(label="End event", command=self._change_element_subtype(elem, "end"))
                    popup_menu.add_cascade(label="Change subtype to", menu=subtype_menu)
                popup_menu.add_command(label="Delete "+elem.type, command=self._del_elem(elem))
            if isinstance(elem, mbpmn.Pool):
                popup_menu.add_command(label="New lane",    command=self._new_lane(elem))
                popup_menu.add_command(label="Delete pool", command=self._del_pool(elem))
            if isinstance(elem, mbpmn.Lane):
                popup_menu.add_command(label="New activity", command=self._new_activity(elem))
                popup_menu.add_command(label="New event",    command=self._new_event(elem))
                popup_menu.add_command(label="New gateway",  command=self._new_gateway(elem))
                popup_menu.add_command(label="Delete lane",  command=self._del_lane(elem))

        if velem.type == "edge":
            popup_menu.add_command(label="Delete edge", command=self._del_edge(velem))

        return popup_menu

    def _add_edge(self, src_velem):
        add_edge_action = AddEdgeAction(self, src_velem)
        def do():
            self.canvas.unbind("<Button-3>")
            self.canvas.unbind("<Button-1>")
            self.canvas.unbind("<ButtonRelease-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<Control-Button-1>")
            self.canvas.bind("<Motion>", motion)
            self.canvas.bind("<Button-1>", left_click)
            self.canvas.bind("<Button-3>", cancel)
        def cancel(event=None):
            add_edge_action.cancel()
            reset_binds()
        def motion(event):
            self.mouse_pos = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            add_edge_action.show(self.mouse_pos)
        def left_click(event):
            self.mouse_pos = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            objs_id = self.canvas.find_overlapping(self.mouse_pos[0], self.mouse_pos[1], self.mouse_pos[0], self.mouse_pos[1])
            finished = False
            for obj_id in objs_id:
                selected_velem = self.id_to_velem.get(obj_id)
                if selected_velem is not None and isinstance(selected_velem.elem, mbpmn.BPMN_Element):
                    finish(selected_velem)
                    finished = True
            if not finished:
                add_point(self.mouse_pos)
        def add_point(point):
            add_edge_action.add_point(point)
        def finish(tgt_velem):
            can_connect = add_edge_action.end(tgt_velem)
            if can_connect:
                self.do_action(add_edge_action)
            reset_binds()
        def reset_binds():
            self.canvas.unbind("<Motion>")
            self.canvas.unbind("<Button-1>")
            self.canvas.unbind("<Button-3>")
            self.canvas.bind("<Button-3>", self.on_right_click)
            self.canvas.bind("<Button-1>", self.on_left_click)
            self.canvas.bind("<ButtonRelease-1>", self.on_stop_left_click)
            self.canvas.bind("<B1-Motion>", self.on_drag)
            self.canvas.bind("<Control-Button-1>", self.on_ctrl_left_click)
        return do

    def _del_edge(self, edge_velem):
        def do():
            self.do_action(DeleteEdgeAction(self, edge_velem))
        return do

    def _new_pool(self, parent_elem=None):
        def do():
            self.do_action(NewPoolAction(self, parent_elem, self.mouse_pos))
        return do

    def _new_lane(self, parent_pool=None):
        def do():
            if isinstance(parent_pool, mbpmn.Pool):
                self.do_action(NewLaneAction(self, parent_pool))
        return do

    def _new_activity(self, parent_elem=None):
        def do():
            self.do_action(NewElementAction(self, parent_elem, self.mouse_pos, "activity"))
        return do

    def _new_event(self, parent_elem=None):
        def do():
            self.do_action(NewElementAction(self, parent_elem, self.mouse_pos, "event"))
        return do

    def _new_gateway(self, parent_elem=None):
        def do():
            self.do_action(NewElementAction(self, parent_elem, self.mouse_pos, "gateway"))
        return do

    def _del_elem(self, elem):
        def do():
            self.do_action(DeleteElementAction(self, elem))
        return do

    def _del_pool(self, pool):
        def do():
            self.do_action(DeletePoolAction(self, pool))
        return do

    def _del_lane(self, lane):
        def do():
            self.do_action(DeleteLaneAction(self, lane))
        return do

    def _change_element_subtype(self, elem, newsubtype):
        def do():
            if newsubtype != elem.subtype and newsubtype in elem.allowed_subtypes:
                self.do_action(ChangeSubtypeAction(self, elem, newsubtype))
        return do

    def _change_element_name(self, elem):
        def do():
            """Opens a new window in which the name of the element can be changed"""
            text_ins = tkTextInsertion(self.master, "Change name", elem.name)
            self.master.wait_window(text_ins.toplevel)
            newname = text_ins.get_text()
            if newname is not None and newname != elem.name:
                self.do_action(ChangeNameAction(self, elem, newname))
        return do


class AddEdgeAction(EditAction):
    def __init__(self, parent, src_velem):
        EditAction.__init__(self, parent)

        self.src_velem = src_velem
        self.tgt_velem = None
        self.edge      = None
        self.diedge    = None
        body_coords    = self.parent.canvas.coords(src_velem.body)
        cx = (body_coords[0] + body_coords[2]) // 2
        cy = (body_coords[1] + body_coords[3]) // 2
        self.edge_coords  = [cx, cy, cx, cy]
        self.show_edge_id = self.parent.canvas.create_line(*self.edge_coords)
        self.edge_velem   = None
        for diagram in self.parent.bpmn.diagrams:
            plane = diagram.plane
            if self.src_velem.shape in diagram.plane.shapes:
                self.plane = plane
                break

    def redo(self):
        if self.edge_velem is None:
            self.edge = (self.src_velem.elem, self.tgt_velem.elem)
            self.diedge = self.plane.new_edge(self.edge)
            del self.plane.edges[-1]  # deleted to not instert it twice
            self.edge_velem = self.parent._create_new_edge(self.diedge, self.edge)

        if self.edge_velem.edge is None:
            self.edge_velem.edge = self.parent.canvas.create_line(0,0,0,0, arrow=LAST)

        self.src_velem.elem.process.add_connection(self.src_velem.elem, self.tgt_velem.elem)

        self.plane.edges.append(self.diedge)
        self.parent.canvas.coords(self.edge_velem.edge, *self.edge_coords)
        self.parent.visual_elements[self.edge] = self.edge_velem
        self.parent.id_to_velem[self.edge_velem.edge] = self.edge_velem

    def undo(self):
        self.src_velem.elem.process.del_connection(self.src_velem.elem, self.tgt_velem.elem)

        self.plane.edges.remove(self.diedge)
        self.parent.canvas.delete(self.edge_velem.edge)
        del self.parent.visual_elements[self.edge]
        del self.parent.id_to_velem[self.edge_velem.edge]
        self.edge_velem.edge = None

    def cancel(self):
        self.parent.canvas.delete(self.show_edge_id)

    def show(self, last_pos):
        self.edge_coords[-2] = last_pos[0]
        self.edge_coords[-1] = last_pos[1]
        self.parent.canvas.coords(self.show_edge_id, *self.edge_coords)

    def add_point(self, new_point):
        self.edge_coords[-2] = new_point[0]
        self.edge_coords[-1] = new_point[1]
        self.edge_coords.extend([new_point[0], new_point[1]])

    def end(self, tgt_velem):
        self.tgt_velem = tgt_velem
        self.parent.canvas.delete(self.show_edge_id)
        self.show_edge_id = None
        src_elem = self.src_velem.elem
        tgt_elem = self.tgt_velem.elem
        if src_elem.process is not tgt_elem.process:
            return False
        if tgt_elem in src_elem.outset:
            return False
        src_coords = self.parent.canvas.coords(self.src_velem.body)
        tgt_coords = self.parent.canvas.coords(self.tgt_velem.body)
        src_left   = min(src_coords[0::2])
        src_right  = max(src_coords[0::2])
        src_up     = min(src_coords[1::2])
        src_down   = max(src_coords[1::2])
        tgt_left   = min(tgt_coords[0::2])
        tgt_right  = max(tgt_coords[0::2])
        tgt_up     = min(tgt_coords[1::2])
        tgt_down   = max(tgt_coords[1::2])
        src_cx = (src_left + src_right) // 2
        src_cy = (src_up   + src_down)  // 2
        tgt_cx = (tgt_left + tgt_right) // 2
        tgt_cy = (tgt_up   + tgt_down)  // 2
        # calculate first point of edge
        if self.edge_coords[0] > self.edge_coords[2]:
            if self.edge_coords[1] == self.edge_coords[3]:
                self.edge_coords[0] = src_left
                self.edge_coords[1] = src_cy
            elif abs(self.edge_coords[3] - src_cy) <= abs(self.edge_coords[2] - src_cx):
                self.edge_coords[0] = src_left
                self.edge_coords[1] = src_cy
            else:
                if self.edge_coords[1] < self.edge_coords[3]:
                    self.edge_coords[0] = src_cx
                    self.edge_coords[1] = src_down
                else:
                    self.edge_coords[0] = src_cx
                    self.edge_coords[1] = src_up
        else:
            if self.edge_coords[1] == self.edge_coords[3]:
                self.edge_coords[0] = src_right
                self.edge_coords[1] = src_cy
            elif abs(self.edge_coords[3] - src_cy) <= abs(self.edge_coords[2] - src_cx):
                self.edge_coords[0] = src_right
                self.edge_coords[1] = src_cy
            else:
                if self.edge_coords[1] < self.edge_coords[3]:
                    self.edge_coords[0] = src_cx
                    self.edge_coords[1] = src_down
                else:
                    self.edge_coords[0] = src_cx
                    self.edge_coords[1] = src_up
        # calculate last point of edge
        if self.edge_coords[-2] > self.edge_coords[-4]:
            if self.edge_coords[-1] == self.edge_coords[-3]:
                self.edge_coords[-2] = tgt_left
                self.edge_coords[-1] = tgt_cy
            elif abs(self.edge_coords[-3] - tgt_cy) <= abs(self.edge_coords[-4] - tgt_cx):
                self.edge_coords[-2] = tgt_left
                self.edge_coords[-1] = tgt_cy
            else:
                if self.edge_coords[-1] < self.edge_coords[-3]:
                    self.edge_coords[-2] = tgt_cx
                    self.edge_coords[-1] = tgt_down
                else:
                    self.edge_coords[-2] = tgt_cx
                    self.edge_coords[-1] = tgt_up
        else:
            if self.edge_coords[-1] == self.edge_coords[-3]:
                self.edge_coords[-2] = tgt_right
                self.edge_coords[-1] = tgt_cy
            elif abs(self.edge_coords[-3] - tgt_cy) <= abs(self.edge_coords[-4] - tgt_cx):
                self.edge_coords[-2] = tgt_right
                self.edge_coords[-1] = tgt_cy
            else:
                if self.edge_coords[-1] < self.edge_coords[3]:
                    self.edge_coords[-2] = tgt_cx
                    self.edge_coords[-1] = tgt_down
                else:
                    self.edge_coords[-2] = tgt_cx
                    self.edge_coords[-1] = tgt_up
        return True


class DeleteEdgeAction(AddEdgeAction):
    def __init__(self, parent, edge_velem):
        self.src_velem = parent.visual_elements[edge_velem.elem[0]]
        AddEdgeAction.__init__(self, parent, self.src_velem)

        self.tgt_velem   = self.parent.visual_elements[edge_velem.elem[1]]
        self.edge_velem  = edge_velem
        self.edge_coords = self.parent.canvas.coords(self.edge_velem.edge)
        self.edge        = edge_velem.elem
        self.diedge      = self.edge_velem.di_edge
        for diagram in self.parent.bpmn.diagrams:
            plane = diagram.plane
            if self.src_velem.di_edge in diagram.plane.edges:
                self.plane = plane
                break

    def redo(self):
        AddEdgeAction.undo(self)

    def undo(self):
        AddEdgeAction.redo(self)


class NewElementAction(EditAction):
    def __init__(self, parent, parent_elem, pos, elemtype):
        EditAction.__init__(self, parent)
        self.parent_elem = parent_elem
        self.pos = pos
        if self.parent_elem is None:
            self.parent_elem = self.parent.bpmn.processes[0]
        self.elem  = None
        self.shape = None
        self.velem = None
        self.plane = None
        self.pindex = -1
        if elemtype == "activity":
            self.red_fn = self.parent._redraw_activity
            self.ele_cl = mbpmn.Activity
        elif elemtype == "event":
            self.red_fn = self.parent._redraw_event
            self.ele_cl = mbpmn.Event
        elif elemtype == "gateway":
            self.red_fn = self.parent._redraw_gateway
            self.ele_cl = mbpmn.Gateway

    def redo(self):
        if self.elem is None:
            self.elem = self.ele_cl(subtype=self.ele_cl.allowed_subtypes[0])
            self.plane = self.parent.bpmn.diagrams[0].plane
            self.shape = self.plane.new_shape(self.elem)
            del self.plane.shapes[-1]  # deleted to not insert it twice
            x = self.pos[0] - self.elem.width  // 2
            y = self.pos[1] - self.elem.height // 2
            self.shape.bounds = BPMNDI_Bounds(x, y, self.elem.width, self.elem.height)
            self.velem = self.parent._create_new_shape(self.shape)

        self.parent_elem.add_element(self.elem)
        self.parent.visual_elements[self.elem]   = self.velem
        self.parent.id_to_velem[self.velem.body] = self.velem
        self.parent.id_to_velem[self.velem.name] = self.velem
        if self.velem.showname:
            self.parent.canvas.itemconfigure(self.velem.name, state=NORMAL)
        self.parent.canvas.itemconfigure(self.velem.body, state=NORMAL)
        for dec in self.velem.decorations:
            self.parent.id_to_velem[dec] = self.velem
        self.plane.shapes.insert(self.pindex, self.shape)
        self.red_fn(self.shape, self.elem)

    def undo(self):
        del self.parent.visual_elements[self.elem]
        del self.parent.id_to_velem[self.velem.body]
        del self.parent.id_to_velem[self.velem.name]
        self.parent.canvas.coords(self.velem.body, 0,0,0,0)
        self.parent.canvas.itemconfigure(self.velem.body, state=HIDDEN)
        self.parent.canvas.itemconfigure(self.velem.name, state=HIDDEN)
        for dec in self.velem.decorations:
            del self.parent.id_to_velem[dec]
            self.parent.canvas.coords(dec, 0,0,0,0)
        self.elem.process.del_element(self.elem)
        self.plane.shapes.remove(self.shape)


class DeleteElementAction(NewElementAction):
    def __init__(self, parent, element):
        NewElementAction.__init__(self, parent, element.parent, (0,0), element.type)
        self.elem  = element
        self.velem = self.parent.visual_elements[self.elem]
        self.shape = self.velem.shape
        self.rem_edge_actions = []
        for diagram in self.parent.bpmn.diagrams:
            plane = diagram.plane
            if self.shape in diagram.plane.shapes:
                self.plane = plane
                self.pindex = self.plane.shapes.index(self.shape)
                break
        for inelem in self.elem.inset:
            edge_velem = self.parent.visual_elements[(inelem, self.elem)]
            del_edge_action = DeleteEdgeAction(self.parent, edge_velem)
            self.rem_edge_actions.append(del_edge_action)
        for outelem in self.elem.outset:
            edge_velem = self.parent.visual_elements[(self.elem, outelem)]
            del_edge_action = DeleteEdgeAction(self.parent, edge_velem)
            self.rem_edge_actions.append(del_edge_action)

    def redo(self):
        for del_edge_action in self.rem_edge_actions:
            del_edge_action.redo()
        NewElementAction.undo(self)

    def undo(self):
        NewElementAction.redo(self)
        for del_edge_action in self.rem_edge_actions:
            del_edge_action.undo()


class NewPoolAction(EditAction):
    def __init__(self, parent, parent_elem, pos):
        EditAction.__init__(self, parent)
        self.parent_elem = parent_elem
        self.pos = pos
        if self.parent_elem is None:
            self.parent_elem = self.parent.bpmn.processes[0]
        self.pool  = None
        self.shape = None
        self.velem = None
        self.index = -1
        self.plane = None
        self.pindex = 1

    def redo(self):
        if self.pool is None:
            self.pool = self.parent_elem.new_pool()
            self.plane = self.parent.bpmn.diagrams[0].plane
            self.shape = self.plane.new_shape(self.pool)
            del self.plane.shapes[-1]  # deleted to not insert it twice
            x = self.pos[0] - self.pool.width  // 2
            y = self.pos[1] - self.pool.height // 2
            self.shape.bounds = BPMNDI_Bounds(x, y, self.pool.width, self.pool.height)
            self.velem = self.parent._create_new_shape(self.shape)

        self.parent_elem.pools.insert(self.index, self.pool)
        self.parent.visual_elements[self.pool]   = self.velem
        self.parent.id_to_velem[self.velem.body] = self.velem
        self.parent.id_to_velem[self.velem.name] = self.velem
        self.parent.canvas.itemconfigure(self.velem.body, state=NORMAL)
        self.plane.shapes.insert(self.pindex, self.shape)
        self.parent._redraw_pool(self.shape, self.pool)

    def undo(self):
        del self.parent.visual_elements[self.pool]
        del self.parent.id_to_velem[self.velem.body]
        del self.parent.id_to_velem[self.velem.name]
        self.parent.canvas.coords(self.velem.body, 0,0,0,0)
        self.parent.canvas.itemconfigure(self.velem.body, state=HIDDEN)
        self.parent.canvas.itemconfigure(self.velem.name, state=HIDDEN)
        self.plane.shapes.remove(self.shape)
        self.parent_elem.pools.remove(self.pool)


class DeletePoolAction(NewPoolAction):
    def __init__(self, parent, pool):
        NewPoolAction.__init__(self, parent, pool.process, (0,0))
        self.pool  = pool
        self.velem = self.parent.visual_elements[self.pool]
        self.shape = self.velem.shape
        self.index = self.pool.process.pools.index(self.pool)
        for diagram in self.parent.bpmn.diagrams:
            plane = diagram.plane
            if self.shape in diagram.plane.shapes:
                self.plane = plane
                self.pindex = self.plane.shapes.index(self.shape)
                break
        self.del_lanes = []
        for lane in self.pool.lanes:
            del_lane_action = DeleteLaneAction(self.parent, lane)
            self.del_lanes.append(del_lane_action)

    def redo(self):
        for del_lane_action in self.del_lanes:
            del_lane_action.redo()
        NewPoolAction.undo(self)

    def undo(self):
        NewPoolAction.redo(self)
        for del_lane_action in self.del_lanes:
            del_lane_action.undo()


class NewLaneAction(EditAction):
    def __init__(self, parent, parent_elem):
        EditAction.__init__(self, parent)

        self.parent_elem = parent_elem
        self.lane  = None
        self.shape = None
        self.velem = None
        self.index = -1
        self.plane = None
        self.pindex = 1
        self.pool_velem = self.parent.visual_elements[self.parent_elem]
        self.pool_shape = self.pool_velem.shape
        self.pool_prev_bounds = self.pool_velem.shape.bounds
        self.pool_new_bounds  = None

    def redo(self):
        if self.lane is None:
            self.lane = self.parent_elem.new_lane()
            self.plane = self.parent.bpmn.diagrams[0].plane
            self.shape = self.plane.new_shape(self.lane)
            del self.plane.shapes[-1]  # deleted to not insert it twice
            self.pindex = 0
            # search where to insert the pool shape: right after the last pool
            for shape in self.plane.shapes:
                if shape.bpmn_element.type != "pool":
                    break
                self.pindex += 1
            x = self.pool_shape.bounds.x + LANE_OFFSET
            y = self.pool_shape.bounds.y + self.pool_shape.bounds.height
            width = max(self.lane.width, self.pool_shape.bounds.width - LANE_OFFSET)
            self.shape.bounds = BPMNDI_Bounds(x, y, width, self.lane.height)
            self.velem = self.parent._create_new_shape(self.shape)
            self.pool_new_bounds = BPMNDI_Bounds(self.pool_shape.bounds.x, self.pool_shape.bounds.y, self.pool_shape.bounds.width, self.pool_shape.bounds.height + self.lane.height)

        self.parent_elem.lanes.insert(self.index, self.lane)
        self.parent.visual_elements[self.lane]   = self.velem
        self.parent.id_to_velem[self.velem.body] = self.velem
        self.parent.id_to_velem[self.velem.name] = self.velem
        self.parent.canvas.itemconfigure(self.velem.body, state=NORMAL)
        self.parent._redraw_lane(self.shape, self.lane)
        self.pool_shape.bounds = self.pool_new_bounds
        self.plane.shapes.insert(self.pindex, self.shape)
        self.parent._redraw_pool(self.pool_shape, self.parent_elem)

    def undo(self):
        del self.parent.visual_elements[self.lane]
        del self.parent.id_to_velem[self.velem.body]
        del self.parent.id_to_velem[self.velem.name]
        self.parent.canvas.coords(self.velem.body, 0,0,0,0)
        self.parent.canvas.itemconfigure(self.velem.body, state=HIDDEN)
        self.parent.canvas.itemconfigure(self.velem.name, state=HIDDEN)
        self.parent_elem.lanes.remove(self.lane)
        self.plane.shapes.remove(self.shape)
        self.pool_shape.bounds = self.pool_prev_bounds
        self.parent._redraw_pool(self.pool_shape, self.parent_elem)


class DeleteLaneAction(NewLaneAction):
    def __init__(self, parent, lane):
        NewLaneAction.__init__(self, parent, lane.parent)
        self.lane  = lane
        self.velem = self.parent.visual_elements[self.lane]
        self.shape = self.velem.shape
        self.index = self.lane.parent.lanes.index(self.lane)
        self.pool_new_bounds = self.pool_prev_bounds
        for diagram in self.parent.bpmn.diagrams:
            plane = diagram.plane
            if self.shape in diagram.plane.shapes:
                self.plane = plane
                self.pindex = self.plane.shapes.index(self.shape)
                break

    def redo(self):
        self.elem_del = []
        while len(self.lane.elements) > 0:
            elem = self.lane.elements[0]
            elem_del_action = DeleteElementAction(self.parent, elem)
            elem_del_action.redo()
            self.elem_del.append(elem_del_action)
        NewLaneAction.undo(self)

    def undo(self):
        NewLaneAction.redo(self)
        self.elem_del.reverse()
        for elem_del_action in self.elem_del:
            elem_del_action.undo()


class ChangeSubtypeAction(EditAction):
    def __init__(self, parent, elem, newsubtype):
        EditAction.__init__(self, parent)
        self.elem = elem
        self.velem = self.parent.visual_elements[self.elem]
        self.newsubtype = newsubtype
        self.oldsubtype = elem.subtype

    def redo(self):
        self.elem.change_subtype(self.newsubtype)
        self._adapt_velem()
        if self.elem.type == "gateway":
            self.parent._redraw_gateway(self.velem.shape, self.elem)
        elif self.elem.type == "event":
            self.parent._redraw_event(self.velem.shape, self.elem)

    def undo(self):
        self.elem.change_subtype(self.oldsubtype)
        self._adapt_velem()
        if self.elem.type == "gateway":
            self.parent._redraw_gateway(self.velem.shape, self.elem)
        elif self.elem.type == "event":
            self.parent._redraw_event(self.velem.shape, self.elem)

    def _adapt_velem(self):
        if self.elem.type == "gateway":
            self._redo_gateway_decorations()
        elif self.elem.type == "event":
            self.parent.canvas.itemconfigure(self.velem.body, fill=self.elem.color)

    def _redo_gateway_decorations(self):
        while len(self.velem.decorations) > 0:
            cid = self.velem.decorations.pop()
            self.parent.canvas.delete(cid)
            del self.parent.id_to_velem[cid]
        if self.elem.subtype == "exclusive" and self.velem.shape.is_marker_visible:
            first_line  = self.parent.canvas.create_line(0, 0, 0, 0)
            second_line = self.parent.canvas.create_line(0, 0, 0, 0)
            self.velem.decorations.append(first_line)
            self.velem.decorations.append(second_line)
            self.parent.id_to_velem[first_line]  = self.velem
            self.parent.id_to_velem[second_line] = self.velem
        elif self.elem.subtype == "inclusive":
            inner_circle = self.parent.canvas.create_oval(0, 0, 0, 0)
            self.velem.decorations.append(inner_circle)
            self.parent.id_to_velem[inner_circle] = self.velem
        elif self.elem.subtype == "parallel":
            horizontal_line = self.parent.canvas.create_line(0, 0, 0, 0)
            vertical_line   = self.parent.canvas.create_line(0, 0, 0, 0)
            self.velem.decorations.append(horizontal_line)
            self.velem.decorations.append(vertical_line)
            self.parent.id_to_velem[horizontal_line] = self.velem
            self.parent.id_to_velem[vertical_line]   = self.velem


class ChangeNameAction(EditAction):
    def __init__(self, parent, elem, newname):
        EditAction.__init__(self, parent)
        self.elem    = elem
        self.velem   = self.parent.visual_elements[elem]
        self.newname = newname
        self.oldname = elem.name

    def redo(self):
        self.elem.name = self.newname
        del self.elem.process.name_to_elem[self.oldname]
        self.elem.process.name_to_elem[self.newname] = self.elem
        self.parent.canvas.itemconfigure(self.velem.name, text=self.newname)

    def undo(self):
        self.elem.name = self.oldname
        del self.elem.process.name_to_elem[self.newname]
        self.elem.process.name_to_elem[self.oldname] = self.elem
        self.parent.canvas.itemconfigure(self.velem.name, text=self.oldname)


class tkTextInsertion:
    def __init__(self, root, titleText="", defaultText=None, width=30):
        self.toplevel = Toplevel()
        self.toplevel.title(titleText)
        self.text = Text(self.toplevel, height=1, width=width)
        self.text.pack(fill=X)
        if defaultText is not None:
            self.text.insert("1.0", defaultText)
        self.text.bind("<Return>", self.ok)
        self.text.focus()
        okbutton = Button(self.toplevel, text="OK", command=self.ok)
        okbutton.pack(side=LEFT, fill=X, expand=1)
        cancelbutton = Button(self.toplevel, text="Cancel", command=self.toplevel.destroy)
        cancelbutton.pack(side=LEFT, fill=X, expand=1)
        self.__text = None

    def ok(self, ev=None):
        self.__text = self.text.get("1.0", "1.end")
        self.toplevel.destroy()

    def get_text(self):
        return self.__text
