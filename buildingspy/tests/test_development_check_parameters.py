#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest

class Test_development_check_parameters(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.development.check_parameters.
    """

    def test_validateModelParameters(self):
        import os
        import buildingspy.development.check_parameters as v
        val = v.Validator()
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        val.validateModelParameters(myMoLib)

if __name__ == '__main__':
    unittest.main()

