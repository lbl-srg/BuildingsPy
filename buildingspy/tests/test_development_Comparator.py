#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import json
import os
import shutil
import unittest


class Test_development_Comparator(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.development.Comparator`.
    """

    def assertIsFile(self, path):
        import pathlib as pl
        if not pl.Path(path).resolve().is_file():
            raise AssertionError("File does not exist: %s" % str(path))

    def setUp(self):
        shutil.rmtree("results", ignore_errors=True)
        for tool in ['dymola', 'openmodelica']:
            shutil.rmtree(tool, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree("results", ignore_errors=True)
        for tool in ['dymola', 'openmodelica']:
            shutil.rmtree(tool, ignore_errors=True)

    def test_merge_iteration_logs(self):
        import buildingspy.development.simulationCompare as sc

        run1 = [
            {"model": "A", "simulation": {"elapsed_time": 1.0, "jacobians": 10, "state_events": 5, "success": True}},
            {"model": "B", "simulation": {"elapsed_time": 2.0, "jacobians": 20, "state_events": 8, "success": True}},
        ]
        run2 = [
            {"model": "A", "simulation": {"elapsed_time": 3.0, "jacobians": 10, "state_events": 5, "success": True}},
            {"model": "B", "simulation": {"elapsed_time": 4.0, "jacobians": 20, "state_events": 8, "success": True}},
        ]
        merged = sc.Comparator._merge_iteration_logs([run1, run2])
        # Model A: avg=(1+3)/2=2.0, min=1.0, max=3.0
        self.assertAlmostEqual(merged[0]["simulation"]["elapsed_time"], 2.0)
        self.assertAlmostEqual(merged[0]["simulation"]["elapsed_time_min"], 1.0)
        self.assertAlmostEqual(merged[0]["simulation"]["elapsed_time_max"], 3.0)
        # Model B: avg=(2+4)/2=3.0, min=2.0, max=4.0
        self.assertAlmostEqual(merged[1]["simulation"]["elapsed_time"], 3.0)
        self.assertAlmostEqual(merged[1]["simulation"]["elapsed_time_min"], 2.0)
        self.assertAlmostEqual(merged[1]["simulation"]["elapsed_time_max"], 4.0)
        # Jacobians and state_events come from first run (unchanged)
        self.assertEqual(merged[0]["simulation"]["jacobians"], 10)
        self.assertEqual(merged[0]["simulation"]["state_events"], 5)
        # nSim=1: min==max==avg
        merged1 = sc.Comparator._merge_iteration_logs([run1])
        self.assertAlmostEqual(merged1[0]["simulation"]["elapsed_time"], 1.0)
        self.assertAlmostEqual(merged1[0]["simulation"]["elapsed_time_min"], 1.0)
        self.assertAlmostEqual(merged1[0]["simulation"]["elapsed_time_max"], 1.0)

    def test_post_process(self):
        import buildingspy.development.simulationCompare as sc

        tools = ['dymola', 'openmodelica']
        branch = 'master'
        model_log = [
            {"model": "Pkg.M1", "simulation": {
                "elapsed_time": 1.5, "elapsed_time_min": 1.2, "elapsed_time_max": 1.8,
                "jacobians": 10, "state_events": 4, "success": True,
                "start_time": 0, "final_time": 1}},
        ]
        for tool in tools:
            d = os.path.join(tool, branch)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, f"comparison-{tool}.log"), "w") as f:
                json.dump(model_log, f)
            with open(os.path.join(d, "commit.log"), "w") as f:
                f.write("abc123def456")

        s = sc.Comparator(
            tools=tools,
            branches=[branch],
            package="Pkg",
            repo="https://example.com/repo")
        s.post_process()

        html_file = os.path.join("results", "html",
                                 f"compare_{branch}--{tools[0]}-{tools[1]}.html")
        self.assertIsFile(html_file)
        with open(html_file) as f:
            content = f.read()
        self.assertIn("Average simulation time", content)
        self.assertIn("[min, max]", content)
        self.assertIn("t<sub>2</sub>", content)

    def test_tools(self):
        import buildingspy.development.simulationCompare as sc

        repo = "https://github.com/ibpsa/modelica-ibpsa"
        tools = ['dymola', 'openmodelica']

        s = sc.Comparator(
            tools=tools,
            branches=['master'],
            package="IBPSA.Utilities.Psychrometrics.Examples",
            repo=repo,
            nSim=2,
            skip_verification=True)

        s.run()
        s.post_process()
        # Make sure output file exists
        self.assertIsFile(
            os.path.join(
                "results",
                "html",
                "compare_master--dymola-openmodelica.html"))


if __name__ == '__main__':
    unittest.main()
