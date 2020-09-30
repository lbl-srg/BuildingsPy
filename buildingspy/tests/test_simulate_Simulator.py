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
            "buildingspy", "tests"))

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


if __name__ == '__main__':
    unittest.main()
