#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import os

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
        import shutil
        shutil.rmtree("results", ignore_errors=True)
        for tool in ['dymola', 'openmodelica']:
            shutil.rmtree(tool, ignore_errors=True)

    def tearDown(self):
        import shutil
        shutil.rmtree("results", ignore_errors=True)
        for tool in ['dymola', 'openmodelica']:
            shutil.rmtree(tool, ignore_errors=True)

    def test_tools(self):
        import buildingspy.development.simulationCompare as sc

        repo = "https://github.com/ibpsa/modelica-ibpsa"
        tools = ['dymola', 'openmodelica']

        s = sc.Comparator(
            tools=tools,
            branches=['master'],
            package="IBPSA.Utilities.Psychrometrics.Examples",
            repo=repo)

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
