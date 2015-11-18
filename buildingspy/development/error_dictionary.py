#!/usr/bin/env python
#######################################################
# Class that contains data fields needed for the
# error checking of the regression tests.
#
#
# MWetter@lbl.gov                            2015-11-17
#######################################################

class ErrorDictionary:
    ''' Class that contains data fields needed for the
        error checking of the regression tests.

        If additional error messages need to be checked,
        then they should be added to the constructor of this class.
    '''

    def __init__(self):
        ''' Constructor.
        '''
        self._error_dict = dict()
        # Set the error dictionaries.
        # Note that buildingspy_var needs to be a unique variable name.
        self._error_dict["numerical Jacobians"] = \
            {'tool_message'    : "Number of numerical Jacobians:",
             'counter'         : 0,
             'buildingspy_var' : "lJac",
             'model_message'   : "Numerical Jacobian in '{}'.",
             'summary_message' : "Number of models with numerical Jacobian                     : {}\n"}

        self._error_dict["unused connector"] = \
            {'tool_message'    : "Warning: The following connector variables are not used in the model",
             'counter'         : 0,
             'buildingspy_var' : "iUnuCon",
             'model_message'   : "Unused connector variables in '{}'.\n",
             'summary_message' : "Number of models with ununsed connector variables            : {}\n"}

        self._error_dict["parameter with start value only"] = \
            {'tool_message'    : "Warning: The following parameters don't have any value, only a start value",
             'counter'         : 0,
             'buildingspy_var' : "iParNoSta",
             'model_message'   : "Parameter with start value only in '{}'.\n",
             'summary_message' : "Number of models with parameters that only have a start value: {}\n"}

        self._error_dict["redundant consistent initial conditions"] = \
            {'tool_message'    : "Redundant consistent initial conditions:",
             'counter'         : 0,
             'buildingspy_var' : "iRedConIni",
             'model_message'   : "Redundant consistent initial conditions in '{}'.\n",
             'summary_message' : "Number of models with redundant consistent initial conditions: {}\n"}

        self._error_dict["type inconsistent definition equations"] = \
            {'tool_message'    : "Type inconsistent definition equation",
             'counter'         : 0,
             'buildingspy_var' : "iTypIncDef",
             'model_message'   : "Type inconsistent definition equations in '{}'.\n",
             'summary_message' : "Number of models with type inconsistent definition equations : {}\n"}

        self._error_dict["type incompatibility"] = \
            {'tool_message'    : "but they must be compatible",
             'counter'         : 0,
             'buildingspy_var' : "iTypInc",
             'model_message'   : "Type incompabitibility in '{}'.\n",
             'summary_message' : "Number of models with incompatible types                     : {}\n"}

        self._error_dict["unspecified initial conditions"] = \
            {'tool_message'    : "Dymola has selected default initial condition",
             'counter'         : 0,
             'buildingspy_var' : "iUnsIni",
             'model_message'   : "Unspecified initial conditions in '{}'.\n",
             'summary_message' : "Number of models with unspecified initial conditions         : {}\n"}

        self._error_dict["invalid connect"] = \
            {'tool_message'    : "The model contained invalid connect statements.",
             'counter'         : 0,
             'buildingspy_var' : "iInvCon",
             'model_message'   : "Invalid connect statements in '{}'.\n",
             'summary_message' : "Number of models with invalid connect statements             : {}\n"}

        # This checks for something like
        # Differentiating (if noEvent(m_flow > m_flow_turbulent) then (m_flow/k)^2 else (if ....
        # under the assumption that it is continuous at switching.
        self._error_dict["differentiated if"] = \
            {'tool_message'    : "Differentiating (if",
             'counter'         : 0,
             'buildingspy_var' : "iDiffIf",
             'model_message'   : "Differentiated if-expression under assumption it is smooth in '{}'.\n",
             'summary_message' : "Number of models with differentiated if-expression           : {}\n"}

    def get_dictionary(self):
        """ Return the dictionary with all error data
        """
        return self._error_dict

    def increment_counter(self, key):
        """ Increment the error counter by one for the error type defined by *key*.

        :param key: The json key of the error type.
        """
        self._error_dict[key]["counter"] = self._error_dict[key]["counter"] + 1

    def keys(self):
        """ Return a copy of the dictionary's list of keys.
        """
        return sorted(self._error_dict.keys())

    def tool_messages(self):
        """ Return a copy of the tool messages as a list.
        """
        ret = list()
        keys = self.keys()
        for key in keys:
            ret.append(self._error_dict[key]['tool_message'])
        return ret