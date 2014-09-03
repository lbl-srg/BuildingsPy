#!/usr/bin/env python
import unittest

class Test_example_dymola_runSimulation(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.io.Plotter`.
    """
    
    def setUp(self):
        '''
        This method creates a variable that points to an existing folder
        that contains a Modelica package.
        '''
        import os
        self._oldWorDir = os.getcwd()
        # Change to a directory that contains a package.mo file
#        os.chdir(os.path.abspath(os.path.join("buildingspy", "tests", "MyModelicaLibrary")))
        print "**************** PYTHONPATH =", os.getenv("PYTHONPATH", "not specified")


    def tearDown(self):
        '''
        This method resets the current working directory
        '''
        import os
        os.chdir(self._oldWorDir)
    

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

