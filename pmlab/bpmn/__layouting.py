from sys import maxint


def is_join(node):
    return False if node is None else len(node.inset) > 1


def is_split(node):
    return False if node is None else len(node.outset) > 1


class BPMN_Layouter:
    class GridContext:
        def __init__(self, grid):
            self.grid = grid
            self.start_cell = grid.get(0, 0)

    def __init__(self, bpmn):
        self.bpmn = bpmn
        self.supergrid = SuperGrid()
        self._do_layout_algorithm()

    def _do_layout_algorithm(self):
        for process in self.bpmn.processes:
            self._layout_process(process)

        self.supergrid.pack()
        self.supergrid.set_geometry()

        edge_layouter = Edge_Layouter(self.bpmn, self.supergrid)
        self.edges    = edge_layouter.edges

    def _layout_process(self, process):
        topological_sorter = TopologicalSorter(process)
        self._do_layout(process, topological_sorter.get_sorted_elements())
        topological_sorter.restore_edges()

    def _do_layout(self, process, sorted_elements):
        self.parent2context = {}

        self._prepare_lanes(process)
        self._layout_elements(sorted_elements)

    def _layout_elements(self, sorted_elements):
        for element in sorted_elements:
            context = self.parent2context[element.parent]
            cell_of_element = self._place_element(element, context)
            comes_from_other_grid = len(element.inset) == 1 and element.inset[0].parent != element.parent
            if not is_join(element) and not comes_from_other_grid and cell_of_element.prev_cell is not None:
                # there is an edge hitting us left, so lets forbid
                # interleaving to use the left cell, if it's empty
                cell_of_element.prev_cell.packable = False

            if is_split(element):
                self._prelayout_successors(element, context, cell_of_element)

    def _prelayout_successors(self, element, context, cell_of_element):
        # prelayout following elements
        base_cell = cell_of_element.after()
        top_cell  = base_cell
        following_elements = element.outset

        # heuristic for direct connection to join
        direct_join = None
        for possible_join in following_elements:
            if is_join(possible_join):
                direct_join = possible_join
        if direct_join is not None:
            # put it in the middle
            following_elements.remove(direct_join)
            position = len(following_elements) / 2  # put the join in the middle
            following_elements.insert(position, direct_join)

        # normal preLayout following Elements
        follow = 0
        for new_elem in following_elements:
            if new_elem.parent is element.parent:
                follow += 1
        for i in range(follow // 2):
            top_cell.parent.insert_row_above()
            base_cell.parent.insert_row_beneath()
            top_cell = top_cell.above()

        for new_elem in following_elements:
            if new_elem.parent is not element.parent:
                continue
            # context.grid.set_cell_of_item(new_elem, top_cell)
            top_cell.set_content(new_elem)  # prelayout
            top_cell = top_cell.beneath()
            if top_cell is base_cell and follow % 2 == 0:
                # skip base_cell if an even amount of elements is following
                top_cell = top_cell.beneath()

    def _place_element(self, element, context):
        new_cell = None
        if len(element.inset) == 0:
            # start event
            context.start_cell.set_content(element)
            new_cell = context.start_cell
            context.start_cell = context.start_cell.beneath()
        else:
            left_cell = None
            new_cell = context.grid.item_to_cell.get(element)
            # new_cell is not None if its a join
            if is_join(element):
                split_found = False
                split = self._prev_split(element)
                if split is not None:
                    # get all close splits
                    splits = [split]
                    for prevelem in element.inset:
                        split = self._prev_split(prevelem)
                        if split[0] is not None and split not in splits:
                            splits.append(split)
                    splits.sort(key=lambda split: split[1])  # we order the splits by distance
                    split = None
                    # get split with most connections
                    max_con = 0
                    for target, dist in splits:
                        if target is element:
                            # being my own split only makes trouble
                            continue
                        elif target.parent is not element.parent:
                            continue
                        cur_con = 0
                        for prevelem in element.inset:
                            if self._back_distance(prevelem, target) < maxint:
                                cur_con += 1
                            if cur_con > max_con:
                                max_con = cur_con
                                split = target
                        split_found = True if split is not None else False
                x     = 0
                y_acc = 0
                y_cnt = 0
                for prevelem in element.inset:
                    tmp = context.grid.find(context.grid.item_to_cell.get(prevelem))
                    if tmp is None:
                        pre_grid = self.parent2context[prevelem.parent].grid
                        tmp = pre_grid.find(pre_grid.item_to_cell.get(prevelem))
                        if tmp is None:
                            tmpx = tmpy = 0
                        else:
                            tmpx, tmpy = tmp
                    else:
                        tmpx, tmpy = tmp
                        y_acc += tmpy
                        y_cnt += 1
                    x = max(x, tmpx)
                if split_found:
                    left_cell = context.grid.item_to_cell[split].parent.row[x]
                    # set path to split unpackable
                    c_cell = left_cell
                    while c_cell.content is not split:
                        c_cell.packable = False
                        c_cell = c_cell.prev_cell
                else:
                    if y_cnt == 0:
                        left_cell = context.grid.first_row.above().row[x]
                    else:
                        left_cell = context.grid.rows[y_acc / y_cnt].row[x]
                if new_cell is not None and new_cell.content is element:
                    new_cell.remove_content(pack=True)
                new_cell = left_cell.after()

                # set all incoming pathes unpackable
                for prevelem in element.inset:
                    target = context.grid.item_to_cell.get(prevelem)
                    if target is None:
                        # dont set unpackable in other grids (other edge layout)
                        continue
                    start  = target.parent.row[x+1]
                    c_cell = start
                    while c_cell is not target:
                        c_cell.packable = False
                        c_cell = c_cell.prev_cell
            # if not prelayouted
            elif new_cell is None:
                pre_elem = element.inset[0]
                left_cell = context.grid.item_to_cell.get(pre_elem)
                if left_cell is None:
                    pre_grid = self.parent2context[pre_elem.parent].grid
                    pre_cell = pre_grid.item_to_cell.get(pre_elem)
                    if pre_cell is None:
                        raise RuntimeError("Cannot find Cell for element")
                    grids = self.supergrid.grids
                    new_row = None
                    if grids.index(pre_grid) < grids.index(context.grid):
                        new_row = context.grid.add_first_row()
                    else:
                        new_row = context.grid.add_last_row()
                    left_cell = new_row.row[max(0, pre_cell.parent.find(pre_cell))]
                new_cell = left_cell.after()
            if new_cell.content is not None and new_cell.content is not element:
                new_cell.parent.insert_row_beneath()
                new_cell = new_cell.beneath()
            new_cell.set_content(element)
        return new_cell

    def _prepare_lanes(self, process):
        # creates a grid for the process and another each lane of the process
        processgrid = Grid()
        gridcontext = self.GridContext(processgrid)
        self.supergrid.add(processgrid)
        self.parent2context[process] = gridcontext

        for pool in process.pools:
            for lane in pool.lanes:
                lanegrid = Grid()
                gridcontext = self.GridContext(lanegrid)
                self.supergrid.add(lanegrid)
                self.parent2context[lane] = gridcontext

    def _prev_split(self, node):
        # returns a pair (split, dist) where split is the closest split of node
        # found (searching backwards) and dist is the distance to that split
        if is_split(node):
            return node, 0
        prevsplits = []
        for prevnode in node.inset:
            prevsplits.append(self._prev_split(prevnode))
        get_closer_split = lambda (node1, dist1), (node2, dist2): (node1, dist1+1) if dist1 < dist2 else (node2, dist2+1)
        return reduce(get_closer_split, prevsplits, (None, maxint))

    def _back_distance(self, src, target):
        # return the minimum distance from src node to target node, where the
        # target node is going backwards from the source node
        if src == target:
            return 0
        min_dist = maxint
        for prev in src.inset:
            dist = self._back_distance(prev, target)
            min_dist = min(dist, min_dist)
        return min_dist


class SuperGrid:
    def __init__(self):
        self.grids = []
        self.width = 1

    def add(self, grid):
        if grid.parent is not None:
            grid.parent.remove(grid)
        grid.parent = self
        self.grids.append(grid)
        self.width = max(self.width, grid.width)
        for grid in self.grids:
            while grid.width < self.width:
                grid.insert_column_after(grid.width-1)

    def remove(self, grid):
        if grid in self.grids:
            self.grids.remove(grid)

    def insert_column_before(self, col, width):
        if width > self.width:
            self.width += 1
            for grid in self.grids:
                while grid.width < self.width:
                    grid.insert_column_before(col)

    def item_to_cell(self, item):
        for grid in self.grids:
            cell = grid.item_to_cell.get(item)
            if cell is not None:
                return cell
        return None

    def pack(self):
        for grid in self.grids:
            grid.pack()

    def set_geometry(self, padding=10):
        """Calculate the geometry of the BPMN elements.
        margin specifies the space left outside the grid
        padding specifies the space left between cells
        """
        class Geometry:
            def __init__(self, x, y, width, height):
                self.x = x
                self.y = y
                self.width  = width
                self.height = height

        self.total_width  = 0
        self.total_height = 0
        self.geometry = {}  # stores the geometry bounds of cells and grids
        self.colwidth = [0]*self.width
        for grid in self.grids:
            grid.set_geometry(padding)
            for col in range(self.width):
                self.colwidth[col] = max(self.colwidth[col], grid.colwidth[col])
        x = 0
        y = 0
        gridwidth = sum(self.colwidth)
        for grid in self.grids:
            grid.colwidth = self.colwidth
            gridheight = sum(grid.rowheight)
            self.geometry[grid] = Geometry(x, y, gridwidth, gridheight)
            for row in range(grid.height):
                for col in range(self.width):
                    cell = grid.get(col, row)
                    if cell.content is not None:
                        cell_center_x = x + self.colwidth[col]  // 2
                        cell_center_y = y + grid.rowheight[row] // 2
                        cell_x = cell_center_x - cell.content.width  // 2
                        cell_y = cell_center_y - cell.content.height // 2
                        self.geometry[cell] = Geometry(cell_x, cell_y, cell.content.width, cell.content.height)
                    x += self.colwidth[col]
                y += grid.rowheight[row]
                self.total_width = max(self.total_width, x)
                x = 0
        self.total_height = y


class Grid:
    def __init__(self):
        self.parent = None
        self.width  = 1
        self.height = 1
        self.item_to_cell = {}
        self.first_row = Row(self, None, None)
        self.last_row  = self.first_row
        self.rows = [self.first_row]

    def insert_column_before(self, col):
        for row in self.rows:
            row._insert_cell_before(col)
        self.width += 1
        if self.parent is not None:
            self.parent.insert_column_before(col, self.width)

    def insert_column_after(self, col):
        self.insert_column_before(col+1)

    def insert_row_above(self, row):
        if isinstance(row, Row):
            pos = self.__find_pos(row)
        elif isinstance(row, (int, long)):
            pos = row
        prevrow = None if pos == 0              else self.rows[pos-1]
        nextrow = None if pos == len(self.rows) else self.rows[pos]
        newrow  = Row(self, prevrow, nextrow)
        if prevrow is not None:
            prevrow.next_row = newrow
        if nextrow is not None:
            nextrow.prev_row = newrow
        self.rows.insert(pos, newrow)
        self.height += 1
        self.first_row = self.rows[0]
        self.last_row  = self.rows[-1]

    def insert_row_beneath(self, row):
        if isinstance(row, Row):
            pos = self.__find_pos(row)
        elif isinstance(row, (int, long)):
            pos = row
        self.insert_row_above(pos+1)

    def add_last_row(self):
        self.insert_row_beneath(self.last_row)
        return self.last_row

    def add_first_row(self):
        self.insert_row_above(0)
        return self.first_row

    def find(self, cell):
        if cell is None:
            return None
        row = cell.parent
        rowpos = self.__find_pos(cell.parent)
        for i in range(self.width):
            if row.row[i] is cell:
                return i, rowpos
        return None

    def __find_pos(self, row):
        for i in range(len(self.rows)):
            if self.rows[i] is row:
                return i

    def pack(self):
        changed = True  # starts at true to do at least 1 iteration
        while changed:
            changed = False
            for row in self.rows:
                changed = changed or row.try_interleave_with(row.next_row)
            for row in self.rows:
                changed = changed or row.try_interleave_with(row.prev_row)

    def get(self, x, y):
        """Returns the cell located in (x,y) where x is the column (horizontal position)
        and the y is the row (vertical position)."""
        return self.rows[y].row[x]

    def set_geometry(self, margin=0, padding=10):
        self.colwidth  = [0]*self.width
        self.rowheight = [0]*self.height
        # calculation of the rowheight and colwidth lists
        for row in range(self.height):
            cellheight = [0]
            for col in range(self.width):
                cell = self.get(col, row)
                if cell.content is not None:
                    cellheight.append(cell.content.height+padding*2)
                    self.colwidth[col] = max(self.colwidth[col], cell.content.width+padding*2)
            self.rowheight[row] = max(cellheight)

    def reset_geometry(self, relayoutEdges=True, margin=None, padding=None):
        margin  = self.margin if margin is None else margin
        padding = self.padding if padding is None else padding
        self._set_geometry(margin, padding)
        if relayoutEdges:
            elements = self.item_to_cell.keys()
            for elem in elements:
                for outelem in elem.outset:
                    Edge_Layouter(self, (elem, outelem))

    def add_edge(self, edge, layout):
        self.edge_layout[edge] = layout


class Row:
    def __init__(self, parent, prevrow, nextrow):
        self.parent   = parent
        self.prev_row = prevrow
        self.next_row = nextrow
        self.__init_row()
        self.first_cell = self.row[0]
        self.last_cell  = self.row[-1]

    def __init_row(self):
        self.row = []
        for i in range(self.parent.width):
            prevcell = None if i == 0 else self.row[i-1]
            newcell  = Cell(self, prevcell)
            self.row.append(newcell)
        for i in range(self.parent.width-1):
            self.row[i].next_cell = self.row[i+1]

    def find(self, cell):
        i = 0
        for rcell in self.row:
            if rcell is cell:
                return i
            i += 1
        return -1

    def insert_row_above(self):
        self.parent.insert_row_above(self)

    def insert_row_beneath(self):
        self.parent.insert_row_beneath(self)

    def _insert_cell_before(self, col):
        prevcell = None if col == 0             else self.row[col-1]
        nextcell = None if col == len(self.row) else self.row[col]
        cell = Cell(self, prevcell, nextcell)
        self.row.insert(col, cell)
        if prevcell is not None:
            prevcell.next_cell = cell
        if nextcell is not None:
            nextcell.prev_cell = cell
        self.first_cell = self.row[0]
        self.last_cell  = self.row[-1]

    def _insert_cell_after(self, col):
        self._insert_cell_before(col+1)

    def above(self):
        if self.prev_row is None:
            self.insert_row_above()
        return self.prev_row

    def beneath(self):
        if self.next_row is None:
            self.insert_row_beneath()
        return self.next_row

    def can_interleave(self, row):
        if row is None or row is self:
            return False
        if row is not self.next_row and row is not self.prev_row:
            return False
        for i in range(len(self.row)):
            if not self.row[i].packable and not row.row[i].packable:
                return False
        return True

    def try_interleave_with(self, row):
        if not self.can_interleave(row):
            return False
        for i in range(len(self.row)):
            self_cell  = self.row[i]
            other_cell = row.row[i]
            if not other_cell.packable:
                self_cell.packable = False
            if other_cell.content is not None:
                content = other_cell.content
                other_cell.remove_content()
                self_cell.set_content(content)
        if row is self.prev_row:
            self.prev_row = row.prev_row
            if self.prev_row is not None:
                self.prev_row.next_row = self
        elif row is self.next_row:
            self.next_row = row.next_row
            if self.next_row is not None:
                self.next_row.prev_row = self
        self.parent.rows.remove(row)
        self.parent.height -= 1
        return True


class Cell:
    def __init__(self, parent, prevcell=None, nextcell=None):
        self.parent = parent
        self.prev_cell = prevcell
        self.next_cell = nextcell
        self.content   = None
        self.packable  = True  # packable is used for interleaving rows. Two cells
                               # can be interleaved if one of them is packable

    def set_content(self, content):
        grid = self.parent.parent
        duplicated_content = grid.item_to_cell.get(content)
        if duplicated_content is not None:
            duplicated_content.remove_content(True)
        grid.item_to_cell[content] = self
        self.content  = content
        self.packable = False

    def remove_content(self, pack=False):
        grid = self.parent.parent
        grid.item_to_cell.pop(self.content, None)
        self.content = None
        if pack:
            self.packable = True

    def beneath(self):
        row = self.parent
        beneath_row = row.beneath()
        for i in range(len(row.row)):
            if row.row[i] is self:
                return beneath_row.row[i]

    def above(self):
        row = self.parent
        above_row = row.above()
        for i in range(len(row.row)):
            if row.row[i] is self:
                return above_row.row[i]

    def after(self):
        if self.next_cell is None:
            grid = self.parent.parent
            grid.insert_column_after(grid.width-1)
        return self.next_cell

    def before(self):
        if self.prev_cell is None:
            grid = self.parent.parent
            grid.insert_column_before(0)
        return self.prev_cell

    def _set_center(self, x, y):
        self.center = (x, y)

    def _set_grid_pos(self, col, row):
        self.col = col
        self.row = row


class TopologicalSorter:
    class _Node:
        def __init__(self, src_node):
            self.original_element = src_node
            self.inset  = list(src_node.inset)
            self.outset = list(src_node.outset)
            self.starting_inset_count  = len(self.inset)
            self.starting_outset_count = len(self.outset)

    def __init__(self, process):
        #self.src_process = process
        #self.process = copy.deepcopy(process)
        self.process = process
        self._save_edges()

    def _save_edges(self):
        self.outedges = {}
        self.inedges  = {}
        for elem in self.process.elements:
            self.outedges[elem] = list(elem.outset)
            self.inedges[elem]  = list(elem.inset)

    def _create_diagram(self):
        self.diagram = []
        for elem in self.process.elements:
            node = self._Node(elem)
            self.diagram.append(node)

    def _get_elem(self, original_element):
        for node in self.diagram:
            if node.original_element is original_element:
                return node

    def get_sorted_elements(self):
        # First step to find loops and backpatch backwards edges
        self._do_sorting(True)
        # Second step to get the real sorting
        self._do_sorting(False)
        return self.sorted_elements

    def restore_edges(self):
        for elem in self.process.elements:
            elem.outset = self.outedges[elem]
            elem.inset  = self.inedges[elem]

    def _do_sorting(self, backpatch):
        self._create_diagram()
        self.sorted_elements = []
        self.elements_to_sort = list(self.diagram)
        self.backward_edges = list()

        self._topological_sort()

        if backpatch:
            self._backpatch_backward_edges()

        # write backwards edges in diagram
        self._reverse_backwards_edges()

    def _get_loop_entry_point(self, G):
        for j in [j for j in G if j.starting_inset_count > 1]:  # for each join
            if len(j.inset) < j.starting_inset_count:
                return j

    def _reverse_edge(self, elem1, elem2, elem1node, elem2node):
        elem1node.outset.remove(elem2)
        elem2node.inset.remove(elem1)
        elem1node.inset.append(elem2)
        elem2node.outset.append(elem1)

    def _topological_sort(self):
        while len(self.elements_to_sort) > 0:
            free_elements = [node for node in self.elements_to_sort if len(node.inset) == 0]
            if len(free_elements) > 0:
                for element in free_elements:
                    self.sorted_elements.append(element.original_element)
                    self.elements_to_sort.remove(element)
                    for outelem in element.outset:
                        nodeelem = self._get_elem(outelem)
                        nodeelem.inset.remove(element.original_element)
                    element.outset = []
            else:  # loop found
                entry = self._get_loop_entry_point(self.elements_to_sort)
                for or_back_elem in entry.inset:
                    back_elem = self._get_elem(or_back_elem)
                    self._reverse_edge(or_back_elem, entry.original_element, back_elem, entry)
                    self.backward_edges.append((or_back_elem, entry.original_element))

    def _backpatch_backward_edges(self):
        new_backward_edges = list(self.backward_edges)
        for edge in self.backward_edges:
            source, target = edge
            while not len(source.inset) > 1 and not len(source.outset) > 1:
                # should have exactly one predecessor, because its a path back
                new_source = source.inset[0]
                target = new_source
                new_backward_edges.append((target, source))
                source = target
        self.backward_edges = new_backward_edges

    def _reverse_backwards_edges(self):
        for edge in self.backward_edges:
            source, target = edge
            source.outset.remove(target)
            target.inset.remove(source)
            source.inset.append(target)
            target.outset.append(source)

    def topological_sort(self):
        nodes = self.diagram
        G = set(nodes)  # Set of nodes to sort
        L = []          # Empty list for the sorted elem
        #S = set()      # Empty Set for nodes with no incoming edges
        B = set()       # Set of backwards edges
        while len(G) > 0:
            S = [node for node in G if len(node.inset) == 0]
            if len(S) > 0:
                # ordinary top-sort
                node = S.pop()
                G.remove(node)
                L.append(node.original_element)
                # m = nodes with an edge from node to m
                for m in [m for m in nodes if m.original_element in node.outset]:
                    node.outset.remove(m.original_element)
                    m.inset.remove(node.original_element)
            else:  # cycle found
                J = self.__get_loop_entry_point(G)
                for or_elem in J.inset:
                    elem = self._get_elem(or_elem)
                    elem.outset.remove(J.original_element)
                    J.inset.remove(or_elem)

                    elem.inset.append(J.original_element)
                    J.outset.append(or_elem)

                    backedge = (elem.original_element, J.original_element)
                    B.add(backedge)
        return L, B


class Edge_Layouter:
    class Node:
        def __init__(self, elem, width, height, cx, cy):
            self.dist    = maxint
            self.hblock  = False if elem is None else True
            self.vblock  = False if elem is None else True
            self.element = elem
            self.width   = width
            self.height  = height
            self.cx      = cx  # cx, cy = center of the node
            self.cy      = cy

        def blocked(self):
            return self.hblock and self.vblock

    def __init__(self, bpmn, supergrid):
        self.bpmn = bpmn
        self.supergrid = supergrid
        self.edges = {}
        self._create_lee_table()
        self._create_table2()
        for process in self.bpmn.processes:
            self._layout_process_edges(process)

    def _create_lee_table(self):
        self.table1 = []
        self.position = {}
        x = y = 0
        sumy  = 0
        for grid in self.supergrid.grids:
            rownum = 0
            for row in grid.rows:
                tablerow = []
                sumx = 0
                cellheight = grid.rowheight[rownum]
                for cell in row.row:
                    cellwidth = grid.colwidth[x]
                    cx = sumx + cellwidth  // 2
                    cy = sumy + cellheight // 2
                    cellnode = self.Node(cell.content, cellwidth, cellheight, cx, cy)
                    tablerow.append(cellnode)
                    if cell.content is not None:
                        self.position[cell.content] = (x, y)
                    x += 1
                    sumx += cellwidth
                self.table1.append(tablerow)
                x = 0
                y += 1
                sumy   += cellheight
                rownum += 1

    def _create_table2(self):
        self.table2 = []
        for row in self.table1:
            tablerow1 = []
            tablerow2 = []
            for node in row:
                content    = node.element
                nodewidth  = node.width
                nodeheight = node.height
                lcx = node.cx - nodewidth  // 4
                rcx = node.cx + nodewidth  // 4
                ucy = node.cy - nodeheight // 4
                dcy = node.cy + nodeheight // 4
                node1 = self.Node(content, nodewidth//2, nodeheight//2, lcx, ucy)
                node2 = self.Node(content, nodewidth//2, nodeheight//2, rcx, ucy)
                node3 = self.Node(content, nodewidth//2, nodeheight//2, lcx, dcy)
                node4 = self.Node(content, nodewidth//2, nodeheight//2, rcx, dcy)
                tablerow1.append(node1)
                tablerow1.append(node2)
                tablerow2.append(node3)
                tablerow2.append(node4)
            self.table2.append(tablerow1)
            self.table2.append(tablerow2)

    def _clear_tables(self):
        self._clear_table(self.table1)
        self._clear_table(self.table2)

    def _clear_table(self, table):
        if table is not None:
            for row in table:
                for node in row:
                    node.dist = maxint

    def _store_and_block_path(self, path, src_elem, tgt_elem, table):
        # path is a list of pairs with the positions (x, y) of the nodes in the path
        self._store_path(path, src_elem, tgt_elem, table)
        self._block_path(path, table)

    def _store_path(self, path, src_elem, tgt_elem, table):
        x, y = self._get_nearest(src_elem, path[0], path[1], table)
        edge_layout = [x, y]
        pdir = self._get_dir(path[0], path[1])
        for i in range(1, len(path)-1):
            new_dir = self._get_dir(path[i], path[i+1])
            if pdir != new_dir:
                x, y = path[i]
                edge_layout.extend([table[y][x].cx, table[y][x].cy])
                pdir = new_dir

        x, y = self._get_nearest(tgt_elem, path[-1], path[-2], table)
        edge_layout.extend([x, y])

        self.edges[(src_elem, tgt_elem)] = edge_layout

    def _get_nearest(self, elem, elem_pos, next_pos, table):
        if table is self.table1:
            elem_cell = self.supergrid.item_to_cell(elem)
            elem_geom = self.supergrid.geometry[elem_cell]

            pdir = self._get_dir(elem_pos, next_pos)
            if pdir == "right":
                x = elem_geom.x + elem_geom.width        # x right
                y = elem_geom.y + elem_geom.height // 2  # y center
            elif pdir == "left":
                x = elem_geom.x                          # x left
                y = elem_geom.y + elem_geom.height // 2  # y center
            elif pdir == "up":
                x = elem_geom.x + elem_geom.width  // 2  # x center
                y = elem_geom.y                          # y up
            elif pdir == "down":
                x = elem_geom.x + elem_geom.width  // 2  # x center
                y = elem_geom.y + elem_geom.height       # y down
            return x, y

        elif table is self.table2:
            tx, ty = elem_pos
            x, y   = table[ty][tx].cx, table[ty][tx].cy
            return x, y

    def _get_dir(self, src_pos, tgt_pos):
        src_x, src_y = src_pos
        tgt_x, tgt_y = tgt_pos
        if src_x < tgt_x:
            return "right"
        elif src_x > tgt_x:
            return "left"
        elif src_y < tgt_y:
            return "down"
        else:
            return "up"

    def _block_path(self, path, table):
        for i in range(1, len(path)-1):
            x, y = path[i]
            prev_dir = self._get_dir(path[i-1], path[i])
            if prev_dir == "right" or prev_dir == "left":
                table[y][x].hblock = True
            if prev_dir == "up" or prev_dir == "down":
                table[y][x].vblock = True
            next_dir = self._get_dir(path[i], path[i+1])
            if next_dir == "right" or next_dir == "left":
                table[y][x].hblock = True
            if next_dir == "up" or next_dir == "down":
                table[y][x].vblock = True

    def _layout_process_edges(self, process):
        for element in process.elements:
            if is_split(element):
                self._layout_group(element, element.outset)
            if is_join(element):
                self._layout_group_j(element, element.inset)
        for element in process.elements:
            if not is_split(element) and len(element.outset) > 0:
                if self.edges.get((element, element.outset[0])) is None:
                    path, tab_num = self._layout_edge(element, element.outset[0], self.table1)
                    if tab_num == 2 and path is not None:
                        self._store_and_block_path(path, element, element.outset[0], self.table2)
                    elif path is not None:
                        self._store_and_block_path(path, element, element.outset[0], self.table1)
                    else:
                        self._direct_edge(element, element.outset[0])
                    self._clear_tables()
            if not is_join(element) and len(element.inset) > 0:
                if self.edges.get((element.inset[0], element)) is None:
                    path, tab_num = self._layout_edge(element.inset[0], element, self.table1)
                    if tab_num == 2 and path is not None:
                        self._store_and_block_path(path, element.inset[0], element, self.table2)
                    elif path is not None:
                        self._store_and_block_path(path, element.inset[0], element, self.table1)
                    else:
                        self._direct_edge(element.inset[0], element)
                    self._clear_tables()

    def _direct_edge(self, src_elem, tgt_elem):
        src_cell = self.supergrid.item_to_cell(src_elem)
        tgt_cell = self.supergrid.item_to_cell(tgt_elem)

        src_center_x = self.supergrid.geometry[src_cell].x + self.supergrid.geometry[src_cell].width  // 2
        src_center_y = self.supergrid.geometry[src_cell].y + self.supergrid.geometry[src_cell].height // 2
        tgt_center_x = self.supergrid.geometry[tgt_cell].x + self.supergrid.geometry[tgt_cell].width  // 2
        tgt_center_y = self.supergrid.geometry[tgt_cell].y + self.supergrid.geometry[tgt_cell].height // 2

        if src_center_x < tgt_center_x:
            src_x = src_center_x + src_elem.width // 2
            src_y = src_center_y
        else:
            src_x = src_center_x - src_elem.width // 2
            src_y = src_center_y

        if src_center_y < tgt_center_y:
            tgt_x = tgt_center_x - tgt_elem.width // 2
            tgt_y = tgt_center_y
        else:
            tgt_x = tgt_center_x + tgt_elem.width // 2
            tgt_y = tgt_center_y

        edge_layout = [src_x, src_y, tgt_x, tgt_y]
        self.edges[(src_elem, tgt_elem)] = edge_layout

    def _layout_group(self, src_elem, tgt_list):
        # layout a group of edges splitting from one element
        path_list1 = []
        path_list2 = []
        for tgt_elem in tgt_list:
            if self.edges.get((src_elem, tgt_elem)) is None:
                edge_path, tab_num = self._layout_edge(src_elem, tgt_elem, self.table1)
                if tab_num == 2 and edge_path is not None:
                    self._store_path(edge_path, src_elem, tgt_elem, self.table2)
                    path_list2.append(edge_path)
                elif edge_path is not None:
                    self._store_path(edge_path, src_elem, tgt_elem, self.table1)
                    path_list1.append(edge_path)
                else:
                    self._direct_edge(src_elem, tgt_elem)
                self._clear_tables()
        for path in path_list1:
            self._block_path(path, self.table1)
        for path in path_list2:
            self._block_path(path, self.table2)

    def _layout_group_j(self, tgt_elem, src_list):
        # layout a group of edges joining in one element
        path_list1 = []
        path_list2 = []
        for src_elem in src_list:
            if self.edges.get((src_elem, tgt_elem)) is None:
                edge_path, tab_num = self._layout_edge(src_elem, tgt_elem, self.table1)
                if tab_num == 2 and edge_path is not None:
                    self._store_path(edge_path, src_elem, tgt_elem, self.table2)
                    path_list2.append(edge_path)
                elif edge_path is not None:
                    self._store_path(edge_path, src_elem, tgt_elem, self.table1)
                    path_list1.append(edge_path)
                else:
                    self._direct_edge(src_elem, tgt_elem)
                self._clear_tables()
        for path in path_list1:
            self._block_path(path, self.table1)
        for path in path_list2:
            self._block_path(path, self.table2)

    def _layout_edge(self, src_elem, tgt_elem, table):
        # returns the path from src_elem to tgt_elem. the distances in the table
        # are modified, but the nodes are not blocked
        x, y = self.position[src_elem]
        node_list = set()

        if table is self.table1:
            table[y][x].dist = 0
            node_list.add((x, y))

        elif table is self.table2:
            table[y*2][x*2].dist     = 0
            table[y*2][x*2+1].dist   = 0
            table[y*2+1][x*2].dist   = 0
            table[y*2+1][x*2+1].dist = 0
            node_list.add((x*2,   y*2))
            node_list.add((x*2,   y*2+1))
            node_list.add((x*2+1, y*2))
            node_list.add((x*2+1, y*2+1))

        while len(node_list) > 0:
            x, y  = node_list.pop()
            right = (x+1, y)
            left  = (x-1, y)
            up    = (x, y-1)
            down  = (x, y+1)
            if self._valid_pos(right, table, tgt_elem) and table[y][x+1].dist > table[y][x].dist:
                node_list.add(right)
                table[y][x+1].dist = table[y][x].dist + 1
            if self._valid_pos(left, table, tgt_elem) and table[y][x-1].dist > table[y][x].dist:
                node_list.add(left)
                table[y][x-1].dist = table[y][x].dist + 1
            if self._valid_pos(up, table, tgt_elem) and table[y-1][x].dist > table[y][x].dist:
                node_list.add(up)
                table[y-1][x].dist = table[y][x].dist + 1
            if self._valid_pos(down, table, tgt_elem) and table[y+1][x].dist > table[y][x].dist:
                node_list.add(down)
                table[y+1][x].dist = table[y][x].dist + 1

        x, y = self.position[tgt_elem]
        if table is self.table1:
            if table[y][x].dist < maxint:
                path, corns = self._redo_path(self.position[tgt_elem], table)
                if path is None:
                    return self._layout_edge(src_elem, tgt_elem, self.table2)
                path.reverse()
                return path, 1
            else:
                return self._layout_edge(src_elem, tgt_elem, self.table2)

        elif table is self.table2:
            positions = [(x*2, y*2), (x*2, y*2+1), (x*2+1, y*2), (x*2+1, y*2+1)]
            positions.sort(key=lambda pair: table[pair[1]][pair[0]].dist)
            better_path = None
            better_corn = maxint
            for pos in positions:
                if table[pos[1]][pos[0]].dist < maxint:
                    path, corns = self._redo_path(pos, table)
                    if corns is not None and corns < better_corn:
                        better_corn = corns
                        better_path = path
            if better_path is not None:
                better_path.reverse()
                return better_path, 2
            else:
                return None, None

    def _redo_path(self, pos, table, start_dir="none", path=None):
        x, y = pos
        if path is None:
            path = [pos]
        else:
            path = list(path)
            path.append(pos)

        if table[y][x].dist == 0:
            if start_dir == "right" or start_dir == "left":
                return path, 0
            # penalize non-gateways elements being connected vertically
            return path, 1 if not is_join(table[y][x].element) and not is_split(table[y][x].element) else 0
        if (start_dir == "right" or start_dir == "left") and table[y][x].hblock:
            return None, 0
        if (start_dir == "up" or start_dir == "down") and table[y][x].vblock:
            return None, 0

        found_paths = []
        if self._valid_pos((x+1, y), table, blocks=False):
            if table[y][x+1].dist < table[y][x].dist:
                found_path, num_corners = self._redo_path((x+1, y), table, "right", path)
                if num_corners is not None and start_dir != "right":
                    num_corners += 1
                if found_path is not None:
                    found_paths.append((found_path, num_corners))
        if self._valid_pos((x-1, y), table, blocks=False):
            if table[y][x-1].dist < table[y][x].dist:
                found_path, num_corners = self._redo_path((x-1, y), table, "left", path)
                if num_corners is not None and start_dir != "left":
                    num_corners += 1
                if found_path is not None:
                    found_paths.append((found_path, num_corners))
        if self._valid_pos((x, y-1), table, blocks=False):
            if table[y-1][x].dist < table[y][x].dist:
                found_path, num_corners = self._redo_path((x, y-1), table, "up", path)
                if num_corners is not None and start_dir != "up":
                    num_corners += 1
                # penalize non-gateways elements being connected vertically
                if num_corners is not None and start_dir == "none":
                    if not is_join(table[y][x].element) and not is_split(table[y][x].element):
                        num_corners += 1
                if found_path is not None:
                    found_paths.append((found_path, num_corners))
        if self._valid_pos((x, y+1), table, blocks=False):
            if table[y+1][x].dist < table[y][x].dist:
                found_path, num_corners = self._redo_path((x, y+1), table, "down", path)
                if num_corners is not None and start_dir != "down":
                    num_corners += 1
                # penalize non-gateways elements being connected vertically
                if num_corners is not None and start_dir == "none":
                    if not is_join(table[y][x].element) and not is_split(table[y][x].element):
                        num_corners += 1
                if found_path is not None:
                    found_paths.append((found_path, num_corners))

        found_paths.sort(key=lambda split: split[1])
        if len(found_paths) > 0:
            return found_paths[0]
        else:
            return None, None

    def _valid_pos(self, pos, table, tgt_elem=None, blocks=True):
        # blocks=False when you don't count if the node is blocked for being a valid position
        x, y = pos
        if 0 <= y < len(table) and 0 <= x < len(table[0]):
            if tgt_elem is not None and table[y][x].element is tgt_elem:
                return True
            if not blocks:
                return True
            elif not table[y][x].blocked():
                return True
        return False
