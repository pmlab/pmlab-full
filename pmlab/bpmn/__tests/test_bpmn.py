from .. __bpmn import *
import unittest

class Test_BPMN(unittest.TestCase):
    def setUp(self):
        self.bpmn = BPMN()

    def test_new_process(self):
        """Test if a new process is created and the process is not None"""
        num_processes = len(self.bpmn.processes)
        proc = self.bpmn.new_process()
        new_num_processes = len(self.bpmn.processes)
        self.assertEqual(num_processes + 1, new_num_processes)
        self.assertNotEqual(None, proc)
    
    def test_del_process(self):
        """Test if the process is deleted"""
        proc = self.bpmn.new_process()
        num_processes = len(self.bpmn.processes)
        self.bpmn.del_process(proc)
        new_num_processes = len(self.bpmn.processes)
        self.assertEqual(num_processes - 1, new_num_processes)

    def test_duplicate(self):
        """Test if duplicate creates a deep copy"""
        self.bpmn.new_process()
        new_bpmn = self.bpmn.duplicate()
        self.assertEqual(len(self.bpmn.processes), len(new_bpmn.processes))
        self.assertNotEqual(self.bpmn.processes[0], new_bpmn.processes[0])
