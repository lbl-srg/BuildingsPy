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

import buildingspy.simulate.Dymola as d

try:
    # Python 2
    basestring
except NameError:
    # Python 3 or newer
    basestring = str


class Simulator(d.Dymola):
    """Class to simulate a Modelica model.

    :param modelName: The name of the Modelica model.
    :param simulator: The simulation engine. Currently, the only supported value is ``dymola``.
    :param outputDirectory: An optional output directory.
    :param packagePath: An optional path where the Modelica ``package.mo`` file is located.

    If the parameter ``outputDirectory`` is specified, then the
    output files and log files will be moved to this directory
    when the simulation is completed.
    Outputs from the python functions will be written to ``outputDirectory/BuildingsPy.log``.

    If the parameter ``packagePath`` is specified, then this directory
    and all its subdirectories will be copied to a temporary directory when running the simulations.

    .. note:: Up to version 1.4, the environmental variable ``MODELICAPATH``
              has been used as the default value. This has been changed as
              ``MODELICAPATH`` can have multiple entries in which case it is not
              clear what entry should be used.
    """

    def __init__(self, modelName, simulator, outputDirectory='.', packagePath=None):
        super().__init__(
            modelName=modelName,
            simulator=simulator,
            outputDirectory=outputDirectory,
            packagePath=packagePath)

        raise DeprecationWarning(
            "The class buildingspy.simulate.Simulator is deprecated and will be removed in future versions. Use buildingspy.simulate.Dymola instead.")
