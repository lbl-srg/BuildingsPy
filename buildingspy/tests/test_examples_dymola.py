#!/usr/bin/env python
import unittest

class Test_example_dymola_runSimulation(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.examples`.
    """

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
