#!/usr/bin/env python
import unittest

class Test_development_refactor(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.development.refactor.Refactor`.
    """
    
    def test_sort_package_order(self):
        import random
        import buildingspy.development.refactor as r
        __MOD=0
        __REC=1
        __PAC=2
        
        o  = [[__PAC, "UsersGuide"], 
              [__MOD, "a"],
              [__MOD, "y"], 
              [__REC, "a_data"],
              [__PAC, "B"], 
              [__PAC, "Z"],
              [__PAC, "Data"],
              [__PAC, "Types"],
              [__PAC, "Examples"],
              [__PAC, "Validation"],
              [__PAC, "Experimental"],
              [__PAC, "Interfaces"],
              [__PAC, "BaseClasses"],
              [__PAC, "Internal"], 
              [__PAC, "Obsolete"]]

        random.seed(1)
        for i in range(10):
            # Copy the list to prevent the original list to be modified.
            s = list(o)
            # Shuffle the list randomly.
            random.shuffle(s)
            s = r._sort_package_order(s)
            self.assertEqual(o, s, "Sorting failed with i=%d." % i)
        # Reset the random number generator.
        random.seed()
        
if __name__ == '__main__':
    unittest.main()

