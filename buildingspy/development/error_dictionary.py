#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################
# Class that contains data fields needed for the
# error checking of the regression tests.
#
#
# MWetter@lbl.gov                            2015-11-17
#######################################################
class ErrorDictionary(object):
    """ Class that contains data fields needed for the
        error checking of the regression tests.

        If additional error messages need to be checked,
        then they should be added to the constructor of this class.
    """

    def __init__(self):
        """ Constructor.
        """
        return

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
        keys = list(self.keys())
        for key in keys:
            ret.append(self._error_dict[key]['tool_message'])
        return ret
