import unittest

import sys, os, os.path
rootDirectory = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..')
if rootDirectory not in sys.path:
    sys.path.append(rootDirectory)

import batlab

class TestBatlabGeneral(unittest.TestCase):
    def test_tests_are_running(self):
        self.assertEqual(True, True)

    def test_batpool_imported(self):
        batpool = batlab.batpool.Batpool()
        self.assertIsNotNone(batpool)

    def test_batlabutil_exists(self):
        self.assertIsNotNone(batlab.batlabutil)
