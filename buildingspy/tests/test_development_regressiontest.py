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


class Test_regressiontest_Tester(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.regressiontest.Tester`.
    """

    def test_get_plot_variables(self):
        import buildingspy.development.regressiontest as r

        self.assertIsNone(r.Tester.get_plot_variables("abc"), "Expected None return value")
        self.assertIsNone(r.Tester.get_plot_variables("y=abc"), "Expected None return value")
        self.assertIsNone(r.Tester.get_plot_variables(
            "leftTitleType=1, bottomTitleType=1, colors={{0,0,255},"), "Expected None")

        self.assertEqual(["a", "b", "c"], r.Tester.get_plot_variables(
            'y = {"a", "b", "c"}'), "Expected a b c")
        self.assertEqual(["a", "b", "c"], r.Tester.get_plot_variables(
            'y = {"a","b","c"}'), "Expected a b c")
        self.assertEqual(["a", "b", "c"], r.Tester.get_plot_variables(
            'y = {" a", "b ", "c"}'), "Expected a b c")
        self.assertEqual(["a", "b", "c"], r.Tester.get_plot_variables(
            'y = {" a" , "b " , "c"}'), "Expected a b c")
        self.assertEqual(["a", "b", "c"], r.Tester.get_plot_variables(
            'y = {"a","b","c"}'), "Expected a b c")
        self.assertEqual(["a"], r.Tester.get_plot_variables('y = {"a"}'), "Expected a")
        self.assertEqual(["a"], r.Tester.get_plot_variables('y = { "a"}'), "Expected a")
        self.assertEqual(["a"], r.Tester.get_plot_variables('y = { "a" }'), "Expected a")
        self.assertEqual(["a"], r.Tester.get_plot_variables('y ={ "a" }'), "Expected a")
        self.assertEqual(["a"], r.Tester.get_plot_variables('y={ "a" }'), "Expected a")

        self.assertEqual(["a"], r.Tester.get_plot_variables('abc, y = {"a"}'), "Expected a")
        self.assertEqual(["a"], r.Tester.get_plot_variables(
            'x= {"x"}, y = {"a"}, z = {"s"}'), "Expected a")
        self.assertEqual(["x_incStrict[1]", "x_incStrict[2]"],
                         r.Tester.get_plot_variables('y={"x_incStrict[1]", "x_incStrict[2]"},'),
                         "Expect other result")
        self.assertEqual(["const1[1].y", "const2[1, 1].y"],
                         r.Tester.get_plot_variables(' y={"const1[1].y", "const2[1, 1].y"} '))

        # Make sure line breaks are raising an error, as they are not parsed
        self.assertRaises(ValueError, r.Tester.get_plot_variables,
                          """y = {"a", "b",
                          "c"}""")

    def test_regressiontest_dymola(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.include_fmu_tests(True)
        rt.writeOpenModelicaResultDictionary()
        rt.run()
        # Delete temporary files
        os.remove(rt.get_unit_test_log_file())

    def test_unit_test_log_file_jmodelica(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False, tool="jmodelica")
        self.assertEqual('unitTests-jmodelica.log', rt.get_unit_test_log_file())

    def test_unit_test_log_file_dymola(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False, tool="dymola")
        self.assertEqual('unitTests-dymola.log', rt.get_unit_test_log_file())

    def test_unit_test_log_file_omc(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False, tool="omc")
        self.assertEqual('unitTests-omc.log', rt.get_unit_test_log_file())

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

    def test_regressiontest_jmodelica_diagnostics(self):
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
            mo_content = test['mo_content']
            dir_name = self._write_test(mo_content)
            rt = r.Tester(check_html=False, tool="jmodelica")
            rt.setLibraryRoot(dir_name)
            retVal = rt.run()
            # Delete temporary files
            self._delete_test(dir_name)
            os.remove(rt.get_unit_test_log_file())
            # Check return value to see if test suceeded
            self.assertEqual(test['retVal'], retVal, "Test for '{}' failed, return value {}".format(test['description'], retVal))

    def test_regressiontest_jmodelica(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False, tool="jmodelica")
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.deleteTemporaryDirectories(True)
        rt.setLibraryRoot(myMoLib)
        rt.run()
        # Delete temporary files
        os.remove(rt.get_unit_test_log_file())

    def test_regressiontest(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        # Verify that invalid packages raise a ValueError.
        self.assertRaises(ValueError, rt.setSinglePackage, "this.package.does.not.exist")

    def test_setSinglePackage(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.include_fmu_tests(True)
        self.assertEqual(0, rt.get_number_of_tests())

    def test_setSinglePackage_1(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.include_fmu_tests(True)
        rt.setSinglePackage("MyModelicaLibrary.Examples.FMUs")
        self.assertEqual(3, rt.get_number_of_tests())

    def test_setSinglePackage_2(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.include_fmu_tests(True)
        rt.setSinglePackage("MyModelicaLibrary.Examples")
        self.assertEqual(6, rt.get_number_of_tests())

    def test_setSinglePackage_3(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.include_fmu_tests(True)
        rt.setSinglePackage("MyModelicaLibrary.Examples.FMUs,MyModelicaLibrary.Examples")
        self.assertEqual(6, rt.get_number_of_tests())

    def test_setSinglePackage_4(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.include_fmu_tests(True)
        # No new tests should be found as FMUs is a subdirectory of Examples.
        self.assertRaises(ValueError, rt.setSinglePackage,
                          "MyModelicaLibrary.Examples,MyModelicaLibrary.Examples.FMUs")

    def test_setExcludeTest(self):
        import buildingspy.development.regressiontest as r
        print("*** Running test_setExcludeTest that excludes files from unit test.\n")
        rt = r.Tester(check_html=False)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        skpFil = os.path.join(myMoLib, "Resources", "Scripts", "skipUnitTestList.txt")
        rt.setLibraryRoot(myMoLib)
        rt.setExcludeTest(skpFil)
        rt.run()
        self.assertEqual(1, rt.get_number_of_tests())
        print("*** Finished test_setExcludeTest.\n")

    def test_runSimulation(self):
        import buildingspy.development.regressiontest as r
        self.assertRaises(OSError,
                          r.runSimulation, ".", "this_command_does_not_exist")

    def test_areResultsEqual(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester()
        tMin = 10
        tMax = 50
        nPoi = 101
        tOld = [tMin, tMax]
        yOld = [10, 10]
        tNew = [tMin + float(i) / (nPoi - 1) * (tMax - tMin) for i in range(nPoi)]
        yNew = [10.0 for i in range(nPoi)]
        varNam = "testVariable"
        filNam = "testFilename"
        (equ, _, _) = rt.areResultsEqual(tOld, yOld, tNew, yNew, varNam, filNam)
        self.assertTrue(equ, "Test 1 for equality failed.")
        # Test with arguments reversed.
        (equ, _, _) = rt.areResultsEqual(tNew, yNew, tOld, yOld, varNam, filNam)
        self.assertTrue(equ, "Test 2 for equality failed.")
        # Modify arguments, now both tests should return false
        yNew[2] = 11.0
        (equ, timMaxErr, _) = rt.areResultsEqual(tOld, yOld, tNew, yNew, varNam, filNam)
        self.assertFalse(equ, "Test 1 for equality should have returned false.")
        self.assertEqual(tNew[2], timMaxErr, "Time of maximum error is wrong for test 1.")
        # Test with arguments reversed.
        (equ, timMaxErr, _) = rt.areResultsEqual(tNew, yNew, tOld, yOld, varNam, filNam)
        self.assertFalse(equ, "Test 2 for equality should have returned false.")
        self.assertEqual(tNew[2], timMaxErr, "Time of maximum error is wrong for test 2.")

        # Test the case where the simulation may have failed and hence the end
        # time is smaller than the end time of the reference results
        tNew = [tMin + float(i) / (nPoi - 1) * 0.9 * (tMax - tMin) for i in range(nPoi)]
        yNew = [10.0 for i in range(nPoi)]
        (equ, timMaxErr, _) = rt.areResultsEqual(tNew, yNew, tOld, yOld, varNam, filNam)
        self.assertFalse(equ, "Test with smaller simulation end time should have returned false.")
        # Test for different start time
        tNew = [0.1 + tMin + float(i) / (nPoi - 1) * (tMax - tMin) for i in range(nPoi)]
        (equ, timMaxErr, _) = rt.areResultsEqual(tNew, yNew, tOld, yOld, varNam, filNam)
        self.assertFalse(equ, "Test with smaller simulation start time should have returned false.")

    def test_statistics_are_equal(self):
        import buildingspy.development.regressiontest as r

        rt = r.Tester()
        self.assertTrue(rt.are_statistics_equal("0", "0"))
        self.assertTrue(rt.are_statistics_equal("", ""))
        self.assertTrue(rt.are_statistics_equal(" ", " "))
        self.assertFalse(rt.are_statistics_equal(" ", "0"))
        self.assertFalse(rt.are_statistics_equal("1", "1 1"))
        # 1, 2 is equal to 2, 1
        self.assertTrue(rt.are_statistics_equal("1, 2", "2, 1"))
        self.assertTrue(rt.are_statistics_equal("1, 40, 2", "2, 1, 40"))
        self.assertFalse(rt.are_statistics_equal("1, 40", "1, 40, 0"))

    def test_format_float(self):
        import buildingspy.development.regressiontest as r

        rt = r.Tester()

        self.assertEqual(float(rt.format_float(1.0)), float(1))
        self.assertEqual(float(rt.format_float(0.5)), float(0.5))
        self.assertEqual(float(rt.format_float(1.234)), float(1.234))
        self.assertEqual(float(rt.format_float(100)), float(100))
        self.assertEqual(float(rt.format_float(100.)), float(100.))
        self.assertEqual(float(rt.format_float(100.01230)), float(100.01230))
        self.assertEqual(float(rt.format_float(-100.01230)), float(-100.01230))
        self.assertEqual(float(rt.format_float(-100.0123)), float(-100.0123))

    def test_setLibraryRoot(self):
        import buildingspy.development.regressiontest as r

        rt = r.Tester()
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        # This call should succeed, even if used twice
        rt.setLibraryRoot(myMoLib)
        rt.setLibraryRoot(myMoLib)
        # This call must raise an exception
        self.assertRaises(ValueError,
                          rt.setLibraryRoot, "this_is_not_the_root_dir_of_a_library")

    def test_test_OpenModelica(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        rt._deleteTemporaryDirectories = False

        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.test_OpenModelica(simulate=True)

    def test_setDataDictionary(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.setDataDictionary()

    def test_expand_packages(self):
        import buildingspy.development.regressiontest as r

        self.assertEqual("A.B",
                         r.Tester.expand_packages("A.B"))
        self.assertEqual("A.B,A.C",
                         r.Tester.expand_packages("A.{B,C}"))
        self.assertEqual("A.B.xy,A.B.xy.z",
                         r.Tester.expand_packages("A.B.{xy,xy.z}"))

        # Add spaces
        self.assertEqual("A.B,A.C",
                         r.Tester.expand_packages("A.{B, C}"))
        self.assertEqual("A.B,A.C",
                         r.Tester.expand_packages("A.{ B , C }"))
        self.assertEqual("A.B.xy,A.B.xy.z",
                         r.Tester.expand_packages("A.B.{xy, xy.z}"))
        self.assertEqual("A.B.xy,A.B.xy.z",
                         r.Tester.expand_packages("A.B.{ xy, xy.z}"))
        self.assertEqual("A.B.xy,A.B.xy.z",
                         r.Tester.expand_packages("A.B.{ xy , xy.z }"))

        self.assertRaises(ValueError,
                          r.Tester.expand_packages, "AB{")
        self.assertRaises(ValueError,
                          r.Tester.expand_packages, "AB{}")
        self.assertRaises(ValueError,
                          r.Tester.expand_packages, "AB}a{")


if __name__ == '__main__':
    unittest.main()
    #selection = unittest.TestSuite()
    # selection.addTest(Test_regressiontest_Tester('test_test_OpenModelica'))
    # unittest.TextTestRunner().run(selection)
