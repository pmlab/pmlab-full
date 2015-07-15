import unittest
from .. __layouting import *

class Test_Grid_Module(unittest.TestCase):
    class __Content:
        width  = 10
        height = 20

    def setUp(self):
        self.grid = Grid()

    def test_default_grid(self):
        row = self.grid.rows[0]
        self.assertIs(row, self.grid.first_row)
        self.assertIs(row, self.grid.last_row)
        self.assertIsNot(None, row)
        self.assertIsNot(None, self.grid.get(0, 0))
        self.assertEqual(1, self.grid.width)
        self.assertEqual(1, self.grid.height)

    def test_default_row(self):
        cell = self.grid.get(0, 0)
        row = self.grid.rows[0]
        self.assertIs(None, row.prev_row)
        self.assertIs(None, row.next_row)
        self.assertIs(self.grid, row.parent)
        self.assertIs(cell, row.first_cell)
        self.assertIs(cell, row.last_cell)

    def test_default_cell(self):
        cell = self.grid.get(0, 0)
        self.assertIs(None, cell.prev_cell)
        self.assertIs(None, cell.next_cell)
        self.assertIs(None, cell.content)
        self.assertTrue(cell.packable)
        self.assertIs(self.grid.rows[0], cell.parent)

    def test_cell_after_creates_new_column(self):
        first_cell = self.grid.get(0, 0)
        next_cell  = first_cell.after()
        self.assertEqual(2, self.grid.width)
        self.assertEqual(1, self.grid.height)
        self.assertIs(first_cell, next_cell.prev_cell)
        self.assertIs(next_cell, first_cell.next_cell)
        self.assertIs(first_cell, self.grid.get(0, 0))
        self.assertIs(next_cell, self.grid.get(1, 0))

    def test_cell_before_creates_new_column(self):
        first_cell  = self.grid.get(0, 0)
        before_cell = first_cell.before()
        self.assertEqual(2, self.grid.width)
        self.assertEqual(1, self.grid.height)
        self.assertIs(first_cell, before_cell.next_cell)
        self.assertIs(before_cell, first_cell.prev_cell)
        self.assertIs(first_cell, self.grid.get(1, 0))
        self.assertIs(before_cell, self.grid.get(0, 0))

    def test_cell_beneath_creates_new_row(self):
        first_cell   = self.grid.get(0, 0)
        beneath_cell = first_cell.beneath()
        self.assertEqual(1, self.grid.width)
        self.assertEqual(2, self.grid.height)
        self.assertIs(first_cell, self.grid.get(0, 0))
        self.assertIs(beneath_cell, self.grid.get(0, 1))

    def test_cell_above_creates_new_row(self):
        first_cell = self.grid.get(0, 0)
        above_cell = first_cell.above()
        self.assertEqual(1, self.grid.width)
        self.assertEqual(2, self.grid.height)
        self.assertIs(first_cell, self.grid.get(0, 1))
        self.assertIs(above_cell, self.grid.get(0, 0))

    def test_content_is_properly_set(self):
        cell = self.grid.get(0, 0)
        self.assertIs(None, cell.content)
        cell.set_content(1)
        self.assertIs(cell, self.grid.item_to_cell[1])
        self.assertEqual(1, cell.content)
        self.assertFalse(cell.packable)

    def test_content_is_properly_removed(self):
        cell = self.grid.get(0, 0)
        cell.set_content(1)
        cell.remove_content()
        self.assertIs(None, cell.content)
        self.assertIs(None, self.grid.item_to_cell.get(1))

    def test_row_beneath_creates_new_row(self):
        first_row   = self.grid.rows[0]
        beneath_row = first_row.beneath()
        self.assertEqual(1, self.grid.width)
        self.assertEqual(2, self.grid.height)
        self.assertIs(beneath_row, first_row.next_row)
        self.assertIs(first_row, beneath_row.prev_row)
        self.assertIs(first_row, self.grid.rows[0])
        self.assertIs(beneath_row, self.grid.rows[1])

    def test_row_above_creates_new_row(self):
        first_row = self.grid.rows[0]
        above_row = first_row.above()
        self.assertEqual(1, self.grid.width)
        self.assertEqual(2, self.grid.height)
        self.assertIs(above_row, first_row.prev_row)
        self.assertIs(first_row, above_row.next_row)
        self.assertIs(first_row, self.grid.rows[1])
        self.assertIs(above_row, self.grid.rows[0])

    def test_insert_row_beneath(self):
        first_row = self.grid.rows[0]
        first_row.insert_row_beneath()
        self.assertEqual(1, self.grid.width)
        self.assertEqual(2, self.grid.height)
        beneath_row = first_row.beneath()
        self.assertIs(beneath_row, first_row.next_row)
        self.assertIs(first_row, beneath_row.prev_row)
        self.assertIs(first_row, self.grid.rows[0])
        self.assertIs(beneath_row, self.grid.rows[1])

    def test_insert_row_above(self):
        first_row = self.grid.rows[0]
        first_row.insert_row_above()
        self.assertEqual(1, self.grid.width)
        self.assertEqual(2, self.grid.height)
        above_row = first_row.above()
        self.assertIs(above_row, first_row.prev_row)
        self.assertIs(first_row, above_row.next_row)
        self.assertIs(first_row, self.grid.rows[1])
        self.assertIs(above_row, self.grid.rows[0])

    def test_insert_column_before(self):
        cell = self.grid.get(0, 0)
        self.grid.insert_column_before(0)
        self.assertEqual(2, self.grid.width)
        self.assertEqual(1, self.grid.height)
        self.assertIs(cell, self.grid.get(1, 0))
        self.assertIs(cell.prev_cell, self.grid.get(0, 0))

    def test_insert_column_after(self):
        cell = self.grid.get(0, 0)
        self.grid.insert_column_after(0)
        self.assertEqual(2, self.grid.width)
        self.assertEqual(1, self.grid.height)
        self.assertIs(cell, self.grid.get(0, 0))
        self.assertIs(cell.next_cell, self.grid.get(1, 0))

    def test_pack_1(self):
        self.grid.insert_row_above(0)
        self.assertEqual(2, self.grid.height)
        self.grid.pack()
        self.assertEqual(1, self.grid.height)

    def test_pack_2(self):
        self.grid.get(0, 0).set_content(1)
        self.grid.insert_row_above(0)
        self.assertEqual(2, self.grid.height)
        self.grid.pack()
        self.assertEqual(1, self.grid.height)

    def test_pack_3(self):
        cell = self.grid.get(0, 0)
        cell.set_content(1)
        cell.above().set_content(2)
        self.assertEqual(2, self.grid.height)
        self.grid.pack()
        self.assertEqual(2, self.grid.height)

    def test_set_geometry_1(self):
        self.grid.set_geometry(padding=5)
        self.assertEqual(0, self.grid.colwidth[0])
        self.assertEqual(0, self.grid.rowheight[0])

    def test_set_geometry_2(self):
        cell = self.grid.get(0, 0)
        cell.set_content(self.__Content())
        self.grid.set_geometry(padding=5)
        self.assertEqual(20, self.grid.colwidth[0])
        self.assertEqual(30, self.grid.rowheight[0])

    def test_set_geometry_3(self):
        cell = self.grid.get(0,0)
        cell.after()
        cell.set_content(self.__Content())
        self.grid.set_geometry(padding=5)
        self.assertEqual(20, self.grid.colwidth[0])
        self.assertEqual(0, self.grid.colwidth[1])
        self.assertEqual(30, self.grid.rowheight[0])

    def test_set_geometry_4(self):
        cell = self.grid.get(0,0)
        cell.beneath()
        cell.set_content(self.__Content())
        self.grid.set_geometry(padding=5)
        self.assertEqual(20, self.grid.colwidth[0])
        self.assertEqual(30, self.grid.rowheight[0])
        self.assertEqual(0, self.grid.rowheight[1])