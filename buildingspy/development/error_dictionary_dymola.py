#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################
# Class that contains data fields needed for the
# error checking of the regression tests for Dymola.
#
#
# MWetter@lbl.gov                            2015-11-17
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
        self._error_dict["numerical Jacobians"] = {
            'tool_message': r"Number of numerical Jacobians: (\d*)",
            'is_regex': True,
            'counter': 0,
            'model_message': "Numerical Jacobian in '{}'.",
            'summary_message': "Number of models with numerical Jacobian                     : {}\n"}

        self._error_dict["unused connector"] = {
            'tool_message': "Warning: The following connector variables are not used in the model",
            'counter': 0,
            'model_message': "Unused connector variables in '{}'.\n",
            'summary_message': "Number of models with unused connector variables             : {}\n"}

        self._error_dict["parameter with start value only"] = {
            'tool_message': "Warning: The following parameters don't have any value, only a start value",
            'counter': 0,
            'model_message': "Parameter with start value only in '{}'.\n",
            'summary_message': "Number of models with parameters that only have a start value: {}\n"}

        self._error_dict["redundant consistent initial conditions"] = {
            'tool_message': "Redundant consistent initial conditions:",
            'counter': 0,
            'model_message': "Redundant consistent initial conditions in '{}'.\n",
            'summary_message': "Number of models with redundant consistent initial conditions: {}\n"}

        self._error_dict["redundant connection"] = {
            'tool_message': "Redundant connection",
            'counter': 0,
            'model_message': "Redundant connections in '{}'.\n",
            'summary_message': "Number of models with redundant connections                  : {}\n"}

        self._error_dict["type inconsistent definition equations"] = {
            'tool_message': "Type inconsistent definition equation",
            'counter': 0,
            'model_message': "Type inconsistent definition equations in '{}'.\n",
            'summary_message': "Number of models with type inconsistent definition equations : {}\n"}

        self._error_dict["type incompatibility"] = {
            'tool_message': "but they must be compatible",
            'counter': 0,
            'model_message': "Type incompatibility in '{}'.\n",
            'summary_message': "Number of models with incompatible types                     : {}\n"}

        self._error_dict["unspecified initial conditions"] = {
            'tool_message': "Dymola has selected default initial condition",
            'counter': 0,
            'model_message': "Unspecified initial conditions in '{}'.\n",
            'summary_message': "Number of models with unspecified initial conditions         : {}\n"}

        self._error_dict["invalid connect"] = {
            'tool_message': "The model contained invalid connect statements.",
            'counter': 0,
            'model_message': "Invalid connect statements in '{}'.\n",
            'summary_message': "Number of models with invalid connect statements             : {}\n"}

        # This checks for something like
        # Differentiating (if noEvent(m_flow > m_flow_turbulent) then (m_flow/k)^2 else (if ....
        # under the assumption that it is continuous at switching.
        self._error_dict["differentiated if"] = {
            'tool_message': "Differentiating (if",
            'counter': 0,
            'model_message': "Differentiated if-expression under assumption it is smooth in '{}'.\n",
            'summary_message': "Number of models with differentiated if-expression           : {}\n"}

        self._error_dict["redeclare non-replaceable"] = \
            {'tool_message': "Warning: Redeclaration of non-replaceable requires type equivalence",
             'counter': 0,
             'model_message': "Redeclaration of non-replaceable class in '{}'.\n",
             'summary_message': "Number of models with redeclaration of non-replaceable class : {}\n"}

        self._error_dict["experiment annotation"] = {
            'tool_message': "Warning: Failed to interpret experiment annotation",
            'counter': 0,
            'model_message': "Failed to interpret experiment annotation in '{}'.\n",
            'summary_message': "Number of models with wrong experiment annotation            : {}\n"}

        # This is a  test for
        #  Warning: Command 'Simulate and plot' in model 'Buildings.Airflow.Multizone.BaseClasses.Examples.WindPressureLowRise',
        #  specified file modelica://Buildings/.../windPressureLowRise.mos which was not found.
        self._error_dict["file not found"] = {
            'tool_message': "which was not found",
            'counter': 0,
            'model_message': "File not found in '{}'.\n",
            'summary_message': "Number of models with file not found                         : {}\n"}

        self._error_dict["stateGraphRoot missing"] = {
            'tool_message': "A \\\"stateGraphRoot\\\" component was automatically introduced.",
            'counter': 0,
            'model_message': "\"inner Modelica.StateGraph.StateGraphRoot\" is missing in '{}'.\n",
            'summary_message': "Number of models with missing StateGraphRoot                 : {}\n"}

        self._error_dict["mismatched displayUnits"] = {
            'tool_message': "Mismatched displayUnit",
            'counter': 0,
            'model_message': "Mismatched displayUnit in '{}'.\n",
            'summary_message': "Number of models with mismatched displayUnit                 : {}\n"}

        self._error_dict["suspicious attributes"] = {
            'tool_message': "which is suspicious",
            'counter': 0,
            'model_message': "Check min and max attributes in '{}'.\n",
            'summary_message': "Number of models with suspicious attributes (likely min/max) : {}\n"}

        # This captures
        # Warning: function Buildings.Utilities.Psychrometrics.Functions.saturationPressureLiquid
        # specified derivative Buildings.Utilities.Psychrometrics.Functions.BaseClasses.der_saturationPressureLiquid,
        # but argument TSat function did not match argument Tsat of derivative
        self._error_dict["wrong derivative specification"] = {
            'tool_message': "did not match argument",
            'counter': 0,
            'model_message': "Check specification of derivative of '{}'.\n",
            'summary_message': "Number of models with wrong derivative specification         : {}\n"}
