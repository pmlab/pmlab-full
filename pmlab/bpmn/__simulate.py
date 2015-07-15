from __draw import BPMN_Draw
from datetime import datetime, timedelta
from Tkinter import *
from sys import maxint
import os.path
import math

_tick_delay = 1000
_anim_delay = 20
_borderwidth_on_active = 3
_anim_elem_size = 6


class BPMN_Simulate(BPMN_Draw):
    def __init__(self, master, bpmn, cases):
        # cases is a list of cases, where a case is a list in the format:
        # (event object, start time, end time)
        BPMN_Draw.__init__(self, master, bpmn)
        master.wm_title("BPMN Simulation")
        self.cases = cases

        self.toggle_lock()

        frame = Frame(master)

        vcmd = (master.register(self._num_entry_validate),
                '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')

        self.case_text = Label(frame, text="Steps:")
        self.case_text.grid(row=0, column=0, sticky=W+E+N+S)

        self.num_entry = Spinbox(frame, increment=1, from_=1, to=maxint, validate='all', validatecommand=vcmd)
        self.num_entry.grid(row=0, column=1, sticky=W+E+N+S)

        self.increm_options = ["seconds", "minutes", "hours", "days"]
        self.increm_var = StringVar()
        self.increm_var.set(self.increm_options[0])
        self.increm_sel = OptionMenu(frame, self.increm_var, *self.increm_options)
        self.increm_sel.grid(row=0, column=2, sticky=W+N+E+S)

        img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graphics")

        self.prev_but = Button(frame, command=self.on_prev_button)
        self.prev_but.grid(row=0, column=3, sticky=W+E+N+S)
        self.prev_img = PhotoImage(file=os.path.join(img_dir, "skip-backward.gif"))
        self.prev_but.config(image=self.prev_img, width=24, height=24)

        self.play_but = Button(frame, command=self.on_play_button)
        self.play_but.grid(row=0, column=4, sticky=W+E+N+S)
        self.play_img = PhotoImage(file=os.path.join(img_dir, "play.gif"))
        self.play_but.config(image=self.play_img, width=24, height=24)
        self.pause_img = PhotoImage(file=os.path.join(img_dir, "pause.gif"))

        self.stop_but = Button(frame, command=self.on_stop_button)
        self.stop_but.grid(row=0, column=5, sticky=W+E+N+S)
        self.stop_img = PhotoImage(file=os.path.join(img_dir, "stop.gif"))
        self.stop_but.config(image=self.stop_img, width=24, height=24)

        self.next_but = Button(frame, command=self.on_next_button)
        self.next_but.grid(row=0, column=6, sticky=W+E+N+S)
        self.next_img = PhotoImage(file=os.path.join(img_dir, "skip-forward.gif"))
        self.next_but.config(image=self.next_img, width=24, height=24)

        self.case_text = Label(frame, text="Case:")
        self.case_text.grid(row=0, column=7, sticky=W+E+N+S)

        self.case_options = range(1, len(self.cases)+1)
        self.case_var = StringVar()
        self.case_var.set(self.case_options[0])
        self.case_sel = OptionMenu(frame, self.case_var, *self.case_options)
        self.case_sel.grid(row=0, column=8, sticky=W+E+N+S)

        frame.pack(anchor=W)

        frame2 = Frame(master)

        self.currt_lab = Label(frame2, text="Current time:")
        self.currt_lab.grid(row=0, column=0, sticky=W+N+S)

        self.currt_var = StringVar()
        self.currt = Label(frame2, textvariable=self.currt_var)
        self.currt.grid(row=0, column=1, sticky=W+N+S)

        frame2.pack(anchor=W)

        self.case_var.trace("w", self.on_case_change)

        self.simulating = "stop"
        self.last_tick  = datetime.now()
        self.anim_tick  = datetime.now()
        self.animations = {}
        #self._init_sim(self.get_case())

    def on_play_button(self):  # toggle play/pause
        if self.simulating == "stop":
            self._init_sim(self.get_case())
            self._play()
        elif self.simulating == "pause":
            self._play()
        elif self.simulating == "play":
            self._pause()

    def on_stop_button(self):
        self._stop()

    def on_prev_button(self):
        if self.simulating == "stop":
            self._init_sim(self.get_case())
            return
        elif self.simulating == "play":
            self._pause()
        prev_state = self.current_time - self.get_delta()
        self._stop()
        self._init_sim(self.get_case())
        self.simulating = "pause"
        if prev_state < (self.get_case()[0][1] - self.get_delta()):
            prev_state = self.get_case()[0][1] - self.get_delta()
            return
        curr_state = self.current_time
        self._step_back(prev_state, curr_state)
        self._anim_step_back(prev_state, curr_state)

    def on_next_button(self):
        if self.simulating == "stop":
            self._init_sim(self.get_case())
            self.simulating = "pause"
        elif self.simulating == "play":
            self._pause()
        self._step_forward()
        self._anim_step_forward(self.get_delta())

    def on_case_change(self, *args):
        self._stop()

    def _step_back(self, back_to, curr_time):
        self._step_forward(back_to - curr_time)
        self._step_forward(timedelta(0))

    def _anim_step_back(self, back_to, curr_time):
        self._anim_step_forward(back_to - curr_time)
        self._anim_step_forward(timedelta(0))

    def _play(self):
        self.simulating = "play"
        self.play_but.config(image=self.pause_img)
        self.currt_var.set(self.current_time.isoformat())
        self.last_tick = datetime.now()
        self.anim_tick = datetime.now()
        self.master.after(_tick_delay, self._sim)
        self.master.after(_anim_delay, self._anim)

    def _pause(self):
        self.simulating = "pause"
        self.play_but.config(image=self.play_img)
        time_passed = datetime.now() - self.last_tick
        time_percentage = (time_passed.total_seconds() * 1000) / _tick_delay
        delta_secs = self.get_delta().total_seconds() * time_percentage
        self.current_time = self.current_time + timedelta(seconds=delta_secs)
        self.currt_var.set(self.current_time.isoformat())

    def _stop(self):
        self.simulating = "stop"
        self.play_but.config(image=self.play_img)
        self.currt_var.set("")
        while len(self.started_evs) > 0:
            self._end_event(self.started_evs[0][0])
            del self.started_evs[0]
        for anim in self.animations.values():
            self.canvas.delete(anim[1])  # delete animation elements
        self.animations = {}

    def get_delta(self):
        nstr = self.num_entry.get()
        if nstr == "":
            nstr = "1"
        n = int(nstr)
        increm = self.increm_var.get()
        if increm == "seconds":
            return timedelta(seconds=n)
        elif increm == "minutes":
            return timedelta(minutes=n)
        elif increm == "hours":
            return timedelta(hours=n)
        elif increm == "days":
            return timedelta(days=n)
        return timedelta(seconds=n)

    def get_case(self):
        n = int(self.case_var.get())
        return self.cases[n-1]

    def _init_sim(self, case):
        self.current_case = case
        first_ev_elem, first_ev_start, first_ev_end = self.current_case[0]
        self.current_time = first_ev_start - self.get_delta()
        self.started_evs  = []
        self.next_ev_pos  = 0
        self.animations   = {}
        self._animate_to_next(first_ev_elem.process.start_event, first_ev_elem, first_ev_start - self.current_time)

    def _sim(self):
        if self.simulating == "play":
            self._step_forward()
            self.last_tick = datetime.now()
            self.master.after(_tick_delay, self._sim)

    def _anim(self):
        if self.simulating == "play":
            self._anim_step_forward()
            self.master.after(_anim_delay, self._anim)

    def _anim_step_forward(self, step=None):  # step = timedelta with the virtual time step
        # calculate the virtual time passed since last animation tick
        prev_tick = self.anim_tick
        self.anim_tick = datetime.now()
        rtime = (self.anim_tick - prev_tick).total_seconds()
        if step is None:
            vtime = (rtime * self.get_delta().total_seconds()) / (_tick_delay / 1000)  # tick_delay is divided by 1000 because its in miliseconds
        else:
            vtime = step.total_seconds()
        # for each edge, animate only if the prerequisites are fulfilled
        for edge in self.animations.keys():
            edge_seq, elem_id, prereq = self.animations[edge]
            all_prereq_done = True
            for prereq_edge in prereq:
                prereq_anim = self.animations.get(prereq_edge)
                if prereq_anim is not None:
                    all_prereq_done = False
            if not all_prereq_done:
                continue
            delta = vtime
            while len(edge_seq) > 0 and edge_seq[0][0] < edge_seq[0][1]:
                elapsed, total, fpoint, spoint = edge_seq[0]
                elapsed += delta
                if elapsed <= total:
                    # calculate new pos for animation elem
                    mult = elapsed / total
                    xdif = spoint[0] - fpoint[0]
                    newx = fpoint[0] + mult * xdif
                    ydif = spoint[1] - fpoint[1]
                    newy = fpoint[1] + mult * ydif
                    self._set_anim_elem_pos(elem_id, newx, newy)
                    # assign new elapsed time to anim
                    edge_seq[0] = (elapsed, total, fpoint, spoint)
                    break  # break while
                else:
                    delta = elapsed - total
                    del edge_seq[0]
            # if animations finished, delete animation from active animations
            if len(edge_seq) == 0:
                self.canvas.delete(elem_id)
                del self.animations[edge]

    def _step_forward(self, step=None):
        if step is None:
            self.current_time = self.current_time + self.get_delta()
        else:
            self.current_time = self.current_time + step
        self.currt_var.set(self.current_time.isoformat())
        # compute ending events
        while len(self.started_evs) > 0 and self.started_evs[0][2] <= self.current_time:
            self._end_event(self.started_evs[0][0])
            next_ev = self._get_next_event_from(self.current_case.index(self.started_evs[0], 0, self.next_ev_pos))
            self._animate_to_next(self.started_evs[0][0], next_ev[0], next_ev[1] - self.started_evs[0][2])
            del self.started_evs[0]
        # compute starting events
        while self.next_ev_pos < len(self.current_case) and self.current_case[self.next_ev_pos][1] <= self.current_time:
            if self.next_ev_pos == len(self.current_case):
                self.on_stop()
            else:
                next_ev = self.current_case[self.next_ev_pos]
                self.started_evs.append(next_ev)
                self._start_event(next_ev[0])
                self.next_ev_pos += 1
        self.started_evs.sort(key=lambda ev: ev[2])  # sort by end time

    def _step_backward(self):
        self.current_time = self.current_time - self.get_delta()

    def _start_event(self, ev_element):
        velem = self.visual_elements.get(ev_element)
        if velem is not None:
            self.canvas.itemconfig(velem.body, outline="red", width=_borderwidth_on_active)

    def _end_event(self, ev_element):
        velem = self.visual_elements.get(ev_element)
        if velem is not None:
            self.canvas.itemconfig(velem.body, outline="black", width=1)

    # self.animations is a dictionary with edge->edge_animation
    # where each edge_animation is a list of tuples with: the elapsed time,
    # the total duration, the first point and the last point for each segment
    # of the edge, and a id for the visual element on the canvas doing the animation
    # and a list of the edge prerequisites for the animation
    #   so: edge_animation = ([tuples], velem_id, [prerequisites])
    def _animate_to_next(self, from_elem, to_elem, delta):
        path = self._find_path(from_elem, to_elem)
        if len(path) == 0:
            print "Error: Path not found from", from_elem.name if from_elem.name is not None else from_elem.internal_name, \
                  "to", to_elem.name if to_elem.name is not None else to_elem.internal_name
            return

        total_time = delta.total_seconds()
        time_for_edge = total_time / (len(path) - 1)  # same time for all animations in the path
        prev_edge = None
        for i in range(len(path)-1):
            edge = (path[i], path[i+1])
            if edge in self.animations:
                # if the animation exists, ingore it but add the previous edge as
                # a prerequisite
                if prev_edge is not None:
                    self.animations[edge][2].append(prev_edge)
                continue
            prereq = [prev_edge] if prev_edge is not None else []
            prev_edge   = edge
            edge_velem  = self.visual_elements[edge]
            edge_coords = self.canvas.coords(edge_velem.edge)
            edge_length = self._get_edge_length(edge_coords)
            edge_anim = []
            # calculate the segments of the edge
            for i in range(0, len(edge_coords)-2, 2):
                x_length = edge_coords[i+2] - edge_coords[i]
                y_length = edge_coords[i+3] - edge_coords[i+1]
                segm_length = math.sqrt(x_length * x_length + y_length * y_length)
                segm_perc = segm_length / edge_length
                segm_time = time_for_edge * segm_perc
                edge_anim.append((0, segm_time, (edge_coords[i], edge_coords[i+1]), (edge_coords[i+2], edge_coords[i+3])))
            self.animations[edge] = (edge_anim, self._get_anim_elem(), prereq)

    def _get_anim_elem(self):
        eid = self.canvas.create_oval(0, 0, 0, 0, fill="red")
        self.canvas.itemconfig(eid, state=HIDDEN)
        return eid

    def _set_anim_elem_pos(self, elem_id, x, y):
        x0 = x - _anim_elem_size // 2
        y0 = y + _anim_elem_size // 2
        x1 = x + _anim_elem_size // 2
        y1 = y - _anim_elem_size // 2
        self.canvas.coords(elem_id, x0, y0, x1, y1)
        self.canvas.itemconfig(elem_id, state=NORMAL)

    def _find_path(self, src, tgt):
        visited = set()
        to_visit = [src]
        came_from = {}
        while len(to_visit) > 0:
            elem = to_visit[0]
            del to_visit[0]

            if elem in visited:
                continue
            # if path found, redo path and return
            if elem is tgt and src in visited:  # elem in visited for the case where src = tgt
                path = []
                prev_elem = elem
                while prev_elem is not src:
                    path.append(prev_elem)
                    prev_elem = came_from[prev_elem]
                path.append(src)
                path.reverse()
                return path

            visited.add(elem)
            for outelem in elem.outset:
                came_from[outelem] = elem
                to_visit.append(outelem)
        return []  # if no path found, return an empty path

    def _get_next_event_from(self, from_index):
        if from_index == len(self.current_case) - 1:  # when is last event in case
            ev_proc = self.current_case[from_index][0].process
            end_t   = self.current_case[from_index][2] + self.get_delta()
            return (ev_proc.end_event, end_t, end_t)
        for i in range(from_index + 1, len(self.current_case)):
            nfrom = self.current_case[from_index]
            nto   = self.current_case[i]
            path  = self._find_path(nfrom[0], nto[0])
            if len(path) != 0:
                return nto
        return None

    def _num_entry_validate(self, action, index, value_if_allowed,
                            prior_value, text, validation_type,
                            trigger_type, widget_name):
        if text in '0123456789':
            try:
                if value_if_allowed == "":
                    return True
                v = int(value_if_allowed)
                if v > 0:
                    return True
            except ValueError:
                return False
        return False

    def _get_edge_length(self, edge_coords):
        length = 0
        for i in range(0, len(edge_coords)-2, 2):
            x_length = edge_coords[i+2] - edge_coords[i]
            y_length = edge_coords[i+3] - edge_coords[i+1]
            length += math.sqrt(x_length * x_length + y_length * y_length)
        return length


def format_data(bpmn, log, start_key, end_key, time_format):
    valid_cases = []
    for case in log.cases:
        ccase = []
        valid_case = True
        for event in case:
            event_name = event.get("name")
            start_time = event.get(start_key)
            end_time   = event.get(end_key)
            # check that the needed data is present
            if event_name is None or start_time is None or end_time is None:
                valid_case = False
                break  # break the event-case for
            # search the bpmn_element corresponding to that log event
            event_elem = None
            for process in bpmn.processes:
                event_elem = process.name_to_elem.get(event_name)
                if event_elem is not None:
                    break  # break process-bpmn.processes for
                else:
                    # if not found by name, try searching with the same name, but removing whitespaces
                    event_elem = process.name_to_elem.get(event_name.replace(" ", ""))
                    if event_elem is not None:
                        break  # break process-bpmn.processes for
            # if the bpmn_element is not found, the case is discarded
            if event_elem is None:
                valid_case = False
                break  # break event-case for
            # time converted from string to a python class
            start_time = datetime.strptime(start_time, time_format)
            end_time   = datetime.strptime(end_time, time_format)
            ccase.append((event_elem, start_time, end_time))
        if valid_case:
            ccase.sort(key=lambda ev: ev[1])  # sort by start time
            valid_cases.append(ccase)
    if len(valid_cases) == 0:
        return False, None
    return True, valid_cases


def format_data2(bpmn, log, time_key, state_key, time_format, start_w, end_w):
    valid_cases = []
    for case in log.cases:
        ccase = []
        valid_case = True
        for event in case:
            event_name  = event.get("name")
            event_time  = event.get(time_key)
            event_state = event.get(state_key)
            # check that the needed data is present
            if event_name is None or event_time is None or event_state is None:
                valid_case = False
                break  # break the event-case for
            # time converted from string to a python class
            event_time = datetime.strptime(event_time, time_format)
            if event_state == start_w:
                # if event = start, search the corresponding bpmn_element
                event_elem = None
                for process in bpmn.processes:
                    event_elem = process.name_to_elem.get(event_name)
                    if event_elem is not None:
                        break  # break process-bpmn.processes for
                    else:
                        # if not found by name, try searching with the same name, but removing whitespaces
                        event_elem = process.name_to_elem.get(event_name.replace(" ", ""))
                        if event_elem is not None:
                            break  # break process-bpmn.processes for
                ccase.append((event_elem, event_time, event_time))
            elif event_state == end_w:
                # if event = end, search the event in the case where it started and store the finishing time
                for i in range(len(ccase)):
                    celem, ctime1, ctime2 = ccase[i]
                    if celem.name == event_name and ctime1 == ctime2:
                        ccase[i] = (celem, ctime1, event_time)
                        break  # break the cevent-ccase for
            else:
                print ("Warning: Unknown word found in the {0} field. Check the log and the parameters of the simulate method").format(state_key)
                valid_case = False
                break  # break the event-case for
        if valid_case:
            ccase.sort(key=lambda ev: ev[1])  # sort by start time
            valid_cases.append(ccase)
    if len(valid_cases) == 0:
        return False, None
    return True, valid_cases
