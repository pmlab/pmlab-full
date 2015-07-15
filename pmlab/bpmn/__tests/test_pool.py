from .. __bpmn import *
import unittest

class Test_Pool(unittest.TestCase):
    def setUp(self):
        self.bpmn = BPMN()
        self.process = self.bpmn.new_process()
        self.pool = self.process.new_pool()
    
    def test_new_lane(self):
        """Test if a new lane can be created in the pool"""
        num_lanes = len(self.pool.lanes)
        lane = self.pool.new_lane("lane_name")
        new_num_lanes = len(self.pool.lanes)
        self.assertEqual(num_lanes + 1, new_num_lanes)
        self.assertEqual(lane.parent, self.pool)
        self.assertEqual(lane.process, self.process)
        self.assertTrue(lane in self.pool.lanes)

    def test_del_lane(self):
        """Test if a lane can be deleted from the pool"""
        lane = self.pool.new_lane("lane_name")
        num_lanes = len(self.pool.lanes)
        self.pool.del_lane(lane)
        new_num_lanes = len(self.pool.lanes)
        self.assertEqual(num_lanes - 1, new_num_lanes)
        self.assertTrue(lane not in self.pool.lanes)

    def test_del_lane_does_not_delete_elements(self):
        """Test that deleting a lane does not delete the elements of the pool, and they are reassigned to
        the process"""
        elem = Activity("task")
        lane = self.pool.new_lane()
        lane.add_element(elem)
        num_elems = len(self.process.elements)
        self.pool.del_lane(lane)
        new_num_elems = len(self.process.elements)
        self.assertEqual(num_elems, new_num_elems)
        self.assertTrue(elem in self.process.elements)
        self.assertEqual(elem.parent, self.process)
        self.assertEqual(elem.process, self.process)

    def test_del_lane_with_elements(self):
        """Test if del_lane_with_elements deletes the lane and all its elements"""
        elem = Activity("task")
        lane = self.pool.new_lane()
        lane.add_element(elem)
        num_elems = len(self.process.elements)
        self.pool.del_lane_with_elements(lane)
        new_num_elems = len(self.process.elements)
        self.assertEqual(num_elems - 1, new_num_elems)
        self.assertTrue(elem not in self.process.elements)
        self.assertEqual(elem.parent, None)
        self.assertEqual(elem.process, None)
