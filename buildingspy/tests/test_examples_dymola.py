#!/usr/bin/env python
import unittest
import os
from buildingspy.io.postprocess import Plotter
import numpy.testing

class Test_example_dymola_runSimulation(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.io.Plotter`.
    """
    def setUp(self):
        '''
        This method creates an environmental variable that points to an existing folder
        that contains a Modelica package.
        '''
        os.environ["MODELICAPATH"] = os.path.abspath(os.path.join("buildingspy", "tests", "MyModelicaLibrary"))
    
    def tearDown(self):
        '''
        This method delete the environmental variable that points to an existing folder
        that contains a Modelica package.
        '''
        del(os.environ["MODELICAPATH"])
        
    def test_runSimulation(self):
        '''
        Tests the :mod:`buildingspy/examples/dymola/runSimulation`
        module.
        '''
        import shutil
        import buildingspy.examples.dymola.runSimulation as s
        s.main()
        # Delete output directories
        shutil.rmtree('case1')
        shutil.rmtree('case2')

if __name__ == '__main__':
    unittest.main()

