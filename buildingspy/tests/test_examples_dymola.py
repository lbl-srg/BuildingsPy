#!/usr/bin/env python
import unittest
from buildingspy.io.postprocess import Plotter
import numpy.testing

class Test_example_dymola_runSimulation(unittest.TestCase):
    """      
       This class contains the unit tests for
       :mod:`buildingspy.io.Plotter`.
    """

    def test_runSimulation(self):
        ''' 
        Tests the :mod:`buildingspy/examples/dymola/runSimulation`
        module.
        '''
        import buildingspy.examples.dymola.runSimulation as s
        s.main()

if __name__ == '__main__':
    unittest.main()        

