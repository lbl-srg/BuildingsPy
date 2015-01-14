#!/usr/bin/env python
import unittest

class Test_development_merger_Annex60(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.development.sync.Annex60`.
    """
    
    needs_initial = True
    repDir = ""
    
    def __init__(self, *args, **kwargs):
#        unittest.TestCase.__init__(self, name) 
        import os
        import tempfile
        from git import Repo
      
        # The constructor is called multiple times by the unit testing framework.
        # Hence, we keep track of the first call to avoid multiple temporary directories.      
        if self.__class__.needs_initial:    
            self._repDir = tempfile.mkdtemp(prefix="tmp-BuildingsPy" +  "-testing-")
            print "**************************", self._repDir
            
            self.__class__.needs_initial = False
            self.__class__.repDir = self._repDir
            
            # Clone the libraries
            print "Cloning Buildings repository. This may take a while."
            print "Dir is ", self._repDir
            Repo.clone_from("https://github.com/lbl-srg/modelica-buildings", os.path.join(self._repDir, "modelica-buildings"))
            print "Cloning Annex 60 repository. This may take a while."        
            Repo.clone_from("https://github.com/iea-annex60/modelica-annex60", os.path.join(self._repDir, "modelica-annex60"))
            print "Finished cloning."
            
        else:
            self._repDir = self.__class__.repDir

        self._annex60_dir=os.path.join(self._repDir, "modelica-annex60", "Annex60")
        self._dest_dir=os.path.join(self._repDir,  "modelica-buildings", "Buildings")

        # Call constructor of parent class
        super(Test_development_merger_Annex60, self).__init__(*args, **kwargs)

        
    def test_initialize(self):
        import buildingspy.development.merger as m

        # Test a package that does not exist
        self.assertRaises(ValueError, m.Annex60, "non_existent_modelica_package", self._dest_dir)
        self.assertRaises(ValueError, m.Annex60, self._annex60_dir, "non_existent_modelica_package")        

        # Test packages that do exist
        m.Annex60(self._annex60_dir, self._dest_dir)
 
        
    def test_merge(self):
        """Test merging the libraries
        """
        # This requires https://github.com/gitpython-developers/GitPython

        import shutil

        import buildingspy.development.merger as m
        
        mer = m.Annex60(self._annex60_dir, self._dest_dir)
        mer.merge()

        if "tmp-BuildingsPy" in self._repDir:
            shutil.rmtree(self._repDir)


        
if __name__ == '__main__':
    unittest.main()

