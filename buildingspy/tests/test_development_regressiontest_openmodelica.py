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

# To run this test, navigate to the BuildingsPy folder, then type
# python buildingspy/tests/test_development_regressiontest.py


class Test_regressiontest_openmodelica_Tester(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.regressiontest.Tester` for OpenModelica.
    """

    def test_unit_test_log_file_omc(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False, tool="omc")
        self.assertEqual('unitTests-omc.log', rt.get_unit_test_log_file())


    def test_test_OpenModelica(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        rt._deleteTemporaryDirectories = False

        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.test_OpenModelica(simulate=True)

if __name__ == '__main__':
    unittest.main()
