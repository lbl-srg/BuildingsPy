#!/usr/bin/env python
import unittest
from test.test_support import EnvironmentVarGuard

class Test_example_dymola_runSimulation(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.examples`.
    """

    def setUp(self):
        ''' Ensure that environment variables that are needed to run
            the tests are set
        '''
        self.env = EnvironmentVarGuard()
        # Set MODELICALIBRARY which is required to run
        # runSimulationTranslated.py
        self.env.setdefault("MODELICALIBRARY", "/usr/local/Modelica/Library")
        
    def test_runSimulation(self):
        '''
        Tests the :mod:`buildingspy/examples/dymola/runSimulation`
        function.
        '''
        import buildingspy.examples.dymola.runSimulation as s
        s.main()

    def test_runSimulationTranslated(self):
        '''
        Tests the :mod:`buildingspy/examples/dymola/runSimulationTranslated`
        function.
        '''
        import buildingspy.examples.dymola.runSimulationTranslated as s
        s.main()

    def test_plotResult(self):
        '''
        Tests the :mod:`buildingspy/examples/dymola/plotResult`
        function.
        '''
        import os
        import buildingspy.examples.dymola.plotResult as s
        s.main()
        # Remove the generated plot files
        os.remove("plot.pdf")
        os.remove("plot.png")

if __name__ == '__main__':
    unittest.main()
