#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import unittest
import os

# To run this test, navigate to the BuildingsPy folder, then type
# python buildingspy/tests/test_development_regressiontest.py


class Test_regressiontest_openmodelica_Tester(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.regressiontest.Tester` for openmodelica.
    """

    def test_unit_test_return_new_configuration_data_using_CI_results(self):
        import buildingspy.development.regressiontest as r
        tool = 'openmodelica'
        rt = r.Tester(skip_verification=True, check_html=False, tool=tool)

        # Simulation failed in the past, and still fails
        configuration_data = [{'model_name': 'model1', tool:
                               {'comment': 'Model excluded from simulation as it has no solution.',
                                'simulate': False}}]
        simulator_log_file_json = [{'model': 'model1', 'translation': {
            'success': True}, 'simulation': {'success': False}}]
        dat = rt.return_new_configuration_data_using_CI_results(
            configuration_data, simulator_log_file_json, tool)
        self.assertEqual(configuration_data, dat,
                         "Test for failed simulation.")

        # Simulation failed in the past, but now works
        configuration_data = [{'model_name': 'model1', tool: {
            'comment': 'To be removed', 'simulate': False}}]
        simulator_log_file_json = [{'model': 'model1', 'translation': {
            'success': True}, 'simulation': {'success': True}}]
        dat = rt.return_new_configuration_data_using_CI_results(
            configuration_data, simulator_log_file_json, tool)
        self.assertEqual(dat,
                         [],
                         "Test for successful simulation.")

        # Simulation failed in the past, but now works (as above), but now there is another tool
        configuration_data = [{'model_name': 'model1', tool: {
            'comment': 'To be removed', 'simulate': False},
            'other_tool': {
            'comment': 'Simulation failed for some reason.', 'simulate': False}}]
        simulator_log_file_json = [{'model': 'model1', 'translation': {
            'success': True}, 'simulation': {'success': True}}]
        dat = rt.return_new_configuration_data_using_CI_results(
            [{'model_name': 'model1',
              'other_tool': {
                  'comment': 'Simulation failed for some reason.', 'simulate': False}}], simulator_log_file_json, tool)
        self.assertEqual(dat,
                         [{'model_name': 'model1',
                           'other_tool': {
                               'comment': 'Simulation failed for some reason.', 'simulate': False}}],
                         "Test for successful simulation.")

        # Translation failed in the past, and still fails
        configuration_data = [{'model_name': 'model1', tool: {
            'comment': 'Some comment', 'translate': False}}]
        simulator_log_file_json = [{'model': 'model1', 'translation': {
            'success': False}, 'simulation': {'success': False}}]
        dat = rt.return_new_configuration_data_using_CI_results(
            configuration_data, simulator_log_file_json, tool)
        self.assertEqual(dat,
                         configuration_data,
                         "Test for failed translation.")

        # Translation failed in the past, but now works, but simulation fails
        configuration_data = [{'model_name': 'model1', tool: {
            'comment': 'Some comment', 'translate': False}}]
        simulator_log_file_json = [{'model': 'model1', 'translation': {
            'success': True}, 'simulation': {'success': False}}]
        dat = rt.return_new_configuration_data_using_CI_results(
            configuration_data, simulator_log_file_json, tool)
        self.assertEqual(dat,
                         [{'model_name': 'model1',
                           tool: {'simulate': False,
                                  'comment': "Added when auto-updating conf.yml."}}],
                         "Test for successful translation, but still failure in simulation.")

        # Translation failed in the past, but now works, but simulation fails, and
        # reports an exception
        simulator_log_file_json = [{'model': 'model1', 'translation': {'success': True}, 'simulation': {
            'success': False, 'exception': "Exception from simulator."}}]
        dat = rt.return_new_configuration_data_using_CI_results(
            configuration_data, simulator_log_file_json, tool)
        self.assertEqual(dat,
                         [{'model_name': 'model1',
                           tool: {'simulate': False,
                                  'comment': "Exception from simulator."}}],
                         "Test for successful translation, but still failure in simulation.")

        # Translation failed in the past, but now works, and simulation works too
        configuration_data = [{'model_name': 'model1', tool: {
            'comment': 'Some comment', 'translate': False}}]
        simulator_log_file_json = [{'model': 'model1', 'translation': {
            'success': True}, 'simulation': {'success': True}}]
        dat = rt.return_new_configuration_data_using_CI_results(
            configuration_data, simulator_log_file_json, tool)
        self.assertEqual(dat,
                         [],
                         "Test for successful translation and simulation.")

        # Model has no entry in configuration data, but now fails to translate
        configuration_data = [{'model_name': 'AAA', tool: {
            'comment': 'Some comment', 'translate': False}}]
        simulator_log_file_json = [{'model': 'model1', 'translation': {
            'success': False}, 'simulation': {'success': False}}]
        dat = rt.return_new_configuration_data_using_CI_results(
            configuration_data, simulator_log_file_json, tool)
        self.assertEqual(dat,
                         [configuration_data[0],
                          {'model_name': 'model1',
                           tool: {'comment': 'Added when auto-updating conf.yml.',
                                  'translate': False}}],
                         "Test for model that has no entry but fails to translate.")

        # Model has no entry in configuration data, but now fails to simulate
        configuration_data = [{'model_name': 'AAA', tool: {
            'comment': 'Some comment', 'translate': False}}]
        simulator_log_file_json = [{'model': 'model1', 'translation': {
            'success': True}, 'simulation': {'success': False}}]
        dat = rt.return_new_configuration_data_using_CI_results(
            configuration_data, simulator_log_file_json, tool)
        self.assertEqual(dat,
                         [configuration_data[0],
                          {'model_name': 'model1',
                           tool: {'comment': 'Added when auto-updating conf.yml.',
                                  'simulate': False}}],
                         "Test for model that has no entry but fails to simulate.")
        # Same as above, but now there are no previous entries
        # Model has no entry in configuration data, but now fails to translate
        configuration_data = []
        simulator_log_file_json = [{'model': 'model1', 'translation': {
            'success': False}, 'simulation': {'success': False}}]
        dat = rt.return_new_configuration_data_using_CI_results(
            configuration_data, simulator_log_file_json, tool)
        self.assertEqual(dat,
                         [{'model_name': 'model1',
                           tool: {'comment': 'Added when auto-updating conf.yml.',
                                  'translate': False}}],
                         "Test for model that has no entry but fails to translate.")

        # Model has no entry in configuration data, but now fails to simulate
        configuration_data = []
        simulator_log_file_json = [{'model': 'model1', 'translation': {
            'success': True}, 'simulation': {'success': False}}]
        dat = rt.return_new_configuration_data_using_CI_results(
            configuration_data, simulator_log_file_json, tool)
        self.assertEqual(dat,
                         [{'model_name': 'model1',
                           tool: {'comment': 'Added when auto-updating conf.yml.',
                                  'simulate': False}}],
                         "Test for model that has no entry but fails to simulate.")

        # Model has no entry in configuration data, but now fails to simulate (as above),
        # and now, test whether OpenModelica exception is correctly parsed.
        configuration_data = []
        simulator_log_file_json = [{'model': 'model1', 'translation': {'success': True}, 'simulation': {
            'success': False, 'exception': "'omc model_simulate.mos' caused 'simulation terminated'."}}]
        dat = rt.return_new_configuration_data_using_CI_results(
            configuration_data, simulator_log_file_json, tool)
        self.assertEqual(dat,
                         [{'model_name': 'model1',
                           tool: {'comment': 'simulation terminated.',
                                  'simulate': False}}],
                         "Test for model that has no entry but fails to simulate and reports an exception.")

    def test_unit_test_update_configuration_file_existing(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(
            skip_verification=True,
            check_html=False,
            tool="openmodelica",
            rewriteConfigurationFile=True)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.deleteTemporaryDirectories(True)
        rt.setLibraryRoot(myMoLib)
        rt.batchMode(True)
        conf_data = rt.get_configuration_data_from_disk()
        ret_val = rt.run()

        # Assert that the configuration data are still the same
        self.assertEqual(conf_data,
                         rt.get_configuration_data_from_disk(),
                         "Configuration data changed but expected no change.")

        # Delete temporary files
        for f in rt.get_unit_test_log_files():
            if os.path.exists(f):
                os.remove(f)

    def test_unit_test_update_configuration_file_non_existing(self):
        import shutil
        import buildingspy.development.regressiontest as r
        rt = r.Tester(
            skip_verification=True,
            check_html=False,
            tool="openmodelica",
            rewriteConfigurationFile=True)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.deleteTemporaryDirectories(True)
        rt.setLibraryRoot(myMoLib)
        rt.batchMode(True)
        conf_data = rt.get_configuration_data_from_disk()

        # Move the configuration data, and recreate it, and make sure it is the same
        conf_yml_name = rt.get_configuration_file_name()
        conf_backup = "conf.yml.backup"
        shutil.move(conf_yml_name, conf_backup)
        ret_val = rt.run()
        self.assertEqual(
            conf_data,
            rt.get_configuration_data_from_disk(),
            "Newly generated configuration data differ from the one that were on disk. Backup in '{conf_backup}'.")
        # Move file back to preserve its time stamp
        shutil.move(conf_backup, conf_yml_name)

        # Delete temporary files
        for f in rt.get_unit_test_log_files():
            if os.path.exists(f):
                os.remove(f)

    def test_unit_test_log_file(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False, tool="openmodelica")
        self.assertEqual(['comparison-openmodelica.log', 'simulator-openmodelica.log',
                         'unitTests-openmodelica.log'], rt.get_unit_test_log_files())

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
            annotation (experiment(Tolerance=1e-6, StopTime=3600));
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

    def test_regressiontest_diagnostics(self):
        """ Test that warnings and errors reported by openmodelica are reported.
        """
        import shutil
        import buildingspy.development.regressiontest as r

        tests = [
            {'ret_val': 0,
             'mo_content': """parameter Real x = 0;""",
             'description': "Correct model."},
            # Commented, see comment in error_dictionary_openmodelica.py
            # {'ret_val': 2,
            # 'mo_content': """parameter Real x(each unit="m") = 0;""",
            # 'description': "Wrong each on scalar."},
            # {'ret_val': 2,
            # 'mo_content': """Modelica.Blocks.Sources.Constant b(each k=0) ;""",
            # 'description': "Wrong each on scalar component."},
            {'ret_val': 1,
             'mo_content': """Modelica.Blocks.Sources.Constant b[2](k=0) ;""",
             'description': "Missing each on array of components."},
            {'ret_val': 0,
             'mo_content': """
                              Real x;
                              equation
                              Modelica.Math.exp(x)=1;""",
             'description': "Missing start value, which should be ignored."},
            {'ret_val': 0,
             'mo_content': """
                              Real x(start=0);
                              equation
                              der(x)^3 = 0;""",
             'description': "Missing start value for der(x), which should be ignored."},
            {'ret_val': 1,
             'mo_content': """parameter Real[2] x(unit="m") = {0, 0};
                                    parameter Real y(each unit="m") = 0;""",
             'description': "Two errors."},
            {'ret_val': 1,
             'mo_content': """x; """,
             'description': "Syntax error that should cause a failure in translation."},
            {'ret_val': 1,
             'mo_content': """Real x(start=0);
                                    equation
                                      Modelica.Math.exp(x)=-1;""",
             'description': "Model that has no solution."}
        ]
        # Run all test cases
        for test in tests:
            des = test['description']
            print("*** Running test for '{}'".format(des))
            mo_content = test['mo_content']
            dir_name = self._write_test(mo_content)
            rt = r.Tester(skip_verification=True, check_html=False, tool="openmodelica")
            rt.setLibraryRoot(dir_name)
            rt.deleteTemporaryDirectories(True)

#                # This test must raise an exception
#                self.assertRaises(ValueError,
#                    rt.setLibraryRoot, "this_is_not_the_root_dir_of_a_library")
#

            ret_val = rt.run()
            # Check return value to see if test succeeded
            self.assertEqual(
                test['ret_val'],
                ret_val,
                f"Test for '{des}' failed, return value {ret_val}, expected {test['ret_val']}")
            # Get parent dir of dir_name, because dir_name contains the Modelica library name
            par = os.path.split(dir_name)[0]
            for f in rt.get_unit_test_log_files():
                if os.path.exists(f):
                    os.remove(f)
            shutil.rmtree(par)

    def _run_regression_test(self, skip_verification):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(skip_verification=skip_verification, check_html=False, tool="openmodelica")
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.deleteTemporaryDirectories(True)
        rt.setLibraryRoot(myMoLib)
        rt.batchMode(True)
        ret_val = rt.run()
        # Check return value to see if test was successful
        self.assertEqual(0, ret_val, "Test failed with return value {}".format(ret_val))
        # Delete temporary files
        for f in rt.get_unit_test_log_files():
            if os.path.exists(f):
                os.remove(f)

    def test_regressiontest(self):
        self._run_regression_test(skip_verification=True)

    def test_regressiontest_with_verification(self):
        self._run_regression_test(skip_verification=False)


if __name__ == '__main__':
    unittest.main()
    #t = Test_regressiontest_openmodelica_Tester()
    # t.test_unit_test_return_new_configuration_data_using_CI_results()
    # t.test_unit_test_update_configuration_file_existing()
    # t.test_unit_test_update_configuration_file_non_existing()
