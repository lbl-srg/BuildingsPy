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


class Test_development_refactor(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.development.refactor.Refactor`.
    """

    def test_sort_package_order(self):
        import random
        import buildingspy.development.refactor as r
        __MOD = 0
        __REC = 1
        __PAC = 2

        o  = [[__PAC, "UsersGuide"],
              [__MOD, "a"],
              [__MOD, "y"],
              [__REC, "a_data"],
              [__PAC, "B"],
              [__PAC, "Z"],
              [__PAC, "Data"],
              [__PAC, "Types"],
              [__PAC, "Examples"],
              [__PAC, "Validation"],
              [__PAC, "Experimental"],
              [__PAC, "Interfaces"],
              [__PAC, "BaseClasses"],
              [__PAC, "Internal"],
              [__PAC, "Obsolete"]]

        random.seed(1)
        for i in range(10):
            # Copy the list to prevent the original list to be modified.
            s = list(o)
            # Shuffle the list randomly.
            random.shuffle(s)
            s = r._sort_package_order(s)
            self.assertEqual(o, s, "Sorting failed with i=%d." % i)
        # Reset the random number generator.
        random.seed()

    def test_write_package_order(self):
        import os
        import buildingspy.development.refactor as r

        package_path = os.path.abspath(os.path.join("buildingspy", "tests", "MyModelicaLibrary"))

        pac_lis = list()
        # The digit 3 is the enumeration for package, e.g, __PAC in refactor
        correct = [[3, "Reset"]]

        pac_lis = r._get_package_list_for_file(package_path, "package.mo")
        self.assertEqual(pac_lis, correct, "Parsing package.order failed.")

    def test_get_modelica_file_name(self):
        import os
        import buildingspy.development.refactor as r
        self.assertEqual( r.get_modelica_file_name("Buildings.Rooms.MixedAir"), \
                os.path.join("Buildings", "Rooms", "MixedAir.mo") )

if __name__ == '__main__':
    unittest.main()
