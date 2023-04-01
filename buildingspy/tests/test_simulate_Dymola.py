#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import unittest
import os
from buildingspy.simulate.Dymola import Simulator


def _simulate(cas):
    """
    Class to simulate models. This needs to be at the top-level for multiprocessing
    to be able to serialize it.
    """
    from buildingspy.simulate.Dymola import Simulator

    packagePath = os.path.abspath(os.path.join("buildingspy", "tests", "MyModelicaLibrary"))
    s = Simulator(cas['model'], outputDirectory=f"out-{cas['tol']}", packagePath=packagePath)
    s.setTolerance(cas['tol'])
    s.simulate()


class Test_simulate_Simulator(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.simulate.Dymola`.
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
        Tests the :mod:`buildingspy.simulate.Dymola`
        constructor.
        """
        Simulator(
            modelName="MyModelicaLibrary.myModel",
            outputDirectory="notSupported",
            packagePath=self._packagePath)

        # Check that this path does not exists
        with self.assertRaises(ValueError):
            Simulator(
                modelName="MyModelicaLibrary.myModel",
                outputDirectory="notSupported",
                packagePath="ThisIsAWrongPath")

    def test_setPackagePath(self):
        """
        Tests the ``setPackagePath'' method.
        """
        s = Simulator("MyModelicaLibrary.MyModel", packagePath=self._packagePath)

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
                outputDirectory=".",
                packagePath="THIS IS NOT A VALID PACKAGE PATH")

    def test_translate(self):
        """
        Tests the various add methods.
        """
        s = Simulator("MyModelicaLibrary.MyModel", packagePath=self._packagePath)
        s.translate()

    def test_simulate_user_library(self):
        """
        Tests simulating a model from the Modelica Standard Library.

        """
        s = Simulator("MyModelicaLibrary.MyModel", packagePath=self._packagePath)
        s.simulate()

    def test_simulate_msl(self):
        """
        Tests simulating a model from the Modelica Standard Library.

        This test is for https://github.com/lbl-srg/BuildingsPy/issues/472
        """
        s = Simulator("Modelica.Blocks.Examples.PID_Controller")
        s.simulate()

    def test_addMethods(self):
        """
        Tests the various add methods.
        """
        import numpy as np

        from buildingspy.io.outputfile import Reader

        s = Simulator("MyModelicaLibrary.MyModel", packagePath=self._packagePath)
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

    def test_addGetParameters(self):
        """
        Tests the :mod:`buildingspy.simulate.Dymola.addParameters`
        and the :mod:`buildingspy.simulate.Dymola.getParameters`
        functions.
        """
        s = Simulator("myPackage.myModel", packagePath=self._packagePath)
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
        Tests the :mod:`buildingspy.simulate.Dymola.addParameters`
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
                      packagePath=self._packagePath)
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

    def test_setBooleanParameterValues(self):
        """
        Tests the :mod:`buildingspy.simulate.Dymola.addParameters`
        function for boolean parameters.
        """

        from buildingspy.io.outputfile import Reader
        # Delete output file
        resultFile = os.path.join("BooleanParameters.mat")

        if os.path.exists(resultFile):
            os.remove(resultFile)

        s = Simulator("MyModelicaLibrary.Examples.BooleanParameters",
                      packagePath=self._packagePath)
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

    def test_raisesAssertionIfWrongDataType(self):
        """
        Tests the :mod:`buildingspy.simulate.Dymola.simulate`
        function to make sure it raises an assertion if a model fails to translate.
        """
        model = "MyModelicaLibrary.Examples.BooleanParameters"

        s = Simulator(model, packagePath=self._packagePath)
        s.addParameters({'p1': 123})  # p1 is a boolean parameter. This will fail the model.
        with self.assertRaises(Exception):
            s.simulate()

    def test_timeout(self, timeout=3):
        model = 'MyModelicaLibrary.MyModelTimeOut'
        s = Simulator(
            model,
            packagePath=self._packagePath
        )
        s._deleteTemporaryDirectory = False
        outDir = os.path.abspath(s.getOutputDirectory())
        s.setTimeOut(timeout)
        with self.assertRaises(TimeoutError):
            s.simulate()
        with open(os.path.join(outDir, s._reporter._logFil)) as fh:
            log = fh.read()
        self.assertTrue('Terminating simulation' in log and 'Process timeout' in log)
        s.setTimeOut(-1)
        s.simulate()
        with open(os.path.join(outDir, 'dslog.txt')) as fh:
            log = fh.read()
        self.assertTrue('Integration terminated successfully' in log)

    def test_multiprocessing(self):
        import os
        import shutil
        from multiprocessing import Pool
        import json

        def _deleteDirs(cases):
            for cas in cases:
                output_dir = f"out-{cas['tol']}"
                shutil.rmtree(output_dir, ignore_errors=True)

        cases = [
            {"model": "MyModelicaLibrary.Examples.MyStep", "tol": 1E-6},
            {"model": "MyModelicaLibrary.Examples.MyStep", "tol": 1E-7}
        ]
        # Delete old directories
        _deleteDirs(cases)

        p = Pool()
        p.map(_simulate, cases)
        p.close()

        # Check output for success
        for cas in cases:
            resultFile = os.path.join(f"out-{cas['tol']}", "dslog.txt")

            self.assertTrue(
                os.path.exists(resultFile), f"File {resultFile} does not exist.")

            with open(resultFile) as f:
                con = f.read()
            self.assertTrue("Integration terminated successfully" in con,
                            f"Expected string 'Integration terminated successfully' in {resultFile}")

        # Delete working directories
        _deleteDirs(cases)

        return


if __name__ == '__main__':
    unittest.main()
