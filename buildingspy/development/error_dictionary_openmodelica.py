#!/usr/bin/env python
# -*- coding: utf-8 -*-
#########################################################
# Class that contains data fields needed for the
# error checking of the regression tests for OpenModelica
#
#
# MWetter@lbl.gov                              2021-12-23
#########################################################
#
import buildingspy.development.error_dictionary as ed


class ErrorDictionary(ed.ErrorDictionary):
    """ Class that contains data fields needed for the
        error checking of the regression tests.

        If additional error messages need to be checked,
        then they should be added to the constructor of this class.
    """

    def __init__(self):
        """ Constructor.
        """
        self._error_dict = dict()
        # Set the error dictionaries.
        # Note that buildingspy_var needs to be a unique variable name.

        # The test below is commented as OpenModelica issues a warning for example in
        # Buildings.Fluid.MixingVolumes.Validation.MixingVolumeHeatReverseFlow.
        # This is already reported in https://github.com/OpenModelica/OpenModelica/issues/7777
        # and in https://github.com/modelica/ModelicaSpecification/issues/3052
        # self._error_dict["each applied to scalar"] = {
        # 'tool_message': "used when modifying non-array element",
        # 'counter': 0,
        # 'summary_message': "Number of models with 'each' keyword applied to scalar       : {}\n"}

        self._error_dict["assuming each"] = {
            'tool_message': "Non-array modification",
            'counter': 0,
            'summary_message': "Number of models with missing 'each'                         : {}\n"}
