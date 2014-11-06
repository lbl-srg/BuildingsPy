#!/usr/bin/env python
import unittest
import os
import shutil
import scipy.io
import numpy as np
from buildingspy.rc_models.rc_model import RcModel, matrix_to_string, read_zones_table

class Test_rc_models(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.rc_models.rc_model`.
    """
    
    def setUp(self):
        """
        Define a variable and files that will be used in other tests
        """
        from array import array
        
        # Define a temporary directory that contains the files for the test
        dirPath = os.path.dirname(__file__)
        self.temp_dir = os.path.join(dirPath, "temp_files")
        os.mkdir(self.temp_dir)
        
        self.wrong_template = os.path.join(self.temp_dir, "wrongTemplate.txt")
        
        # Create a wrong template file
        with open(self.wrong_template, "w") as f:
            f.write("Not a template")
            
        # Create a correct mat file
        self.correct_mat_file = os.path.join(self.temp_dir, "correctMatFile.mat")
        dict = {}
        dict["A"] = np.ones((2,2))
        dict["Bv"] = np.ones((2,4))
        dict["state_x"] = [[array('u', u'one')], [array('u', u'two')]]
        dict["state_v"] = [[array('u', u'A1')], [array('u', u'D2')], [array('u', u'C3')], [array('u', u'D4')]]
        zones_table = np.array([[[u'identifier'],[u'description'],[u'area'],[u'volume']],\
                       [[u'Z001'],[u'zone 1'],[u'11.00'],[u'33.00']],\
                       [[u'Z002'],[u'zone 2'],[u'11.00'],[u'33.00']],\
                       [[u'Z003'],[u'zone 3'],[u'11.00'],[u'33.00']],\
                       [[u'Z004'],[u'zone 4'],[u'11.00'],[u'33.00']],\
                       [[u'Z005'],[u'zone 5'],[u'11.00'],[u'33.00']]])
        dict["zone"] = zones_table
        scipy.io.savemat(self.correct_mat_file, mdict = dict)
        
        # Create a wrong mat file
        self.wrong_mat_file = os.path.join(self.temp_dir, "wrongMatFile.mat")
        dict = {}
        dict["A"] = np.ones((2,2))
        scipy.io.savemat(self.wrong_mat_file, mdict = dict)
        
        # Create dummy templates
        self.dummy_template_rc_model_path = os.path.join(self.temp_dir, "model.jinja")
        self.dummy_template_avg_model_path = os.path.join(self.temp_dir, "model_avg.jinja")
        self.dummy_template_rc_model_name = "model.jinja"
        self.dummy_template_avg_model_name = "model_avg.jinja"
        with open(self.dummy_template_rc_model_path, "w") as f:
            f.write(("{{modelName}}\n"))
            f.write(("{{description}}\n"))
            f.write(("{{A}}\n"))
            f.write(("{{B}}"))
            
        with open(self.dummy_template_avg_model_path, "w") as f:
            f.write(("{{modelName}}\n"))
            f.write(("{{description}}\n"))
            f.write(("{{weigths}}\n"))
            f.write(("{{N_zones}}"))
    
    def tearDown(self):
        """
        This method deletes all the files and directories created by the setUp method
        """
        shutil.rmtree(self.temp_dir)
    
    def test_matrix_to_string(self):
        '''
        Tests the :mod:`buildingspy.rc_models.rc_model.matrix_to_string`
        function.
        '''
        
        A = np.ones((2,2))
        As = matrix_to_string(A)
        As_expected = "[1.000000, 1.000000; 1.000000, 1.000000]"
        self.assertEqual(As_expected, As, "The Modelica matrix has not been generated correctly")
        
        V = np.array([1,2,3,4,5])
        Vs = matrix_to_string(V)
        Vs_expected = "{1.000000, 2.000000, 3.000000, 4.000000, 5.000000}"
        self.assertEqual(Vs_expected, Vs, "The Modelica vector has not been generated correctly")
        
    def test_init_RcModel(self):
        '''
        Tests the :cls:`buildingspy.rc_models.rc_model.RcModel`
        class.
        '''
        rc = RcModel()
        
        # Do not set details
        rc.set_templates_details(dir_path = None, rc_model_template = None, avg_model_template = None)
        
        # Try to set wrong details
        self.assertRaises(OSError, rc.set_templates_details, dir_path = "UnknownDir")
        self.assertRaises(OSError, rc.set_templates_details, rc_model_template = "UnknownFile")
        self.assertRaises(OSError, rc.set_templates_details, avg_model_template = "UnknownFile")
        self.assertRaises(ValueError, rc.set_templates_details, dir_path = self.temp_dir, avg_model_template = self.wrong_template)
        self.assertRaises(ValueError, rc.set_templates_details, dir_path = self.temp_dir, rc_model_template = self.wrong_template)\
    
    def test_read_zones_table(self):
        """
        Tests the :mod:`buildingspy.rc_models.rc_model.read_zones_table`
        function.
        """
        import numpy as np
        import array
        
        # Create a valid zone table
        zones_table = np.array([[[u'identifier'],[u'description'],[u'area'],[u'volume']],\
                       [[u'Z001'],[u'zone 1'],[u'11.00'],[u'33.00']],\
                       [[u'Z002'],[u'zone 2'],[u'22.00'],[u'66.00']],\
                       [[u'Z003'],[u'zone 3'],[u'33.00'],[u'99.00']],\
                       [[u'Z004'],[u'zone 4'],[u'44.00'],[u'132.00']],\
                       [[u'Z005'],[u'zone 5'],[u'55.00'],[u'165.00']]])
        
        # Read the data
        (zones, zones_id, zones_desc) = read_zones_table(zones_table)
        
        # Check correctness
        self.assertListEqual(['zone 1','zone 2','zone 3','zone 4','zone 5'], zones_desc, "The zones descriptions are different")
        self.assertListEqual(['Z001','Z002','Z003','Z004','Z005'], zones_id, "The zones ids are different")
        zones_expected = np.array([range(1,6), range(1,6)]).T
        zones_expected[:,0] *= 11.0
        zones_expected[:,1] *= 33.0
        np.testing.assert_array_equal(zones_expected, zones, "The zones values are different")
        
        # Check with wrong tables
        zones_table = np.array([[[u'identifier'],[u'description'],[u'volume']],\
                       [[u'Z001'],[u'zone 1'],[u'33.00']],\
                       [[u'Z002'],[u'zone 2'],[u'66.00']],\
                       [[u'Z003'],[u'zone 3'],[u'99.00']],\
                       [[u'Z004'],[u'zone 4'],[u'132.00']],\
                       [[u'Z005'],[u'zone 5'],[u'165.00']]])
        self.assertRaises(KeyError, read_zones_table, zones_table)
        
        zones_table = np.array([[[u'identifier'],[u'description'],[u'area']],\
                       [[u'Z001'],[u'zone 1'],[u'33.00']],\
                       [[u'Z002'],[u'zone 2'],[u'66.00']],\
                       [[u'Z003'],[u'zone 3'],[u'99.00']],\
                       [[u'Z004'],[u'zone 4'],[u'132.00']],\
                       [[u'Z005'],[u'zone 5'],[u'165.00']]])
        self.assertRaises(KeyError, read_zones_table, zones_table)
        
       
    def test_load_from_brcm(self):
        '''
        Tests the :cls:`buildingspy.rc_models.rc_model.RcModel`
        class.
        '''
        rc = RcModel()
        
        # Try to open non existing file
        self.assertFalse(rc.load_from_brcm("unknownFile"))
        
        # Try to open wrong file (not a .mat)
        self.assertFalse(rc.load_from_brcm(self.wrong_template))
        
        # Try to open wrong file (keys missing)
        self.assertFalse(rc.load_from_brcm(self.wrong_mat_file))
        
        # Try to open correct file
        self.assertTrue(rc.load_from_brcm(self.correct_mat_file))
        
        # Get the values just set from the mat file
        np.testing.assert_array_almost_equal(np.ones((2,2)), rc.get_A(), 4,\
                                             "Matrix A is different")
        np.testing.assert_array_almost_equal(np.ones((2,4)), rc.get_B(), 4,\
                                             "Matrix B is different")
        zones_expected = np.ones((5,2))
        zones_expected[:,0] *= 11.0
        zones_expected[:,1] *= 33.0
        np.testing.assert_array_almost_equal(zones_expected, rc.get_zone_volumes(), 4,\
                                             "Zones volumes are different")
        
    def test_create_model_from_brcm(self):
        '''
        Tests the :cls:`buildingspy.rc_models.rc_model.RcModel`
        class.
        '''
        rc = RcModel()
        
        # Set the dummy templates
        rc.set_templates_details(dir_path = self.temp_dir, rc_model_template = self.dummy_template_rc_model_name,\
                                avg_model_template = self.dummy_template_avg_model_name)
        
        # Open correct .mat file
        self.assertTrue(rc.load_from_brcm(self.correct_mat_file))
        
        # Write the models
        rc.generate_modelica_rc_model(dir_path = self.temp_dir, model_name = "RCmodel", \
                                      description = "This is the description of the RC model")
        
        rc.generate_modelica_avg_model(dir_path = self.temp_dir, model_name = "AvgModel", \
                                      description = "This is the description of the AVG model")
        
        
        # Read the generated files
        self.assertTrue(os.path.exists(self.dummy_template_avg_model_path), "The average model has not been created")
        self.assertTrue(os.path.exists(self.dummy_template_rc_model_path), "The RC model has not been created")
        
        with open(os.path.join(self.temp_dir, "RCmodel.mo"), "r") as f:
            modelRC = f.read()
            expected_model = "RCmodel\n"
            expected_model += "This is the description of the RC model\n"
            expected_model += "[1.000000, 1.000000; 1.000000, 1.000000]\n"
            expected_model += "[1.000000, 1.000000, 1.000000, 1.000000; 1.000000, 1.000000, 1.000000, 1.000000]"
            
            self.assertEqual(expected_model, modelRC, "The RC model is different from the expected one")
            
        with open(os.path.join(self.temp_dir, "AvgModel.mo"), "r") as f:
            modelAvg = f.read()
            expected_model = "AvgModel\n"
            expected_model += "This is the description of the AVG model\n"
            expected_model += "{0.200000, 0.200000, 0.200000, 0.200000, 0.200000}\n"
            expected_model += "5"
            
            self.assertEqual(expected_model, modelAvg, "The AVG model is different from the expected one")
        
        
if __name__ == '__main__':
    unittest.main()

