#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import unittest


class Test_development_refactor(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.development.refactor.Refactor`.
    """

    def test_sort_package_order(self):
        import random
        import buildingspy.development.refactor as r
        __MOD = 0
        __REC = 1
        __PAC = 2
        __CON = 3

        o = [[__PAC, "UsersGuide"],
             [__MOD, "a"],
             [__MOD, "y"],
             [__REC, "a_data"],
             [__PAC, "B"],
             [__PAC, "Z"],
             [__CON, "zcon_b"],
             [__CON, "zcon_c"],
             [__CON, "zcon_a"],
             [__PAC, "Data"],
             [__PAC, "Types"],
             [__PAC, "Examples"],
             [__PAC, "Validation"],
             [__PAC, "Experimental"],
             [__PAC, "Interfaces"],
             [__PAC, "BaseClasses"],
             [__PAC, "Internal"],
             [__PAC, "Obsolete"]]

        c = [[__CON, "zcon_b"],
             [__CON, "zcon_c"],
             [__CON, "zcon_a"]]
        random.seed(1)
        for i in range(10):
            # Copy the list to prevent the original list to be modified.
            s = list(o)
            # Shuffle the list randomly.
            random.shuffle(s)
            # Remove and insert constants (whose order need to be preserved between
            # .mo and package.order
            s2 = [ele for ele in s if not ele[0] == __CON]
            s2.extend(c)
            s = r._sort_package_order(s2)
            self.assertEqual(o, s, "Sorting failed with i=%d." % i)
        # Reset the random number generator.
        random.seed()

    def test_write_package_order(self):
        import os
        import buildingspy.development.refactor as r

        package_path = os.path.abspath(os.path.join("buildingspy", "tests", "MyModelicaLibrary"))

        pac_lis = list()
        # The digit 3 is the enumeration for package, e.g, __PAC in refactor
        correct = [[3, u'one'], [3, u'two'], [3, u'Reset']]

        pac_lis = r._get_package_list_for_file(package_path, "package.mo")

        self.assertEqual(pac_lis, correct, "Parsing package.order failed.")

    def test_get_constants_non_empty(self):
        import buildingspy.development.refactor as r

        lines = """
        constant Real a = 1 "some text";
        constant Real b = 1;
        constant Real A = 1;
        constant Real B[2] = {1, 2};
        constant Real C[:] = {1, 2};
        constant Real D[1,2] = {{1}, {1, 2}};
        constant Real E[:,:] = {{1}, {1, 2}};
        not_a_constant f = 1;
        """
        con = r._get_constants(lines)
        self.assertEqual(con, ['a', 'b', 'A', 'B', 'C', 'D', 'E'], "Failed to get all constants.")

    def test_get_constants_empty(self):
        import buildingspy.development.refactor as r

        lines = """

        """
        con = r._get_constants(lines)
        for ele in con:
            print(f"--{ele}--")
        self.assertEqual(
            con,
            [],
            "Failed to get all constants for a file content with no constants.")

    def test_get_modelica_file_name(self):
        import os
        import buildingspy.development.refactor as r
        self.assertEqual(r.get_modelica_file_name("Buildings.Rooms.MixedAir"),
                         os.path.join("Buildings", "Rooms", "MixedAir.mo"))

    def test_getShortName(self):
        import os
        import buildingspy.development.refactor as r

        workdir = os.getcwd()
        os.chdir(os.path.join("buildingspy", "tests"))
        filePath = 'MyModelicaLibrary/Examples/FMUs/Gain.mo'
        self.assertEqual(
            r._getShortName(
                filePath,
                'MyModelicaLibrary.Examples.IntegratorGain'
            ),
            ' Examples.IntegratorGain'
        )
        self.assertEqual(
            r._getShortName(
                filePath,
                'MyModelicaLibrary.Examples.Test'
            ),
            ' Test'
        )
        self.assertEqual(
            r._getShortName(
                filePath,
                'MyModelicaLibrary.Examples.FMUs.IntegratorGain'
            ),
            ' IntegratorGain'
        )
        os.chdir(workdir)


if __name__ == '__main__':
    unittest.main()
