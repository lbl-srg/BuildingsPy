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

from multiprocessing import Pool
import buildingspy.simulate.Simulator as si


# Function to set common parameters and to run the simulation
def simulateCase(s):
    """ Set common parameters and run a simulation.

    :param s: A simulator object.

    """
    s.setStopTime(86400)
    # Kill the process if it does not finish in 1 minute
    s.setTimeOut(60)
    s.showProgressBar(False)
    s.printModelAndTime()
    s.simulate()


def main():
    """ Main method that configures and runs all simulations
    """
    import shutil
    # Build list of cases to run
    li = []
    # First model
    model = 'Buildings.Controls.Continuous.Examples.PIDHysteresis'
    s = si.Simulator(model, 'dymola', 'case1')
    s.addParameters({'con.eOn': 0.1})
    li.append(s)
    # second model
    s = si.Simulator(model, 'dymola', 'case2')
    s.addParameters({'con.eOn': 1})
    li.append(s)

    # Run all cases in parallel
    po = Pool()
    po.map(simulateCase, li)

    # Clean up
    shutil.rmtree('case1')
    shutil.rmtree('case2')


# Main function
if __name__ == '__main__':
    main()
