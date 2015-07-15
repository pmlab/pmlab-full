from .. __bpmn import *
import unittest

class Test_Process(unittest.TestCase):
    def setUp(self):
        self.bpmn = BPMN()
        self.process = self.bpmn.new_process()
    
    def test_start_and_end_events_created(self):
        """Test if a start event and a end event are created for the process when is created"""
        self.assertNotEqual(None, self.process.start_event)
        self.assertNotEqual(None, self.process.end_event)
        self.assertTrue(self.process.start_event in self.process.elements)
        self.assertTrue(self.process.end_event in self.process.elements)
    
    def test_add_element(self):
        """Test if the element is added to the process"""
        elem = Activity("element_name")
        num_elements = len(self.process.elements)
        self.process.add_element(elem)
        new_num_elements = len(self.process.elements)
        self.assertTrue(elem in self.process.elements)
        self.assertEqual(num_elements + 1, new_num_elements)
        self.assertEqual(elem.parent, self.process)
        self.assertEqual(elem.process, self.process)

    def test_add_element_twice(self):
        """Test that adding an element twice does not duplicate the object"""
        elem = Activity("task")
        self.process.add_element(elem)
        elem_count = len(self.process.elements)
        self.process.add_element(elem)
        new_elem_count = len(self.process.elements)
        self.assertEqual(elem_count, new_elem_count)
        self.assertEqual(self.process.elements.count(elem), 1)

    def test_del_element(self):
        """Test if the element is deleted from the process"""
        elem = Activity("element_name")
        self.process.add_element(elem)
        num_elements = len(self.process.elements)
        self.process.del_element(elem)
        new_num_elements = len(self.process.elements)
        self.assertTrue(elem not in self.process.elements)
        self.assertEqual(num_elements - 1, new_num_elements)
        self.assertEqual(elem.parent, None)

    def test_add_connection(self):
        """Test if a connection can be created between two elements of the process"""
        elem1 = Activity("task1")
        elem2 = Activity("task2")
        self.process.add_element(elem1)
        self.process.add_element(elem2)
        self.process.add_connection(elem1, elem2)
        self.assertEqual(elem1.outset[0], elem2)
        self.assertEqual(elem2.inset[0], elem1)

    def test_add_connection_to_list(self):
        """Test if a connection can be created between an element and a list of elements"""
        elem1 = Activity("task1")
        elem2 = Activity("task1")
        self.process.add_element(elem1)
        self.process.add_element(elem2)
        self.process.add_connection(self.process.start_event, [elem1, elem2])
        self.assertTrue(elem1 in self.process.start_event.outset)
        self.assertTrue(elem2 in self.process.start_event.outset)
        self.assertEqual(self.process.start_event, elem1.inset[0])
        self.assertEqual(self.process.start_event, elem2.inset[0])

    def test_add_connection_from_list(self):
        """Test if a connection can be created between a list of elements and an element"""
        elem1 = Activity("task1")
        elem2 = Activity("task1")
        self.process.add_element(elem1)
        self.process.add_element(elem2)
        self.process.add_connection([elem1, elem2], self.process.end_event)
        self.assertTrue(elem1 in self.process.end_event.inset)
        self.assertTrue(elem2 in self.process.end_event.inset)
        self.assertEqual(self.process.end_event, elem1.outset[0])
        self.assertEqual(self.process.end_event, elem2.outset[0])

    def test_elements_must_be_on_process_to_add_connection(self):
        """Test if a connection fails to be added when the elements doesn't belong to the same proceess"""
        elem1 = Activity("task1")
        elem2 = Activity("task2")
        self.process.add_element(elem1)
        self.process.add_connection(elem1, elem2)
        self.assertTrue(elem1 not in elem2.inset)
        self.assertTrue(elem2 not in elem1.outset)

    def test_add_connection_twice(self):
        """Test that a connection doesn't duplicate when it's added two times"""
        elem1 = Activity("task1")
        elem2 = Activity("task2")
        self.process.add_element(elem1)
        self.process.add_element(elem2)
        self.process.add_connection(elem1, elem2)
        num_elem = len(elem1.outset)
        self.process.add_connection(elem1, elem2)
        new_num_elem = len(elem1.outset)
        self.assertEqual(num_elem, new_num_elem)

    def test_add_element_which_belongs_to_another_process(self):
        """Test if adding an element to a process when belongs to another process deletes its connections"""
        elem1 = Activity("task1")
        elem2 = Activity("task2")
        self.process.add_element(elem1)
        self.process.add_element(elem2)
        self.process.add_connection(elem1, elem2)
        process2 = self.bpmn.new_process()
        process2.add_element(elem1)
        self.assertEqual(elem1.parent, process2)
        self.assertTrue(elem1 in process2.elements)
        self.assertTrue(elem1 not in self.process.elements)
        self.assertTrue(elem1 not in elem2.inset)
        self.assertTrue(elem2 not in elem1.outset)

    def test_del_connection(self):
        """Test if a connection between two elements of the process can be deleted"""
        elem1 = Activity("task1")
        elem2 = Activity("task2")
        self.process.add_element(elem1)
        self.process.add_element(elem2)
        self.process.add_connection(elem1, elem2)
        self.process.del_connection(elem1, elem2)
        self.assertTrue(elem1 not in elem2.inset)
        self.assertTrue(elem2 not in elem1.outset)

    def test_del_connection_to_list(self):
        """Test if a connection between an element and a list of elements can be deleted"""
        elem1 = Activity("task1")
        elem2 = Activity("task1")
        self.process.add_element(elem1)
        self.process.add_element(elem2)
        self.process.add_connection(self.process.start_event, [elem1, elem2])
        self.process.del_connection(self.process.start_event, [elem1, elem2])
        self.assertTrue(elem1 not in self.process.start_event.outset)
        self.assertTrue(elem2 not in self.process.start_event.outset)
        self.assertTrue(self.process.start_event not in elem1.inset)
        self.assertTrue(self.process.start_event not in elem2.inset)

    def test_del_connection_from_list(self):
        """Test if a connection between a list of elements and an element can be deleted"""
        elem1 = Activity("task1")
        elem2 = Activity("task1")
        self.process.add_element(elem1)
        self.process.add_element(elem2)
        self.process.add_connection([elem1, elem2], self.process.end_event)
        self.process.del_connection([elem1, elem2], self.process.end_event)
        self.assertTrue(elem1 not in self.process.end_event.inset)
        self.assertTrue(elem2 not in self.process.end_event.inset)
        self.assertTrue(self.process.end_event not in elem1.outset)
        self.assertTrue(self.process.end_event not in elem2.outset)

    def test_get_events(self):
        """Test if the get_gateways method returns the events"""
        ev = Event("start", "ev_name")
        num_ev = len(self.process.get_events())
        self.process.add_element(ev)
        new_num_ev = len(self.process.get_events())
        self.assertEqual(num_ev + 1, new_num_ev)
        self.assertTrue(ev in self.process.get_events())

    def test_get_activities(self):
        """Test if the get_gateways method returns the gateways"""
        act = Activity("act_name")
        num_act = len(self.process.get_activities())
        self.process.add_element(act)
        new_num_act = len(self.process.get_activities())
        self.assertEqual(num_act + 1, new_num_act)
        self.assertTrue(act in self.process.get_activities())

    def test_get_gateways(self):
        """Test if the get_gateways method returns the gateways"""
        gw = Gateway("exclusive", "gw_name")
        num_gw = len(self.process.get_gateways())
        self.process.add_element(gw)
        new_num_gw = len(self.process.get_gateways())
        self.assertEqual(num_gw + 1, new_num_gw)
        self.assertTrue(gw in self.process.get_gateways())

    def test_new_pool(self):
        """Test if a pool can be added to a process"""
        num_pools = len(self.process.pools)
        pool = self.process.new_pool()
        new_num_pools = len(self.process.pools)
        self.assertEqual(num_pools + 1, new_num_pools)
        self.assertTrue(pool in self.process.pools)
        self.assertEqual(pool.parent, self.process)
        self.assertEqual(pool.process, self.process)

    def test_del_pool(self):
        """Test if a pool can be deleted from a process"""
        pool = self.process.new_pool()
        num_pools = len(self.process.pools)
        self.process.del_pool(pool)
        new_num_pools = len(self.process.pools)
        self.assertEqual(num_pools - 1, new_num_pools)
        self.assertTrue(pool not in self.process.pools)
        self.assertEqual(pool.parent, None)

    def test_del_pool_does_not_delete_elements(self):
        """Test that deleting a pool does not delete the elements of the pool, and they are reassigned to
        the process"""
        elem = Activity("task")
        pool = self.process.new_pool()
        lane = pool.new_lane()
        lane.add_element(elem)
        num_elems = len(self.process.elements)
        self.process.del_pool(pool)
        new_num_elems = len(self.process.elements)
        self.assertEqual(num_elems, new_num_elems)
        self.assertTrue(elem in self.process.elements)
        self.assertEqual(elem.parent, self.process)
        self.assertEqual(elem.process, self.process)

    def test_del_pool_with_elements(self):
        """Test if del_pool_with_elements deletes the pool and all its elements"""
        elem = Activity("task")
        pool = self.process.new_pool()
        lane = pool.new_lane()
        lane.add_element(elem)
        num_elems = len(self.process.elements)
        self.process.del_pool_with_elements(pool)
        new_num_elems = len(self.process.elements)
        self.assertEqual(num_elems - 1, new_num_elems)
        self.assertTrue(elem not in self.process.elements)
        self.assertEqual(elem.parent, None)
        self.assertEqual(elem.process, None)

    def test_internal_name_to_elem_on_add_element(self):
        """Test if the variable internalname_to_element is correctly updated when adding an element"""
        elem = Activity("task")
        self.process.add_element(elem)
        ret_elem = self.process.internalname_to_elem[elem.internal_name]
        self.assertEqual(elem, ret_elem)
        self.assertTrue(elem.internal_name in self.process.internalname_to_elem)

    def test_internal_name_to_elem_on_del_element(self):
        """Test if the variable internalname_to_element is correctly updated when deleting an element"""
        elem = Activity("task")
        self.process.add_element(elem)
        self.process.del_element(elem)
        ret_elem = self.process.internalname_to_elem.get(elem.internal_name, None)
        self.assertEqual(ret_elem, None)
        self.assertTrue(elem.internal_name not in self.process.internalname_to_elem)
