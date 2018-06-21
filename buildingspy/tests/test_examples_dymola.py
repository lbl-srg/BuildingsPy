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
import sys
print(sys.path)

try:
    from test.test_support import EnvironmentVarGuard
except ImportError:
    from test.support import EnvironmentVarGuard


class Test_example_dymola_runSimulation(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.examples`.
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor.
        """
        super(Test_example_dymola_runSimulation, self).__init__(*args, **kwargs)

        self._temDir = None

    def setUp(self):
        """ Ensure that environment variables that are needed to run
            the tests are set
        """
        # Set MODELICALIBRARY which is required to run
        # runSimulationTranslated.py
        from git import Repo
        import tempfile
        import os
        import shutil

        self.env = EnvironmentVarGuard()

        self._temDir = tempfile.mkdtemp(prefix='tmp-BuildingsPy-Modelica-Lib-')

        if not os.path.exists(os.path.join(os.getcwd(), "tmp")):
            clo_dir = os.path.join(os.getcwd(), "tmp")
            if os.path.exists(clo_dir):
                shutil.rmtree(clo_dir)
            Repo.clone_from("https://github.com/lbl-srg/modelica-buildings.git",
                            clo_dir, depth=1)

            if os.path.exists(os.path.join(os.getcwd(), "Buildings")):
                shutil.rmtree(os.path.join(os.getcwd(), "Buildings"))
            shutil.move(os.path.join(os.getcwd(), "tmp", "Buildings"),
                        os.path.join(os.getcwd()))

    def tearDown(self):
        """ Method called after all the tests.
        """
        # Delete temporary directory
        import shutil
        import os
        shutil.rmtree(os.path.join(os.getcwd(), "Buildings"))
        shutil.rmtree(os.path.join(os.getcwd(), "tmp"))

    def test_runSimulation(self):
        """
        Tests the :mod:`buildingspy/examples/dymola/runSimulation`
        function.
        """
        import os
        import buildingspy.examples.dymola.runSimulation as s

        os.chdir("Buildings")
        s.main()
        os.chdir("..")

    def test_runSimulationTranslated(self):
        """
        Tests the :mod:`buildingspy/examples/dymola/runSimulationTranslated`
        function.
        """
        import os
        import buildingspy.examples.dymola.runSimulationTranslated as s

        os.chdir("Buildings")
        s.main()
        os.chdir("..")

    def test_plotResult(self):
        """
        Tests the :mod:`buildingspy/examples/dymola/plotResult`
        function.
        """
        import os
        import buildingspy.examples.dymola.plotResult as s
        s.main()
        # Remove the generated plot files
        os.remove("plot.pdf")
        os.remove("plot.png")


if __name__ == '__main__':
    unittest.main()
