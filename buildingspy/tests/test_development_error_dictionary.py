#!/usr/bin/env python
import unittest

class Test_development_error_dictionary(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.development.error_dictionary.ErrorDictionary`.
    """

    def test_keys(self):
        import buildingspy.development.error_dictionary as e
        err_dic = e.ErrorDictionary()
        k = err_dic.keys()

        k_expected = ['differentiated if',
                      'experiment annotation',
                      'file not found',
                      'invalid connect',
                      'numerical Jacobians',
                      'parameter with start value only',
                      'redeclare non-replaceable',
                      'redundant consistent initial conditions',
                      'type incompatibility',
                      'type inconsistent definition equations',
                      'unspecified initial conditions',
                      'unused connector']

        self.assertEqual(len(k), len(k_expected), "Wrong number of keys.")
        for i in range(len(k)):
            self.assertEqual(k[i], k_expected[i], "Wrong key, expected \"{}\".".format(k_expected[i]))

    def test_tool_messages(self):
        import buildingspy.development.error_dictionary as e
        err_dic = e.ErrorDictionary()
        k = err_dic.tool_messages()
        k_expected = ['Differentiating (if',
                      'Warning: Failed to interpret experiment annotation',
                      'which was not found',
                      'The model contained invalid connect statements.',
                      'Number of numerical Jacobians:',
                      "Warning: The following parameters don't have any value, only a start value",
                      'Warning: Redeclaration of non-replaceable requires type equivalence',
                      'Redundant consistent initial conditions:',
                      'but they must be compatible',
                      'Type inconsistent definition equation',
                      'Dymola has selected default initial condition',
                      'Warning: The following connector variables are not used in the model']

        self.assertEqual(len(k), len(k_expected), "Wrong number of tool messages.")
        for i in range(len(k)):
            self.assertEqual(k[i], k_expected[i], "Wrong tool message, expected \"{}\".".format(k_expected[i]))


if __name__ == '__main__':
    unittest.main()
