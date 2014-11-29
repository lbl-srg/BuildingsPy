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
        
        o  = ["UsersGuide", "a", "B", "y", "Z", "Data", "Types", 
              "Examples", "Validation", "Experimental", "BaseClasses", "Interfaces", "Internal", "Obsolete"]

        random.seed(1)
        for i in range(10):
            # Copy the list to prevent the original list to be modified.
            s = list(o)
            # Shuffle the list randomly.
            random.shuffle(s)
            s = r.Refactor.sort_package_order(s)
            self.assertEqual(o, s, "Sorting failed with i=%d." % i)
        # Reset the random number generator.
        random.seed()
        
if __name__ == '__main__':
    unittest.main()

