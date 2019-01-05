#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################
# Class that contains data fields needed for the
# error checking of the regression tests for JModelica
#
#
# MWetter@lbl.gov                            2019-01-04
#######################################################
#
import error_dictionary as ed


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
        self._error_dict["each applied to scalar"] = {
            'tool_message': "The 'each' keyword should not be applied to a modification of a scalar component",
            'counter': 0,
            'buildingspy_var': "iEacSca",
            'model_message': "Keyword 'each' applied to scalar in '{}'.",
            'summary_message': "Number of models with 'each' keyword applied to scalar        : {}\n"}
