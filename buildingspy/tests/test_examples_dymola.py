#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import unittest


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
        import tempfile
        import os
        import shutil
        import requests
        import zipfile
        from io import BytesIO

        self._temDir = tempfile.mkdtemp(prefix='tmp-BuildingsPy-Modelica-Lib-')
        self._buiDir = os.path.join(os.getcwd(), "Buildings")

        zip_file_url = "https://github.com/lbl-srg/modelica-buildings/archive/refs/tags/v11.0.0.zip"

        r = requests.get(zip_file_url)
        # Split URL to get the file name
        zip_file = zip_file_url.split('/')[-1]
        # Writing the file to the local file system
        with open(zip_file, 'wb') as output_file:
            output_file.write(r.content)
        z = zipfile.ZipFile(BytesIO(r.content))
        z.extractall()
        shutil.move(os.path.join("modelica-buildings-11.0.0", "Buildings"), "Buildings")
        shutil.rmtree("modelica-buildings-11.0.0")

    def tearDown(self):
        """ Method called after all the tests.
        """
        # Delete temporary directory
        import shutil
        import os
        shutil.rmtree(self._buiDir)
        zipFil = "v11.0.0.zip"
        if os.path.exists(zipFil):
            os.remove(zipFil)

    def test_runSimulation(self):
        """
        Tests the :mod:`buildingspy/examples/dymola/runSimulation`
        function.
        """
        import os
        import buildingspy.examples.dymola.runSimulation as s
        s.main()

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
