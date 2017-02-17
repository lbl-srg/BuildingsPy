#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################
# Script that runs all regression tests.
#
#
# MWetter@lbl.gov                            2011-02-23
#######################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from io import open

import buildingspy.development.regressiontest

class Tester(buildingspy.development.regressiontest.Tester):
    ''' Class that runs all regression tests using Dymola.

    .. note: This is added for backward compatibility.
             Use :mod:`~buildingspy.development.regressiontest`
             instead of `unittest`.

'''
    def __init__(self):
        ''' Constructor.
        '''
        buildingspy.development.regressiontest.Tester.__init__(self)
        s = "buildingspy.development.unittest is deprecated.\n" \
            "Use buildingspy.development.regressiontest instead of unittest.\n"
        self._reporter.writeWarning(s)
