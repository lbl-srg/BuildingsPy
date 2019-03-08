#!/usr/bin/env python
#######################################################
# Script that runs the funnel software with a python
# binding.
#######################################################
from ctypes import *

def compareAndReport(
    tReference,
    yReference,
    tTest,
    yTest,
    outputDirectory,
    atolx,
    atoly,
    rtolx,
    rtoly):

    import os

    lib = cdll.LoadLibrary(
        os.path.join(os.path.dirname(__file__), "..", "lib64/libfunnel.so"))

    lib.compareAndReport.argtypes = [
        POINTER(c_double),
        POINTER(c_double),
        c_int,
        POINTER(c_double),
        POINTER(c_double),
        c_int,
        c_char_p,
        c_double,
        c_double,
        c_double,
        c_double]
    lib.compareAndReport.restype = c_int

    nReference = len(tReference)
    nTest = len(tTest)

    # Check arguments
    if (nReference != len(yReference)):
        raise ValueError("tReference and yReference must have the same length.")
    if (nTest != len(yTest)):
        raise ValueError("tTest and yTest must have the same length.")

    retVal = lib.compareAndReport(
        (c_double * len(tReference))(*tReference),
        (c_double * len(yReference))(*yReference),
        nReference,
        (c_double * len(tTest))(*tTest),
        (c_double * len(yTest))(*yTest),
        nTest,
        outputDirectory,
        atolx,
        atoly,
        rtolx,
        rtoly)
    print("Return value is {}".format(retVal))
