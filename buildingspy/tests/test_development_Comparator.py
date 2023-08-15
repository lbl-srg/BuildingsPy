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

    def test_tools(self):
        import buildingspy.development.simulationCompare as sc
        import shutil

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
        self.assertIsFile(os.path.join("results", "html", "tools_compare_master.html"))
        shutil.rmtree("results")
        for tool in tools:
            shutil.rmtree(tool)


if __name__ == '__main__':
    unittest.main()
