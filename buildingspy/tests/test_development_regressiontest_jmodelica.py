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


class Test_regressiontest_jmodelica_Tester(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.regressiontest.Tester` for jmodelica.
    """

    def test_unit_test_log_file(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False, tool="jmodelica")
        self.assertEqual('unitTests-jmodelica.log', rt.get_unit_test_log_file())

    @staticmethod
    def _write_test(content):
        """ Write a unit test for a model with the content `content`
            in a temporary directory and return the name of this directory.
        """
        import os
        import tempfile

        dir_name = os.path.join(tempfile.mkdtemp(prefix='tmp-BuildingsPy-unittests-'), "TestLib")
        script_dir = os.path.join(dir_name, "Resources", "Scripts", "Dymola")
        mo_name = "Test"
        mo_content = """within TestLib;
          model Test
            {}
          end Test;
        """.format(content)

        # Create directory for mos scripts
        os.makedirs(script_dir)
        # Write mos file
        with open(os.path.join(script_dir, mo_name + ".mos"), mode="w", encoding="utf-8") as fil:
            con = """
simulateModel("TestLib.{}", tolerance=1e-6, stopTime=1.0, method="CVode", resultFile="test");""".format(mo_name)
            con = con + """
createPlot(id=1, y={"Test.x"});
"""
            fil.write(con)
        # Write mo file
        with open(os.path.join(dir_name, mo_name + ".mo"), mode="w", encoding="utf-8") as fil:
            fil.write(mo_content)
        # Write top-level package
        with open(os.path.join(dir_name, 'package.mo'), mode="w", encoding="utf-8") as fil:
            mo = """
            within;
            package TestLib
            end TestLib;
"""
            fil.write(mo)
        # Write top-level package.order
        with open(os.path.join(dir_name, 'package.order'), mode="w", encoding="utf-8") as fil:
            mo = """TestLib"""
            fil.write(mo)
        return dir_name


    @staticmethod
    def _delete_test(dir_name):
        """ Delete the test directory `dir_name`.
        """
        import shutil
        shutil.rmtree(dir_name)

    def test_regressiontest_diagnostics(self):
        """ Test that warnings and errors reported by JModelica are reported.
        """
        import buildingspy.development.regressiontest as r
        tests = [ \
                  {'retVal': 0,
                   'mo_content': """parameter Real[2] x(each unit="m") = {0, 0};""",
                   'description': "Corrected model."},
                  {'retVal': 2,
                   'mo_content': """parameter Real[2] x(unit="m") = {0, 0};""",
                   'description': "Missing each on variable."},
                  {'retVal': 2,
                   'mo_content': """parameter Real x(each unit="m") = 0;""",
                   'description': "Wrong each on scalar."},
                  {'retVal': 2,
                   'mo_content': """Modelica.Blocks.Sources.Constant b(each k=0) ;""",
                   'description': "Wrong each on scalar component."},
                  {'retVal': 2,
                   'mo_content': """Modelica.Blocks.Sources.Constant b[2](k=0) ;""",
                   'description': "Missing each on array of components."},
                  {'retVal': 2,
                   'mo_content': """Real x;
                                    equation
                                      Modelica.Math.exp(x)=1;""",
                   'description': "Missing start value."},
                  {'retVal': 2,
                   'mo_content': """parameter Real[2] x(unit="m") = {0, 0};
                                    parameter Real y(each unit="m") = 0;""",
                   'description': "Two errors."},
                  {'retVal': 1,
                   'mo_content': """x; """,
                   'description': "Syntax error that should cause a failure in translation."},
                  {'retVal': 1,
                   'mo_content': """Real x(start=0);
                                    equation
                                      Modelica.Math.exp(x)=-1;""",
                   'description': "Model that has no solution."}

]
        for test in tests:
            des = test['description']
            print("*** Running test for '{}'".format(des))
            mo_content = test['mo_content']
            dir_name = self._write_test(mo_content)
            rt = r.Tester(check_html=False, tool="jmodelica")
            rt.setLibraryRoot(dir_name)
            retVal = rt.run()
            # Delete temporary files
            self._delete_test(dir_name)
            os.remove(rt.get_unit_test_log_file())
            # Check return value to see if test suceeded
            self.assertEqual(test['retVal'], retVal, "Test for '{}' failed, return value {}".format(des, retVal))

    def test_regressiontest(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False, tool="jmodelica")
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.deleteTemporaryDirectories(True)
        rt.setLibraryRoot(myMoLib)
        rt.run()
        # Delete temporary files
        os.remove(rt.get_unit_test_log_file())


if __name__ == '__main__':
    unittest.main()
