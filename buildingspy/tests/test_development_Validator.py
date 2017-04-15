#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# import from future to make Python2 behave like Python3
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import *
from io import open
from jinja2 import Template 
import random, string, os
# end of from future import

import unittest

MO_TEMPLATE="""model {{model_name}}
  annotation ({{experiment}}
    __Dymola_Commands(file="Resources/Scripts/Dymola/Examples/{{model_name}}.mos"
    "Simulate and plot"),
    Documentation(info="<html>
    This model is used in the regression test
    to set boolean parameters.
    </html>"));
end {{model_name}}
"""

MOS_TEMPLATE="""simulateModel("MyModelicaLibrary.Examples.{{model_name}}", method="dassl", {{parameter}} resultFile="{{model_name}}");
createPlot(
  id=1, 
  y={"p1", "p2"}
)
"""

class Test_development_Validator(unittest.TestCase):
    """
       This class contains the unit tests for
       :mod:`buildingspy.development.Validator`.
    """

    def test_validateHTMLInPackage(self):
        import os
        import buildingspy.development.validator as v
        val = v.Validator()
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        # Get a list whose elements are the error strings
        errStr = val.validateHTMLInPackage(myMoLib)
        self.assertEqual(len(errStr), 0)
        # Test a package that does not exist
        self.assertRaises(ValueError, val.validateHTMLInPackage, "non_existent_modelica_package")
        
    def run_case(self, val, mod_lib, mo_param, mos_param, err_msg):
        """
        Create and validate mo and mos files on the fly  
        
        
        :param: val Validator object.
        :param: mod_lib Path to model library.
        :param: mo_param Parameter of mo file.
        :param: mos_param Parameter of mos file.    
        :param: mos_param Parameter of mos file.    
        :param: mos_param Expected error message. 
        
        """
        
        model_name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        
        path_mo=os.path.join(mod_lib, 'Examples', model_name+'.mo')
        template= Template(MO_TEMPLATE)
        output_res = template.render(experiment=mo_param, model_name=model_name)
        
        with open(path_mo, 'w') as mo_fil:
            mo_fil.write(output_res)
        mo_fil.close()
        
        path_mos=os.path.join(mod_lib, 'Resources', 'Scripts', 'Dymola', 
                              'Examples', model_name+'.mos')
        if(os.path.isfile(path_mos)):
            os.remove(path_mo)
        template= Template(MOS_TEMPLATE)
        output_res = template.render(parameter=mos_param, model_name=model_name)
        
        with open(path_mos, 'w') as mos_fil:
            mos_fil.write(output_res)
        mos_fil.close()
        
        with self.assertRaises(ValueError) as context:
            val.validateModelParameters(mod_lib)
        
        for path in [path_mo, path_mos]:
            os.remove(path)
        self.assertTrue(err_msg in str(context.exception))


    def test_validateModelParameters(self):
        
        import buildingspy.development.validator as v
        val = v.Validator()
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        
        #########################################
        #Checking default library
        val.validateModelParameters(myMoLib)
        
        #########################################
        # Checking missing experiment
        self.run_case(val, myMoLib, "", "tolerance=1e-6,",
                      "without experiment annotation.")
        
        ###########################################
        #Checking missing tolerance in mos file
        self.run_case(val, myMoLib, "experiment(Tolerance=1e-6),",
                      "", "A maximum tolerance of 1e-6 is required")  
         
        ###########################################
        # Checking missing tolerance in mo file
        self.run_case(val, myMoLib, "experiment(StopTime=1.0),",
                      "stopTime=1.0,", "A maximum tolerance of 1e-6 is required by JModelica.")   
                     
        ###########################################
        # Checking tolerances mismatch
        self.run_case(val, myMoLib, "experiment(Tolerance=1e-6),",
                                        "tolerance=1e-3,",
                                        "The tolerance found is bigger than 1e-6")
   
        #########################################
        # Checking tolerances mismatch
        self.run_case(val, myMoLib, "experiment(Tolerance=1e-3),", "tolerance=1e-6,",
                      "different from the (default) value=1e-6")            
           
        ###########################################
        # Checking stopTime mismatch 
        self.run_case(val, myMoLib, "experiment(Tolerance=1e-6, StopTime=2.0),",
                      "tolerance=1e-6,",
                      "The value of StopTime=2.0 is different from the (default) value=1.0") 
          
        ###########################################
        # Checking stopTime mismatch 
        self.run_case(val, myMoLib, "experiment(Tolerance=1e-6),",
                      "tolerance=1e-6, stopTime=10,",
                      "parameter name stopTime is defined in") 

if __name__ == '__main__':
    unittest.main()

