from .. __bpmn import *
import unittest

class Test_Lane(unittest.TestCase):
    def setUp(self):
        self.bpmn = BPMN()
        self.process = self.bpmn.new_process()
        self.pool = self.process.new_pool()
        self.lane = self.pool.new_lane("lane")

    def test_add_element(self):
        """Test if an element can be added and it still belongs to the process"""
        elem = Activity("task")
        self.lane.add_element(elem)
        self.assertEqual(elem.parent, self.lane)
        self.assertEqual(elem.process, self.process)
        self.assertTrue(elem in self.process.elements)
        self.assertTrue(elem in self.lane.elements)

    def test_add_element_twice(self):
        """Test that adding an element twice does not duplicate the object"""
        elem = Activity("task")
        self.lane.add_element(elem)
        self.lane.add_element(elem)
        self.assertEqual(self.lane.elements.count(elem), 1)
        self.assertEqual(self.process.elements.count(elem), 1)

    def test_del_element(self):
        """Test if an element can be deleted from the lane, and it is also deleted from the process"""
        elem = Activity("task")
        self.lane.add_element(elem)
        self.lane.del_element(elem)
        self.assertNotEqual(elem.parent, self.lane)
        self.assertTrue(elem in self.process.elements)
        self.assertTrue(elem not in self.lane.elements)

    def test_internal_name_to_elem_on_add_element(self):
        """Test if the variable internalname_to_element is correctly updated when adding an element"""
        elem = Activity("task")
        self.lane.add_element(elem)
        ret_elem = self.lane.internalname_to_elem[elem.internal_name]
        self.assertEqual(elem, ret_elem)
        self.assertTrue(elem.internal_name in self.lane.internalname_to_elem)

    def test_internal_name_to_elem_on_del_element(self):
        """Test if the variable internalname_to_element is correctly updated when deleting an element"""
        elem = Activity("task")
        self.lane.add_element(elem)
        self.lane.del_element(elem)
        self.assertTrue(elem.internal_name in self.process.internalname_to_elem)
        self.assertTrue(elem.internal_name not in self.lane.internalname_to_elem)

    def test_get_events(self):
        """Test if the get_gateways method returns the events"""
        ev = Event("start", "ev_name")
        num_ev = len(self.lane.get_events())
        self.lane.add_element(ev)
        new_num_ev = len(self.lane.get_events())
        self.assertEqual(num_ev + 1, new_num_ev)
        self.assertTrue(ev in self.lane.get_events())

    def test_get_activities(self):
        """Test if the get_gateways method returns the gateways"""
        act = Activity("act_name")
        num_act = len(self.lane.get_activities())
        self.lane.add_element(act)
        new_num_act = len(self.lane.get_activities())
        self.assertEqual(num_act + 1, new_num_act)
        self.assertTrue(act in self.lane.get_activities())

    def test_get_gateways(self):
        """Test if the get_gateways method returns the gateways"""
        gw = Gateway("exclusive", "gw_name")
        num_gw = len(self.lane.get_gateways())
        self.lane.add_element(gw)
        new_num_gw = len(self.lane.get_gateways())
        self.assertEqual(num_gw + 1, new_num_gw)
        self.assertTrue(gw in self.lane.get_gateways())
