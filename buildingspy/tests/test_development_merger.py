#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import unittest


class Test_development_merger_IBPSA(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.development.merger`.
    """

    needs_initial = True
    repDir = ""

    def __init__(self, *args, **kwargs):
        # unittest.TestCase.__init__(self, name)
        import os
        import tempfile
        from git import Repo

        # The constructor is called multiple times by the unit testing framework.
        # Hence, we keep track of the first call to avoid multiple temporary directories.
        if self.__class__.needs_initial:
            self._repDir = tempfile.mkdtemp(prefix="tmp-BuildingsPy" + "-testing-")
            print("************************** {}".format(self._repDir))

            self.__class__.needs_initial = False
            self.__class__.repDir = self._repDir

            # Clone the libraries
            print("Cloning Buildings repository. This may take a while.")
            print("Dir is {}".format(self._repDir))
            Repo.clone_from("https://github.com/lbl-srg/modelica-buildings",
                            os.path.join(self._repDir, "modelica-buildings"), depth=5)
            print("Cloning IBPSA repository. This may take a while.")
            Repo.clone_from("https://github.com/ibpsa/modelica-ibpsa",
                            os.path.join(self._repDir, "modelica"), depth=5)
            print("Finished cloning.")

        else:
            self._repDir = self.__class__.repDir

        self._ibpsa_dir = os.path.join(self._repDir, "modelica", "IBPSA")
        self._dest_dir = os.path.join(self._repDir, "modelica-buildings", "Buildings")

        # Call constructor of parent class
        super(Test_development_merger_IBPSA, self).__init__(*args, **kwargs)

    def test_initialize(self):
        import buildingspy.development.merger as m

        # Test a package that does not exist
        self.assertRaises(ValueError, m.IBPSA, "non_existent_modelica_package", self._dest_dir)
        self.assertRaises(ValueError, m.IBPSA, self._ibpsa_dir, "non_existent_modelica_package")

        # Test packages that do exist
        m.IBPSA(self._ibpsa_dir, self._dest_dir)

    def test_remove_library_specific_documentation(self):
        import buildingspy.development.merger as m

        lines = ["aaa", "bbb", "<!-- @include_Buildings", "ccc", "-->", "ddd"]
        result = ["aaa", "bbb", "ccc", "ddd"]
        self.assertEqual(result,
                         m.IBPSA.remove_library_specific_documentation(lines, "Buildings"),
                         "Test one library")

        lines[2] = "<!-- @include_Buildings @include_aaa"
        self.assertEqual(result,
                         m.IBPSA.remove_library_specific_documentation(lines, "Buildings"),
                         "Test multiple libraries")

        lines[2] = "<!-- @include_aaa @include_Buildings"
        self.assertEqual(result,
                         m.IBPSA.remove_library_specific_documentation(lines, "Buildings"),
                         "Test multiple libraries reverse")

        lines[2] = " <!--  @include_Buildings"
        self.assertEqual(result,
                         m.IBPSA.remove_library_specific_documentation(lines, "Buildings"),
                         "Test with spaces")

        lines[2] = "<!--"
        result = ["aaa", "bbb", "<!--", "ccc", "-->", "ddd"]
        self.assertEqual(result,
                         m.IBPSA.remove_library_specific_documentation(lines, "Buildings"),
                         "Test without removing")
        return

    def test_merge(self):
        """Test merging the libraries
        """
        # This requires https://github.com/gitpython-developers/GitPython

        import shutil

        import buildingspy.development.merger as m

        mer = m.IBPSA(self._ibpsa_dir, self._dest_dir)
        mer.merge()

        if "tmp-BuildingsPy" in self._repDir:
            shutil.rmtree(self._repDir)


if __name__ == '__main__':
    unittest.main()
