#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import unittest
import os


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
