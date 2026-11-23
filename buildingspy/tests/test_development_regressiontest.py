#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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

    def _run_regression_test(self, skip_verification, single_class=None):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(skip_verification=skip_verification, check_html=False, tool="dymola")
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.deleteTemporaryDirectories(True)
        rt.setLibraryRoot(myMoLib)
        if single_class is not None:
            rt.setSingleClass(single_class)
        rt.batchMode(True)
        ret_val = rt.run()
        # Check return value to see if test succeeded
        self.assertEqual(0, ret_val, "Test failed with return value {}".format(ret_val))
        # Delete temporary files
        for f in rt.get_unit_test_log_files():
            if os.path.exists(f):
                os.remove(f)

    def test_regressiontest(self):
        self._run_regression_test(skip_verification=True)

    def test_regressiontest_with_verification(self):
        self._run_regression_test(skip_verification=False)

    def test_regressiontest_single_class(self):
        for single_class in [
            "MyModelicaLibrary.Examples.BooleanParameters",
            "MyModelicaLibrary.Examples.BooleanParameters,MyModelicaLibrary.Examples.Constants",
            "MyModelicaLibrary.Examples.{BooleanParameters,Constants}",
            "MyModelicaLibrary.Examples.BooleanParameters,MyModelicaLibrary.Examples.FMUs",
            "MyModelicaLibrary.Examples.FMUs",
            "MyModelicaLibrary.Examples.FMUs,MyModelicaLibrary.Obsolete.Examples",
        ]:
            self._run_regression_test(skip_verification=False, single_class=single_class)

    def test_unit_test_log_file(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False, tool="dymola")
        self.assertEqual(['comparison-dymola.log', 'simulator-dymola.log',
                         'unitTests-dymola.log'], rt.get_unit_test_log_files())

    def test_regressiontest_invalid_package(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        # Verify that invalid packages raise a ValueError.
        with self.assertWarns(DeprecationWarning):
            self.assertRaises(ValueError, rt.setSinglePackage, "this.package.does.not.exist")
        with self.assertRaises(ValueError) as context:
            rt.setSingleClass("this.class.does.not.exist")
        moDir = os.path.abspath(os.path.join(myMoLib, "class", "does", "not", "exist"))
        moFil = moDir + ".mo"
        self.assertEqual(
            str(context.exception),
            "Requested to test only class 'this.class.does.not.exist', but neither directory\n"
            f"'{moDir}' nor file '{moFil}' exists."
        )

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
        with self.assertWarns(DeprecationWarning):
            rt.setSinglePackage("MyModelicaLibrary.Examples.FMUs")
        self.assertEqual(3, rt.get_number_of_tests())

    def test_setSinglePackage_2(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.include_fmu_tests(True)
        with self.assertWarns(DeprecationWarning):
            rt.setSinglePackage("MyModelicaLibrary.Examples")
        self.assertEqual(7, rt.get_number_of_tests())

    def test_setSinglePackage_3(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.include_fmu_tests(True)
        with self.assertWarns(DeprecationWarning):
            rt.setSinglePackage("MyModelicaLibrary.Examples.FMUs,MyModelicaLibrary.Examples")
        self.assertEqual(7, rt.get_number_of_tests())

    def test_setSinglePackage_4(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.include_fmu_tests(True)
        with self.assertWarns(DeprecationWarning):
            rt.setSinglePackage("MyModelicaLibrary.Examples,MyModelicaLibrary.Examples.FMUs")
        self.assertEqual(7, rt.get_number_of_tests())

    def test_setSingleClass(self):
        import buildingspy.development.regressiontest as r
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        for class_name, n_tests in [
            # Single model
            ("MyModelicaLibrary.Examples.BooleanParameters", 1),
            # Two models
            ("MyModelicaLibrary.Examples.BooleanParameters,MyModelicaLibrary.Examples.Constants", 2),
            ("MyModelicaLibrary.Examples.{BooleanParameters,Constants}", 2),
            ("MyModelicaLibrary.Examples.FMUs.Gain,MyModelicaLibrary.Examples.FMUs.IntegratorGain", 2),
            # A model and a class (package)
            ("MyModelicaLibrary.Examples.BooleanParameters,MyModelicaLibrary.Examples.FMUs", 4),
            ("MyModelicaLibrary.Examples.FMUs,MyModelicaLibrary.Examples.BooleanParameters", 4),
            ("MyModelicaLibrary.Examples.BooleanParameters,MyModelicaLibrary.Examples", 7),
            ("MyModelicaLibrary.Examples,MyModelicaLibrary.Examples.BooleanParameters", 7),
            # A class (package)
            ("MyModelicaLibrary.Examples.FMUs", 3),
            ("MyModelicaLibrary.Examples", 7),
            # Two classes (packages)
            ("MyModelicaLibrary.Examples.FMUs,MyModelicaLibrary.Obsolete.Examples", 4),
            ("MyModelicaLibrary.Examples.FMUs,MyModelicaLibrary.Examples", 7),
            ("MyModelicaLibrary.Examples,MyModelicaLibrary.Examples.FMUs", 7),
        ]:
            rt = r.Tester(check_html=False)
            rt.setLibraryRoot(myMoLib)
            rt.include_fmu_tests(True)
            rt.setSingleClass(class_name)
            self.assertEqual(n_tests, rt.get_number_of_tests(), f"Failed for {class_name}")

    def test_areResultsEqual(self):
        """Test legacy comparison tool."""
        import buildingspy.development.regressiontest as r
        rt = r.Tester(comp_tool='legacy')
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
        # Zeros are ignored
        self.assertTrue(rt.are_statistics_equal("1, 40", "1, 40, 0"))
        self.assertTrue(rt.are_statistics_equal("1, 0, 0, 40", "1, 40, 0"))

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

    def test_set_data_attributes_from_mos(self):
        import buildingspy.development.regressiontest as r

        content = """
        simulateModel("MyModel.Name");
        """
        data, err = r.Tester._set_data_attributes_from_mos(mos_content=content)
        expected_result = {'dymola':
                           {'exportFMU': False,
                            'translate': True,
                            'simulate': True,
                            'TranslationLogFile': 'MyModel.Name.translation.log'},
                           'model_name': 'MyModel.Name',
                           'startTime': 0,
                           'stopTime': 1}
        self.assertIsNone(err, f"Received unexpected error: {err}")
        self.assertDictEqual(data, expected_result, "Failed to parse model name.")

        # Test parsing with line breaks and spaces
        for content in [
            """simulateModel("MyModel.Name")
        """,
            """
        simulateModel(
            "MyModel.Name");
        """,
            """
        simulateModel( "MyModel.Name" );
        """
        ]:
            data, err = r.Tester._set_data_attributes_from_mos(mos_content=content)
            self.assertEqual(data, {**data, **{"model_name": "MyModel.Name"}},
                             f"Failed to parse line ending in content='{content}'.")

        # Test parsing of time
        for content in [
            """simulateModel("MyModel.Name",
          startTime=1)""",
            """simulateModel("MyModel.Name", startTime=1)""",
            """simulateModel("MyModel.Name",startTime=1)""",
            """simulateModel("MyModel.Name", startTime = 1)""",
            """simulateModel("MyModel.Name", startTime = 1 )""",
            """simulateModel("MyModel.Name", startTime=+1)""",
            """simulateModel("MyModel.Name", startTime=1e0)""",
            """simulateModel("MyModel.Name", startTime=1e+0)""",
            """simulateModel("MyModel.Name", startTime=1.00e+00)""",
            """simulateModel("MyModel.Name", startTime=1.00e-00)""",
            """simulateModel("MyModel.Name",
          startTime=1e+0)"""
        ]:
            data, err = r.Tester._set_data_attributes_from_mos(mos_content=content)
            self.assertEqual(data, {**data, **{"startTime": 1}},
                             f"Failed to parse startTime in content='{content}'.")

        content = """
            translateModelFMU(
                modelToOpen="MyModelicaLibrary.Examples.MyModel",
                storeResult=false,
                modelName="",
                fmiVersion="2",
                fmiType="me",
                includeSource=false);
                 """
        data, err = r.Tester._set_data_attributes_from_mos(mos_content=content)

        expected_result = {
            'dymola': {
                'translate': False,
                'simulate': False,
                'exportFMU': True,
                'modelToOpen': 'MyModelicaLibrary.Examples.MyModel',
                'modelName': 'MyModelicaLibrary.Examples.MyModel'
            }
        }

        self.assertIsNone(err, f"Received unexpected error: {err}")
        self.assertDictEqual(data, expected_result, "Failed to parse model name.")

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

    def test_get_coverage_single_package(self):
        coverage_result = self._test_get_and_print_coverage(package="Examples")
        self.assertEqual(coverage_result[0], 88)
        self.assertEqual(coverage_result[1], 7)
        self.assertEqual(coverage_result[2], 8)
        self.assertTrue(coverage_result[3][0].endswith("ParameterEvaluation.mo"))
        self.assertEqual(coverage_result[4], ["Examples"])

    def test_get_coverage_all_packages(self):
        coverage_result = self._test_get_and_print_coverage(package=None)
        self.assertEqual(coverage_result[0], 89)
        self.assertEqual(coverage_result[1], 8)
        self.assertEqual(coverage_result[2], 9)
        self.assertEqual(len(coverage_result[3]), 1)
        self.assertEqual(len(coverage_result[4]), 2)

    def _test_get_and_print_coverage(self, package: str = None):
        import buildingspy.development.regressiontest as r
        ut = r.Tester(tool='dymola')
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        ut.setLibraryRoot(myMoLib)
        if package is not None:
            ut.setSingleClass(package)
        coverage_result = ut.getCoverage()
        self.assertIsInstance(coverage_result, tuple)
        self.assertIsInstance(coverage_result[0], float)
        self.assertIsInstance(coverage_result[1], int)
        self.assertIsInstance(coverage_result[2], int)
        self.assertIsInstance(coverage_result[3], list)
        self.assertIsInstance(coverage_result[4], list)
        # Check print with both custom and standard printer
        ut.printCoverage(*coverage_result, printer=print)
        ut.printCoverage(*coverage_result)
        return coverage_result

    def test_checkReferencePoints_batch_mode(self):
        import shutil
        from unittest.mock import patch
        import buildingspy.development.regressiontest as r

        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        y_sim = [{"time": [0.0, 1.0], "p1": [0.0, 0.0], "p2": [2.0, 2.0]}]
        y_tra = {"simulation": {"numerical Jacobians": "0", "nonlinear": " ", "linear": " "}}

        for comp_tool in ["funnel", "legacy"]:
            for batch, ans, expect_plot in [
                (True, "N", False),
                (True, "-", False),
                (False, "N", False),
                (False, "Y", False),
                (False, "-", True),
            ]:
                rt = r.Tester(check_html=False, comp_tool=comp_tool)
                rt.setLibraryRoot(myMoLib)
                rt.setSingleClass("MyModelicaLibrary.Examples.BooleanParameters")
                rt.batchMode(batch)
                rt._comp_info = [{"model": rt._data[0]["model_name"]}]
                try:
                    with patch.object(rt, "_getSimulationResults", return_value=y_sim), \
                            patch.object(rt, "_getDymolaTranslationStatistics", return_value=y_tra), \
                            patch.object(rt, "_writeReferenceResults"), \
                            patch.object(rt, "_funnel_plot") as mock_funnel_plot, \
                            patch.object(rt, "_legacy_plot") as mock_legacy_plot, \
                            patch("builtins.input", return_value="n") as mock_input:
                        rt._checkReferencePoints(ans=ans)
                        self.assertEqual(
                            mock_funnel_plot.call_count,
                            1 if (expect_plot and comp_tool == "funnel") else 0)
                        self.assertEqual(
                            mock_legacy_plot.call_count,
                            1 if (expect_plot and comp_tool == "legacy") else 0)
                        self.assertEqual(mock_input.call_count, 1 if expect_plot else 0)
                finally:
                    if rt._comp_dir and os.path.exists(rt._comp_dir):
                        shutil.rmtree(rt._comp_dir)
                    for f in rt.get_unit_test_log_files():
                        if os.path.exists(f):
                            os.remove(f)

    def test_reference_mismatch_prints_model_name(self):
        import io
        import shutil
        from contextlib import redirect_stderr, redirect_stdout
        from unittest.mock import patch
        import buildingspy.development.regressiontest as r

        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        model_name = "MyModelicaLibrary.Examples.BooleanParameters"
        ref_txt = "MyModelicaLibrary_Examples_BooleanParameters.txt"
        y_sim = [{"time": [0.0, 1.0], "p1": [0.0, 0.0], "p2": [2.0, 2.0]}]
        y_tra = {"simulation": {"numerical Jacobians": "0", "nonlinear": " ", "linear": " "}}

        # 1. Trajectory mismatch in batch and interactive modes
        for comp_tool in ["funnel", "legacy"]:
            for batch in [True, False]:
                rt = r.Tester(check_html=False, comp_tool=comp_tool)
                rt.setLibraryRoot(myMoLib)
                rt.setSingleClass(model_name)
                rt.batchMode(batch)
                rt._comp_info = [{"model": model_name}]
                out_buf, err_buf = io.StringIO(), io.StringIO()
                try:
                    with patch.object(rt, "_getSimulationResults", return_value=y_sim), \
                            patch.object(rt, "_getDymolaTranslationStatistics", return_value=y_tra), \
                            patch.object(rt, "_writeReferenceResults"), \
                            patch.object(rt, "_funnel_plot"), \
                            patch.object(rt, "_legacy_plot"), \
                            patch("builtins.input", return_value="n"), \
                            redirect_stdout(out_buf), \
                            redirect_stderr(err_buf):
                        rt._checkReferencePoints(ans="N" if batch else "-")
                    stdout_val = out_buf.getvalue()
                    stderr_val = err_buf.getvalue()
                    with open("unitTests-dymola.log", "r", encoding="utf-8") as log_fil:
                        log_val = log_fil.read()
                    self.assertIn(f"{model_name}: Errors during result verification.", stderr_val)
                    self.assertIn(f"{model_name}: Errors during result verification.", log_val)
                    self.assertNotIn(ref_txt, stderr_val)
                    self.assertNotIn(ref_txt, stdout_val)
                    self.assertNotIn(ref_txt, log_val)
                    if not batch:
                        self.assertIn(f"For {model_name},", stdout_val)
                finally:
                    if rt._comp_dir and os.path.exists(rt._comp_dir):
                        shutil.rmtree(rt._comp_dir)
                    for f in rt.get_unit_test_log_files():
                        if os.path.exists(f):
                            os.remove(f)

        # 2. Old reference file has no simulation results
        rt = r.Tester(check_html=False)
        rt.setLibraryRoot(myMoLib)
        rt.setSingleClass(model_name)
        rt._comp_info = [{"model": model_name}]
        out_buf, err_buf = io.StringIO(), io.StringIO()
        try:
            with patch.object(rt, "_getSimulationResults", return_value=y_sim), \
                    patch.object(rt, "_getDymolaTranslationStatistics", return_value=y_tra), \
                    patch.object(rt, "_readReferenceResults", return_value={"results": {}}), \
                    patch.object(rt, "_writeReferenceResults"), \
                    patch("builtins.input", return_value="n"), \
                    redirect_stdout(out_buf), \
                    redirect_stderr(err_buf):
                rt._checkReferencePoints(ans="-")
            stdout_val = out_buf.getvalue()
            self.assertIn(f"for {model_name}", stdout_val)
            self.assertNotIn(ref_txt, stdout_val)
            self.assertNotIn(ref_txt, err_buf.getvalue())
        finally:
            if rt._comp_dir and os.path.exists(rt._comp_dir):
                shutil.rmtree(rt._comp_dir)
            for f in rt.get_unit_test_log_files():
                if os.path.exists(f):
                    os.remove(f)

        # 3. FMU statistics mismatch and missing FMU statistics in reference results
        fmu_model = "MyModelicaLibrary.Examples.FMUs.Gain"
        fmu_ref_txt = "MyModelicaLibrary_Examples_FMUs_Gain.txt"
        dep_diff = {"InitialUnknowns": {}, "Outputs": {}, "Derivatives": {}}
        for mock_old_dep in [None, {"results": {}}]:
            rt = r.Tester(check_html=False)
            rt.setLibraryRoot(myMoLib)
            rt.setSingleClass(fmu_model)
            rt._data[0]["ResultDirectory"] = "dummy"
            out_buf, err_buf = io.StringIO(), io.StringIO()
            try:
                read_ctx = (
                    patch.object(rt, "_readReferenceResults", return_value=mock_old_dep)
                    if mock_old_dep is not None
                    else redirect_stdout(out_buf)
                )
                with patch("buildingspy.fmi.get_dependencies", return_value=dep_diff), \
                        read_ctx, \
                        redirect_stdout(out_buf), \
                        redirect_stderr(err_buf):
                    rt._check_fmu_statistics(ans="N")
                stderr_val = err_buf.getvalue()
                with open("unitTests-dymola.log", "r", encoding="utf-8") as log_fil:
                    log_val = log_fil.read()
                self.assertIn(fmu_model, stderr_val)
                self.assertIn(fmu_model, log_val)
                self.assertNotIn(fmu_ref_txt, stderr_val)
                self.assertNotIn(fmu_ref_txt, out_buf.getvalue())
                self.assertNotIn(fmu_ref_txt, log_val)
            finally:
                for f in rt.get_unit_test_log_files():
                    if os.path.exists(f):
                        os.remove(f)


if __name__ == '__main__':
    unittest.main()
