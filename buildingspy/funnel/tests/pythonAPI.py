#!/usr/bin/env python
#######################################################
# Script that runs the funnel software with a python
# binding.
#######################################################

if __name__ == "__main__":
    import sys
    # Add directory where pyfunnel.py is to search path
    sys.path.append('../bin')

    import pyfunnel as pf

    nReference = 6
    nTest = 6
    tReference = range(0, nReference)
    yReference = [0., 0., 1., 1., 0., 0.]
    tTest = range(0, nTest)
    yTest = [0, 0, 1.1, 1, 0, 0]
    outputDirectory = 'testPython'
    atolx = 0
    atoly = 0
    rtolx = 0.002
    rtoly = 0.002

    pf.compareAndReport(
        tReference,
        yReference,
        tTest,
        yTest,
        outputDirectory,
        atolx,
        atoly,
        rtolx,
        rtoly)
