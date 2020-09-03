#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# import from future to make Python2 behave like Python3
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import *
from io import open
# end of from future import

import unittest
import os
from buildingspy.simulate.Simulator import Simulator


class Test_simulate_Simulator(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.simulate.Simulator`.
    """

    def setUp(self):
        """
        This method creates a variable that points to an existing folder
        that contains a Modelica package.
        """
        self._packagePath = os.path.abspath(os.path.join(
            "buildingspy", "tests", "MyModelicaLibrary"))

    def test_Constructor(self):
        """
        Tests the :mod:`buildingspy.simulate.Simulator`
        constructor.
        """
        self.assertRaises(
            ValueError,
            Simulator,
            "myModelicaLibrary.myModel",
            "notSupported",
            packagePath=self._packagePath)

        # Check that this path does not exists
        self.assertRaises(ValueError, Simulator,
                          "myModelicaLibrary.myModel", "notSupported", "ThisIsAWrongPath")

        # Check that this path does not contain a package.mo file
        path = os.path.abspath(os.path.join("buildingspy", "tests"))
        self.assertRaises(ValueError, Simulator,
                          "myModelicaLibrary.myModel", "notSupported", path)

    def test_setPackagePath(self):
        """
        Tests the ``setPackagePath'' method.
        """
        s = Simulator("MyModelicaLibrary.MyModel", "dymola", packagePath=self._packagePath)

        # Try to load an existing path.
        p = os.path.abspath(os.path.join("buildingspy", "tests", "MyModelicaLibrary"))
        s.setPackagePath(p)

        # Try to load a not existing path.
        self.assertRaises(ValueError, s.setPackagePath, "ThisIsAWrongPath")

    def test_wrong_package_path_simulation(self):
        """
        Tests reporting the exception if a simulation fails.
        """
        with self.assertRaises(ValueError):
            Simulator(
                modelName="MyModelicaLibrary.MyModel",
                simulator="dymola",
                packagePath="THIS IS NOT A VALID PACKAGE PATH")

    def test_addMethods(self):
        """
        Tests the various add methods.
        """
        import numpy as np

        from buildingspy.io.outputfile import Reader

        s = Simulator("MyModelicaLibrary.MyModel", "dymola", packagePath=self._packagePath)
        s.addPreProcessingStatement("Advanced.StoreProtectedVariables:= true;")
        s.addPostProcessingStatement("Advanced.StoreProtectedVariables:= false;")
        s.addModelModifier(
            "redeclare Modelica.Blocks.Sources.Step source(offset=-0.1, height=1.1, startTime=0.5)")
        s.setStartTime(-1)
        s.setStopTime(5)
        s.setTimeOut(600)
        s.setTolerance(1e-4)
        s.setSolver("dassl")
        s.setNumberOfIntervals(50)
        s.setResultFile("myResults")
        s.exitSimulator(True)
        # s.deleteOutputFiles()
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
        np.testing.assert_allclose(0.725 * 6, r.integral('source.y'))
        np.testing.assert_allclose(-0.1, r.min('source.y'))
        # Delete output files
        s.deleteOutputFiles()
        s.deleteLogFiles()

    def test_addGetParameters(self):
        """
        Tests the :mod:`buildingspy.simulate.Simulator.addParameters`
        and the :mod:`buildingspy.simulate.Simulator.getParameters`
        functions.
        """
        s = Simulator("myPackage.myModel", "dymola", packagePath=self._packagePath)
        # Make sure values are added correctly
        s.addParameters({'PID.k': 1.0, 'valve.m_flow_nominal': 0.1})
        self.assertEqual(sorted(s.getParameters()), [('PID.k', 1.0), ('valve.m_flow_nominal', 0.1)])
        # Add one more parameter
        s.addParameters({'PID.t': 10.0})
        self.assertEqual(sorted(s.getParameters()), [
                         ('PID.k', 1.0), ('PID.t', 10.0), ('valve.m_flow_nominal', 0.1)])
        # Arguments must be a dictionary
        self.assertRaises(ValueError, s.addParameters, ["aaa", "bbb"])

    def test_addVectorOfParameterValues(self):
        """
        Tests the :mod:`buildingspy.simulate.Simulator.addParameters`
        function for the situation where values for a parameter that is
        a vector is added.
        """
        import numpy as np
        from buildingspy.io.outputfile import Reader
        # Delete output file
        resultFile = os.path.join("Constants.mat")
        if os.path.exists(resultFile):
            os.remove(resultFile)

        s = Simulator("MyModelicaLibrary.Examples.Constants",
                      "dymola", packagePath=self._packagePath)
        s.addParameters({'const1.k': [2, 3]})
        s.addParameters({'const2.k': [[1.1, 1.2], [2.1, 2.2], [3.1, 3.2]]})
        s.addParameters({'const3.k': 0})
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
        """
        Tests the :mod:`buildingspy.simulate.Simulator.addParameters`
        function for boolean parameters.
        """

        from buildingspy.io.outputfile import Reader
        # Delete output file
        resultFile = os.path.join("BooleanParameters.mat")

        if os.path.exists(resultFile):
            os.remove(resultFile)

        s = Simulator("MyModelicaLibrary.Examples.BooleanParameters",
                      "dymola", packagePath=self._packagePath)
        s.addParameters({'p1': True})
        s.addParameters({'p2': False})
        s.simulate()

        r = Reader(resultFile, "dymola")

        (_, p) = r.values('p1')
        self.assertEqual(p[0], 1.0)
        (_, p) = r.values('p2')
        self.assertEqual(p[0], 0.0)
        # Delete output files
        s.deleteOutputFiles()
        s.deleteLogFiles()


if __name__ == '__main__':
    unittest.main()
