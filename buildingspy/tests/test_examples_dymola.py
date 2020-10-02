#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import unittest

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
        self._buiDir = None

    def setUp(self):
        """ Ensure that environment variables that are needed to run
            the tests are set
        """
        from git import Repo
        import tempfile
        import os
        import shutil

        self.env = EnvironmentVarGuard()

        self._temDir = tempfile.mkdtemp(prefix='tmp-BuildingsPy-Modelica-Lib-')
        self._buiDir = os.path.join(os.getcwd(), "Buildings")

        clo_dir = os.path.join(os.getcwd(), "tmp")

        if os.path.exists(clo_dir):
            shutil.rmtree(clo_dir)

        Repo.clone_from("https://github.com/lbl-srg/modelica-buildings.git",
                        clo_dir, depth=1)

        if os.path.exists(os.path.join(os.getcwd(), "Buildings")):
            shutil.rmtree(os.path.join(os.getcwd(), "Buildings"))
        shutil.move(os.path.join(os.getcwd(), "tmp", "Buildings"),
                    self._buiDir)
        shutil.rmtree(clo_dir)

    def tearDown(self):
        """ Method called after all the tests.
        """
        # Delete temporary directory
        import shutil
        import os
        shutil.rmtree(self._buiDir)

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
