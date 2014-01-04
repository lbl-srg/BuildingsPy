#!/usr/bin/env python
import unittest
from buildingspy.simulate.Simulator import Simulator

class Test_simulate_Simulator(unittest.TestCase):
    """      
       This class contains the unit tests for
       :mod:`buildingspy.simulate.Simulator`.
    """

    def test_Constructor(self):
        ''' 
        Tests the :mod:`buildingspy.simulate.Simulator`
        constructor.
        '''
        self.assertRaises(ValueError, Simulator, "myModelicaLibrary.myModel", "notSupported")


    def test_addMethods(self):
        ''' 
        Tests the various add methods.
        '''
        import os
        import numpy as np

        from buildingspy.io.outputfile import Reader

        os.environ["MODELICAPATH"] = os.path.abspath(os.path.join("buildingspy", "tests", "MyModelicaLibrary"))
        s = Simulator("MyModelicaLibrary.MyModel", "dymola")
        s.addPreProcessingStatement("Advanced.StoreProtectedVariables:= true;")
        s.addPostProcessingStatement("Advanced.StoreProtectedVariables:= false;")
        s.addModelModifier('redeclare Modelica.Blocks.Sources.Step source(offset=-0.1, height=1.1, startTime=0.5)')
        s.setStartTime(-1)
        s.setStopTime(5)
        s.setTimeOut(600)
        s.setTolerance(1e-4)
        s.setSolver("dassl")
        s.setNumberOfIntervals(50)
        s.setResultFile("myResults")
        s.exitSimulator(True)
        s.deleteOutputFiles()
        s.showGUI(False)
#        s.printModelAndTime()
        s.showProgressBar(False)
        s.simulate()
        # Read the result and test their validity
        outDir = s.getOutputDirectory()
        resultFile = os.path.abspath(os.path.join(outDir, "myResults.mat"))
        r=Reader(resultFile, "dymola")
        np.testing.assert_allclose(1.0, r.max('source.y'))
        np.testing.assert_allclose(0.725, r.mean('source.y'))
        np.testing.assert_allclose(0.725*6, r.integral('source.y'))
        np.testing.assert_allclose(-0.1, r.min('source.y'))
        # Delete output files
        s.deleteOutputFiles()
        s.deleteLogFiles()

    def test_addGetParameters(self):
        ''' 
        Tests the :mod:`buildingspy.simulate.Simulator.addParameters`
        and the :mod:`buildingspy.simulate.Simulator.getParameters`
        functions.
        '''
        s = Simulator("myPackage.myModel", "dymola")
        # Make sure values are added correctly
        s.addParameters({'PID.k': 1.0, 'valve.m_flow_nominal' : 0.1})
        self.assertEqual(sorted(s.getParameters()), [('PID.k', 1.0), ('valve.m_flow_nominal', 0.1)])
        # Add one more parameter
        s.addParameters({'PID.t': 10.0})
        self.assertEqual(sorted(s.getParameters()), [('PID.k', 1.0), ('PID.t', 10.0), ('valve.m_flow_nominal', 0.1)])
        # Arguments must be a dictionary
        self.assertRaises(ValueError, s.addParameters, ["aaa", "bbb"])

if __name__ == '__main__':
    unittest.main()        

