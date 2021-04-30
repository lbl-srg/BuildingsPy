#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################
# Class that contains data fields needed for the
# error checking of the regression tests for OPTIMICA
#
#
# MWetter@lbl.gov                            2020-01-30
#######################################################
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
        self._error_dict["each applied to scalar"] = {
            'tool_message': "The 'each' keyword should not be applied to a modification of a scalar component",
            'counter': 0,
            #            'buildingspy_var': "iEacSca",
            #            'model_message': "Keyword 'each' applied to scalar in '{}'.",
            'summary_message': "Number of models with 'each' keyword applied to scalar          : {}\n"}

        self._error_dict["errorneous each"] = {
            'tool_message': "Ignoring erroneous 'each' for the modification",
            'counter': 0,
            #            'buildingspy_var': "iEacIgn",
            #            'model_message': "Keyword 'each' applied to scalar in '{}'.",
            'summary_message': "Number of models with erroneous 'each'                          : {}\n"}

        self._error_dict["assuming each"] = {
            'tool_message': "Assuming 'each' for the modification",
            'counter': 0,
            #            'buildingspy_var': "iEacAss",
            #            'model_message': "Keyword 'each' applied to scalar in '{}'.",
            'summary_message': "Number of models with assuming 'each'                           : {}\n"}

        # Search for strings such as Iteration variable "chi_y.QCon_flow" is missing start value!
#        self._error_dict["iteration variable missing start value"] = {
#            'tool_message': "is missing start value",
#            'counter': 0,
        #            'buildingspy_var': "iIteMis",
        #            'model_message': "Keyword 'each' applied to scalar in '{}'.",
#            'summary_message': "Number of models with missing start value for iteration variable: {}\n"}

        # Search for strings such as Iteration variable "chi_y.QCon_flow" is missing start value!
        self._error_dict["redeclare of non-replaceable"] = {
            'tool_message': "can't be redeclared since it has already been redeclared without 'replaceable'",
            'counter': 0,
            #            'buildingspy_var': "iIteMis",
            #            'model_message': "Keyword 'each' applied to scalar in '{}'.",
            'summary_message': "Number of models with redeclare of no longer replaceable class  : {}\n"}

        # Search for strings such as
        # Access to component cor not recommended, it is not present in
        # constraining type of declaration
        # 'replaceable Buildings.Examples.VAVReheat.BaseClasses.Floor flo
        self._error_dict["non-recommended access to component not in constraining type"] = {
            'tool_message': "it is not present in constraining type of declaration",
            'counter': 0,
            'summary_message': "Number of models with access not in constraining type           : {}\n"}
