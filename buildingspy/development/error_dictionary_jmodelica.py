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
import buildingspy.development.error_dictionary_optimica as ed


class ErrorDictionary(ed.ErrorDictionary):
    """ Class that contains data fields needed for the
        error checking of the regression tests.

        If additional error messages need to be checked,
        then they should be added to the constructor of this class.
    """
