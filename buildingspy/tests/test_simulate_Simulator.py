#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import unittest
import os
from buildingspy.simulate.base_simulator import _BaseSimulator


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
        _BaseSimulator(
            modelName="MyModelicaLibrary.myModel",
            outputDirectory="notSupported",
            outputFileList=None,
            packagePath=self._packagePath)
        os.rmdir("notSupported")


if __name__ == '__main__':
    unittest.main()
