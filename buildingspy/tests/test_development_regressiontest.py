#!/usr/bin/env python
import unittest
import os


# To run this test, navigate to the BuildingsPy folder, then type
# python buildingspy/tests/test_development_regressiontest.py

class Test_regressiontest_Tester(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.regressiontest.Tester`.
    """

    def test_get_plot_variables(self):
        import buildingspy.development.regressiontest as r

        self.assertIsNone(r.Tester.get_plot_variables("abc"), "Expected None return value")
        self.assertIsNone(r.Tester.get_plot_variables("y=abc"), "Expected None return value")
        self.assertIsNone(r.Tester.get_plot_variables("leftTitleType=1, bottomTitleType=1, colors={{0,0,255},"), "Expected None")

        self.assertEqual(["a", "b", "c"], r.Tester.get_plot_variables('y = {"a", "b", "c"}'), "Expected a b c")
        self.assertEqual(["a", "b", "c"], r.Tester.get_plot_variables('y = {"a","b","c"}'), "Expected a b c")
        self.assertEqual(["a", "b", "c"], r.Tester.get_plot_variables('y = {" a", "b ", "c"}'), "Expected a b c")
        self.assertEqual(["a", "b", "c"], r.Tester.get_plot_variables('y = {" a" , "b " , "c"}'), "Expected a b c")
        self.assertEqual(["a", "b", "c"], r.Tester.get_plot_variables('y = {"a","b","c"}'), "Expected a b c")
        self.assertEqual(["a"], r.Tester.get_plot_variables('y = {"a"}'), "Expected a")
        self.assertEqual(["a"], r.Tester.get_plot_variables('y = { "a"}'), "Expected a")
        self.assertEqual(["a"], r.Tester.get_plot_variables('y = { "a" }'), "Expected a")
        self.assertEqual(["a"], r.Tester.get_plot_variables('y ={ "a" }'), "Expected a")
        self.assertEqual(["a"], r.Tester.get_plot_variables('y={ "a" }'), "Expected a")

        self.assertEqual(["a"], r.Tester.get_plot_variables('abc, y = {"a"}'), "Expected a")
        self.assertEqual(["a"], r.Tester.get_plot_variables('x= {"x"}, y = {"a"}, z = {"s"}'), "Expected a")
        self.assertEqual(["x_incStrict[1]", "x_incStrict[2]"],\
                          r.Tester.get_plot_variables('y={"x_incStrict[1]", "x_incStrict[2]"},'),\
                         "Expect other result")
        self.assertEqual(["const1[1].y", "const2[1, 1].y"], \
                         r.Tester.get_plot_variables(' y={"const1[1].y", "const2[1, 1].y"} '))


    def test_regressiontest(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.include_fmu_tests(True)
        rt.writeOpenModelicaResultDictionary()
        rt.run()
        # Delete temporary files
        os.remove('unitTests.log')

        # Verify that invalid packages raise a ValueError.
        self.assertRaises(ValueError, rt.setSinglePackage, "this.package.does.not.exist")


    def test_runSimulation(self):
        import buildingspy.development.regressiontest as r
        self.assertRaises(OSError, \
                          r.runSimulation, ".", "this_command_does_not_exist")

    def test_areResultsEqual(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester()
        tMin = 10
        tMax = 50
        nPoi = 101
        tOld = [tMin, tMax]
        yOld = [10, 10]
        tNew = [tMin+float(i)/(nPoi-1)*(tMax-tMin) for i in range(nPoi) ]
        yNew = [10.0 for i in range(nPoi)]
        varNam = "testVariable"
        filNam = "testFilename"
        (equ, _, _) = rt.areResultsEqual(tOld, yOld, tNew, yNew, varNam, filNam)
        self.assertTrue(equ, "Test 1 for equality failed.")
        # Test with arguments reversed.
        (equ, _, _) = rt.areResultsEqual(tNew, yNew, tOld, yOld, varNam, filNam)
        self.assertTrue(equ, "Test 2 for equality failed.")
        # Modify arguments, now both tests should return false
        yNew[2] = 11.0
        (equ, timMaxErr, _) = rt.areResultsEqual(tOld, yOld, tNew, yNew, varNam, filNam)
        self.assertFalse(equ, "Test 1 for equality should have returned false.")
        self.assertEqual(tNew[2], timMaxErr, "Time of maximum error is wrong for test 1.")
        # Test with arguments reversed.
        (equ, timMaxErr, _) = rt.areResultsEqual(tNew, yNew, tOld, yOld, varNam, filNam)
        self.assertFalse(equ, "Test 2 for equality should have returned false.")
        self.assertEqual(tNew[2], timMaxErr, "Time of maximum error is wrong for test 2.")

        # Test the case where the simulation may have failed and hence the end
        # time is smaller than the end time of the reference results
        tNew = [tMin+float(i)/(nPoi-1)*0.9*(tMax-tMin) for i in range(nPoi) ]
        yNew = [10.0 for i in range(nPoi)]
        (equ, timMaxErr, _) = rt.areResultsEqual(tNew, yNew, tOld, yOld, varNam, filNam)
        self.assertFalse(equ, "Test with smaller simulation end time should have returned false.")
        # Test for different start time
        tNew = [0.1 + tMin+float(i)/(nPoi-1)*(tMax-tMin) for i in range(nPoi) ]
        (equ, timMaxErr, _) = rt.areResultsEqual(tNew, yNew, tOld, yOld, varNam, filNam)
        self.assertFalse(equ, "Test with smaller simulation start time should have returned false.")

    def test_statistics_are_equal(self):
        import buildingspy.development.regressiontest as r

        rt = r.Tester()
        self.assertTrue(rt.are_statistics_equal("0", "0"))
        self.assertTrue(rt.are_statistics_equal("", ""))
        self.assertTrue(rt.are_statistics_equal(" ", " "))
        self.assertFalse(rt.are_statistics_equal(" ", "0"))
        self.assertFalse(rt.are_statistics_equal("1", "1 1"))
        # 1, 2 is equal to 2, 1
        self.assertTrue(rt.are_statistics_equal("1, 2", "2, 1"))
        self.assertTrue(rt.are_statistics_equal("1, 40, 2", "2, 1, 40"))
        self.assertFalse(rt.are_statistics_equal("1, 40", "1, 40, 0"))

    def test_format_float(self):
        import buildingspy.development.regressiontest as r

        rt = r.Tester()

        self.assertEqual(float(rt.format_float(1.0)), float(1))
        self.assertEqual(float(rt.format_float(0.5)), float(0.5))
        self.assertEqual(float(rt.format_float(1.234)), float(1.234))
        self.assertEqual(float(rt.format_float(100)), float(100))
        self.assertEqual(float(rt.format_float(100.)), float(100.))
        self.assertEqual(float(rt.format_float(100.01230)), float(100.01230))
        self.assertEqual(float(rt.format_float(-100.01230)), float(-100.01230))
        self.assertEqual(float(rt.format_float(-100.0123)), float(-100.0123))

    def test_setLibraryRoot(self):
        import buildingspy.development.regressiontest as r

        rt = r.Tester()
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        # This call should succeed, even if used twice
        rt.setLibraryRoot(myMoLib)
        rt.setLibraryRoot(myMoLib)
        # This call must raise an exception
        self.assertRaises(ValueError, \
                          rt.setLibraryRoot, "this_is_not_the_root_dir_of_a_library")

    def test_test_OpenModelica(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        rt._deleteTemporaryDirectories=False

        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.test_OpenModelica(simulate=True)

    def test_setDataDictionary(self):
        import buildingspy.development.regressiontest as r
        rt = r.Tester(check_html=False)
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        rt.setLibraryRoot(myMoLib)
        rt.setDataDictionary()

if __name__ == '__main__':
    unittest.main()
    #selection = unittest.TestSuite()
    #selection.addTest(Test_regressiontest_Tester('test_test_OpenModelica'))
    #unittest.TextTestRunner().run(selection)
