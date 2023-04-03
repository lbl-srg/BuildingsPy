#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
from multiprocessing import Pool

from buildingspy.simulate.Dymola import Simulator


# Function to set common parameters and to run the simulation
def simulateCase(s):
    """ Set common parameters and run a simulation.

    :param s: A simulator object.

    """
    s.setStopTime(24*3600)
    # Kill the process if it does not finish in 1 minute
    s.setTimeOut(60)
    s.printModelAndTime()
    s.simulate()


def main():
    """ Main method that configures and runs all simulations
    """
    import shutil

    # Build list of cases to run
    li = []
    # First model, from Modelica Buildings Library, v9.1.0
    model = 'Buildings.Fluid.SolarCollectors.Examples.FlatPlateWithTank'
    s = Simulator(model, outputDirectory='case1')
    s.addParameters({'tan.VTan': 1.5})
    li.append(s)
    # second model
    s = Simulator(model, outputDirectory='case2')
    s.addParameters({'tan.VTan': 2})
    li.append(s)

    # Run all cases in parallel
    po = Pool()
    po.map(simulateCase, li)
    po.close()
    po.join()

    # Clean up
    #shutil.rmtree('case1')
    #shutil.rmtree('case2')


# Main function
if __name__ == '__main__':
    main()
