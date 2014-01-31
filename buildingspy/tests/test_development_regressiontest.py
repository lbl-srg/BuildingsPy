#!/usr/bin/env python
import unittest
from buildingspy.development.regressiontest import Tester

class Test_regressiontest_Tester(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.regressiontest.Tester`.
    """

    def test_regressiontest(self):
        import os
        import buildingspy.development.regressiontest as r
        rt = r.Tester()
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.run()
        # Delete temporary files
        os.remove('dymola.log')
        os.remove('unitTests.log')

if __name__ == '__main__':
    unittest.main()
