#!/usr/bin/env python
import unittest
import os
from buildingspy.simulate.Simulator import Simulator

class Test_simulate_Simulator(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.simulate.Simulator`.
    """

    def setUp(self):
        '''
        This method creates a variable that points to an existing folder
        that contains a Modelica package.
        '''
        self._packagePath = os.path.abspath(os.path.join("buildingspy", "tests", "MyModelicaLibrary"))

    def test_Constructor(self):
        '''
        Tests the :mod:`buildingspy.simulate.Simulator`
        constructor.
        '''
        self.assertRaises(ValueError, Simulator,
                          "myModelicaLibrary.myModel", "notSupported", packagePath=self._packagePath)

        # Check that this path does not exists
        self.assertRaises(ValueError, Simulator,
                          "myModelicaLibrary.myModel", "notSupported", "ThisIsAWrongPath")

        # Check that this path does not contain a package.mo file
        path = os.path.abspath(os.path.join("buildingspy", "tests"))
        self.assertRaises(ValueError, Simulator,
                          "myModelicaLibrary.myModel", "notSupported", path)

    def test_setPackagePath(self):
        '''
        Tests the ``setPackagePath'' method.
        '''
        s = Simulator("MyModelicaLibrary.MyModel", "dymola", packagePath=self._packagePath)

        # Try to load an existing path.
        p = os.path.abspath(os.path.join("buildingspy", "tests", "MyModelicaLibrary"))
        s.setPackagePath(p)

        # Try to load a not existing path.
        self.assertRaises(ValueError, s.setPackagePath, "ThisIsAWrongPath")

    def test_addMethods(self):
        '''
        Tests the various add methods.
        '''
        import numpy as np

        from buildingspy.io.outputfile import Reader


        s = Simulator("MyModelicaLibrary.MyModel", "dymola", packagePath=self._packagePath)
        s.addPreProcessingStatement("Advanced.StoreProtectedVariables:= true;")
        s.addPostProcessingStatement("Advanced.StoreProtectedVariables:= false;")
        s.addModelModifier("redeclare Modelica.Blocks.Sources.Step source(offset=-0.1, height=1.1, startTime=0.5)")
        s.setStartTime(-1)
        s.setStopTime(5)
        s.setTimeOut(600)
        s.setTolerance(1e-4)
        s.setSolver("dassl")
        s.setNumberOfIntervals(50)
        s.setResultFile("myResults")
        s.exitSimulator(True)
        #s.deleteOutputFiles()
        s.showGUI(False)
#        s.printModelAndTime()
        s.showProgressBar(False)
        s.simulate()
        # Read the result and test their validity
        outDir = s.getOutputDirectory()
        resultFile = os.path.abspath(os.path.join(outDir, "myResults.mat"))
        r = Reader(resultFile, "dymola")
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
        s = Simulator("myPackage.myModel", "dymola", packagePath=self._packagePath)
        # Make sure values are added correctly
        s.addParameters({'PID.k': 1.0, 'valve.m_flow_nominal' : 0.1})
        self.assertEqual(sorted(s.getParameters()), [('PID.k', 1.0), ('valve.m_flow_nominal', 0.1)])
        # Add one more parameter
        s.addParameters({'PID.t': 10.0})
        self.assertEqual(sorted(s.getParameters()), [('PID.k', 1.0), ('PID.t', 10.0), ('valve.m_flow_nominal', 0.1)])
        # Arguments must be a dictionary
        self.assertRaises(ValueError, s.addParameters, ["aaa", "bbb"])

    def test_addVectorOfParameterValues(self):
        '''
        Tests the :mod:`buildingspy.simulate.Simulator.addParameters`
        function for the situation where values for a parameter that is
        a vector is added.
        '''
        import numpy as np
        from buildingspy.io.outputfile import Reader
        # Delete output file
        resultFile = os.path.join("Constants.mat")
        if os.path.exists(resultFile):
            os.remove(resultFile)

        s = Simulator("MyModelicaLibrary.Examples.Constants", "dymola", packagePath=self._packagePath)
        s.addParameters({'const1.k' : [2, 3]})
        s.addParameters({'const2.k' : [[1.1, 1.2], [2.1, 2.2], [3.1, 3.2]]})
        s.addParameters({'const3.k' : 0})
        s.simulate()

        r = Reader(resultFile, "dymola")

        np.testing.assert_allclose(2, r.max('const1[1].y'))
        np.testing.assert_allclose(3, r.max('const1[2].y'))

        np.testing.assert_allclose(1.1, r.max('const2[1, 1].y'))
        np.testing.assert_allclose(1.2, r.max('const2[1, 2].y'))
        np.testing.assert_allclose(2.1, r.max('const2[2, 1].y'))
        np.testing.assert_allclose(2.2, r.max('const2[2, 2].y'))
        np.testing.assert_allclose(3.1, r.max('const2[3, 1].y'))
        np.testing.assert_allclose(3.2, r.max('const2[3, 2].y'))

        np.testing.assert_allclose(0, r.max('const3.y'))
        # Delete output files
        s.deleteOutputFiles()
        s.deleteLogFiles()

    def test_setBooleanParameterValues(self):
        '''
        Tests the :mod:`buildingspy.simulate.Simulator.addParameters`
        function for boolean parameters.
        '''

        from buildingspy.io.outputfile import Reader
        # Delete output file
        resultFile = os.path.join("BooleanParameters.mat")

        if os.path.exists(resultFile):
            os.remove(resultFile)

        s = Simulator("MyModelicaLibrary.Examples.BooleanParameters", "dymola", packagePath=self._packagePath)
        s.addParameters({'p1' : True})
        s.addParameters({'p2' : False})
        s.simulate()

        r = Reader(resultFile, "dymola")

        (_, p) = r.values('p1')
        self.assertEqual(p[0], 1.0)
        (_, p) = r.values('p2')
        self.assertEqual(p[0], 0.0)
        # Delete output files
        s.deleteOutputFiles()
        s.deleteLogFiles()

    def test_translate_simulate(self):
        '''
        Tests the :mod:`buildingspy.simulate.Simulator.translate` and
        the :mod:`buildingspy.simulate.Simulator.simulate_translated`
        method.
        '''
        import numpy as np

        from buildingspy.io.outputfile import Reader

        s = Simulator("MyModelicaLibrary.MyModel", "dymola", packagePath=self._packagePath)
        s.addModelModifier("redeclare Modelica.Blocks.Sources.Step source(offset=-0.1, height=1.1, startTime=0.5)")
        s.setStartTime(-1)
        s.setStopTime(5)
        s.setTimeOut(600)
        s.setTolerance(1e-4)
        s.setSolver("dassl")
        s.setNumberOfIntervals(50)
        s.setResultFile("myResults")
        s.translate()
        s.simulate_translated()

        # Read the result and test their validity
        outDir = s.getOutputDirectory()
        resultFile = os.path.abspath(os.path.join(outDir, "myResults.mat"))
        r = Reader(resultFile, "dymola")
        np.testing.assert_allclose(1.0, r.max('source.y'))
        np.testing.assert_allclose(-0.1, r.min('source.y'))
        np.testing.assert_allclose(0.725, r.mean('source.y'))
        np.testing.assert_allclose(0.725*6, r.integral('source.y'))
        # Delete output files
        s.deleteOutputFiles()
        s.deleteLogFiles()

        # Make another simulation, but now the start time is at -2, and the height is 2.1
        s.setStartTime(-2)
        s.addParameters({'source.height': 2.1})
        s.simulate_translated()
        outDir = s.getOutputDirectory()
        resultFile = os.path.abspath(os.path.join(outDir, "myResults.mat"))
        r = Reader(resultFile, "dymola")
        np.testing.assert_allclose(2.0, r.max('source.y'))
        np.testing.assert_allclose(-0.1, r.min('source.y'))
        np.testing.assert_allclose(1.25, r.mean('source.y'))
        np.testing.assert_allclose(7*1.25, r.integral('source.y'))

        # clean up translate temporary dir
        s.deleteOutputFiles()
        s.deleteLogFiles()
        s.deleteTranslateDirectory()


    def test_translate_simulate_exception_parameter(self):
        '''
        Tests the :mod:`buildingspy.simulate.Simulator.translate` and
        the :mod:`buildingspy.simulate.Simulator.simulate_translated`
        method.
        This tests whether an exception is thrown if
        one attempts to change a parameter that is fixed after compilation
        '''
        import numpy as np
        from buildingspy.io.outputfile import Reader

        s = Simulator("MyModelicaLibrary.Examples.ParameterEvaluation", "dymola", packagePath=self._packagePath)
        s.translate()
        s.setSolver("dassl")
        desired_value = 0.2
        s.addParameters({'x': desired_value})
        # Simulate the model with new parameter and check in the output file
        # whether the parameter is really set.
        # Dymola 2016 FD01 sets it correctly, but Dymola 2016 does not.
        try:
            s.simulate_translated()
            # No exception. Check results
            actual_res = Reader(os.path.join(".",
                                             'ParameterEvaluation.mat'),
                                             'dymola')
            (_, y) = actual_res.values('x')
            (_, n) = actual_res.values('n')
            np.testing.assert_allclose(y[0], desired_value)
            np.testing.assert_allclose(n[0], 5)
        except IOError as e:
            # An IOError was raised. Make sure it is raised by simulate_translated
            print "Caught IOError with message '{}'".format(e)
            self.assertRaises(IOError, s.simulate_translated)
        # clean up translate temporary dir
        s.deleteTranslateDirectory()
        # Delete output files
        s.deleteOutputFiles()
        s.deleteLogFiles()
        # This is called to clean up after an exception in simulate_translated().
        s.deleteSimulateDirectory()

    def test_translate_simulate_exception_error(self):
        '''
        Tests the :mod:`buildingspy.simulate.Simulator.translate` and
        the :mod:`buildingspy.simulate.Simulator.simulate_translated`
        method.
        This tests whether an exception is thrown if
        the simulation settings are not appropriate.
        '''

        s = Simulator("MyModelicaLibrary.Examples.ParameterEvaluation", "dymola", packagePath=self._packagePath)
        s.translate()
        s.setSolver("radau")
        # The next call must throw an exception.
        self.assertRaises(IOError, s.simulate_translated)
        # clean up translate temporary dir
        s.deleteTranslateDirectory()
        # Delete output files
        s.deleteOutputFiles()
        s.deleteLogFiles()
        # This is called to clean up after an exception in simulate_translated().
        s.deleteSimulateDirectory()

if __name__ == '__main__':
    unittest.main()
