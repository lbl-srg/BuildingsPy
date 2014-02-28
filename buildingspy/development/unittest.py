#!/usr/bin/env python
#######################################################
# Script that runs all regression tests.
#
#
# MWetter@lbl.gov                            2011-02-23
#######################################################
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
