#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
from jinja2 import Template
import random
import string
import os

import unittest

MO_TEMPLATE = """model {{model_name}}
  annotation ({{experiment}}
    __Dymola_Commands(file="Resources/Scripts/Dymola/Examples/{{model_name}}.mos"
    "Simulate and plot"),
    Documentation(info="<html>
    This model is used in the regression test
    to set boolean parameters.
    </html>"));
end {{model_name}}
"""

MOS_TEMPLATE = """simulateModel("MyModelicaLibrary.Examples.{{model_name}}", method="dassl", {{parameter}} resultFile="{{model_name}}");
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
        import buildingspy.development.validator as v
        val = v.Validator()
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        # Get a list whose elements are the error strings
        errStr = val.validateHTMLInPackage(myMoLib)
        self.assertEqual(len(errStr), 0)
        # Test a package that does not exist
        self.assertRaises(ValueError, val.validateHTMLInPackage, "non_existent_modelica_package")

    def run_case(self, val, mod_lib, model_name, mo_param, mos_param, err_msg):
        """
        Create and validate mo and mos files


        :param: val Validator object.
        :param: mod_lib Path to model library.
        :param: model_name Name of model.
        :param: mo_param Parameter of mo file.
        :param: mos_param Parameter of mos file.
        :param: err_msg Expected error message.

        """

        path_mo = os.path.join(mod_lib, 'Examples', model_name + '.mo')

        with open(path_mo, mode="w", encoding="utf-8") as mo_fil:
            mo_fil.write(Template(MO_TEMPLATE).render(experiment=mo_param, model_name=model_name))

        path_mos = os.path.join(mod_lib, 'Resources', 'Scripts', 'Dymola',
                                'Examples', model_name + '.mos')

        with open(path_mos, mode="w", encoding="utf-8") as mos_fil:
            mos_fil.write(
                Template(MOS_TEMPLATE).render(
                    experiment=mos_param,
                    model_name=model_name))

        with self.assertRaises(ValueError) as context:
            val.validateExperimentSetup(mod_lib)
            self.assertTrue(err_msg in str(context.exception))

        # Delete created files
        os.remove(path_mo)
        os.remove(path_mos)

    def test_validateExperimentSetup(self):

        import buildingspy.development.validator as v
        val = v.Validator()
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")

        #########################################
        # Checking default library
        val.validateExperimentSetup(myMoLib)

        #########################################
        # Checking missing experiment
        self.run_case(val, myMoLib, "Test1", "", "tolerance=1e-6,",
                      "without experiment annotation.")

        ###########################################
        # Checking missing tolerance in mos file
        self.run_case(val, myMoLib, "Test2", "experiment(Tolerance=1e-6, StopTime=1.0),",
                      "", "A minimum tolerance of 1e-6 is required for OPTIMICA.")

        ###########################################
        # Checking missing tolerance in mo file
        self.run_case(val, myMoLib, "Test3", "experiment(StopTime=1.0),", "stopTime=1.0,",
                      "A minimum tolerance of 1e-6 is required for OPTIMICA.")

        ###########################################
        # Checking tolerances mismatch
        self.run_case(val, myMoLib, "Test4", "experiment(Tolerance=1e-6, StopTime=1.0),",
                      "tolerance=1e-3, stopTime=1.0,",
                      "The tolerance found is bigger than 1e-6")

        #########################################
        # Checking tolerances mismatch
        self.run_case(val, myMoLib, "Test5", "experiment(Tolerance=1e-3, StopTime=1.0),",
                      "tolerance=1e-6, stopTime=1.0,",
                      "different from the (default) value=1e-6")

        ###########################################
        # Checking stopTime mismatch
        self.run_case(val, myMoLib, "Test6", "experiment(Tolerance=1e-6, StopTime=2.0),",
                      "tolerance=1e-6,",
                      "The value of StopTime=2.0 is different from the (default) value=1.0")

        ###########################################
        # Checking stopTime mismatch
        self.run_case(val, myMoLib, "Test7", "experiment(Tolerance=1e-6, StopTime=30.0),",
                      "tolerance=1e-6, stopTime=15,",
                      "The value of StopTime=30.0 is different from the")

        ###########################################
        # Checking wrong literal in StopTime
        self.run_case(val, myMoLib, "Test8", "experiment(Tolerance=1e-6, StopTime=2*5),",
                      "tolerance=1e-6, stopTime=10,",
                      "contains invalid expressions such as")

        ###########################################
        # Checking stopTime mismatch
        self.run_case(
            val,
            myMoLib,
            "Test9",
            "experiment(Tolerance=1e-6, StartTime=2, StopTime=1.0),",
            "tolerance=1e-6, stopTime=1.0,",
            "The value of StartTime=2 is different from the (default) value=0.0")

        ###########################################
        # Checking stopTime mismatch
        self.run_case(val, myMoLib, "Test10", "experiment(Tolerance=1e-6, StopTime=1.0),",
                      "tolerance=1e-6, startTime=2.0, stopTime=1.0,",
                      "The parameter name startTime is defined in the mos file")

        ###########################################
        # Checking stopTime mismatch
        self.run_case(
            val,
            myMoLib,
            "Test11",
            "experiment(Tolerance=1e-6, StartTime=15, StopTime=1.0),",
            "tolerance=1e-6, startTime=10, stopTime=1.0,",
            "The value of StartTime=15 is different from the")

        ###########################################
        # Checking missing StopTime in mo mismatch
        self.run_case(val, myMoLib, "Test12", "experiment(Tolerance=1e-6),",
                      "tolerance=1e-6,",
                      "without StopTime in experiment annotation")

        ###########################################
        # Checking wrong data type that can cause an overflow
        # In OPTIMICA's CI testing, the maximum integer is 2147483647
        self.run_case(
            val,
            myMoLib,
            "Test13",
            "experiment(Tolerance=1e-6, StartTime=0, StopTime=2147483648),",
            "tolerance=1e-6, startTime=0, stopTime=2147483648,",
            "Integer overflow: Integers can be -2147483648 to 2147483647, received")
        self.run_case(
            val,
            myMoLib,
            "Test14",
            "experiment(Tolerance=1e-6, StartTime=-2147483649, StopTime=0),",
            "tolerance=1e-6, startTime=-2147483649, stopTime=0,",
            "Integer overflow: Integers can be -2147483648 to 2147483647, received")

    def test_validateHyperlinks_lib(self):
        """
        Test whether the `.mo` files point only have valid hyperlinks
        """
        # Test My ModelicaLibrary
        import buildingspy.development.validator as v
        val = v.Validator()
        myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
        # Get a list whose elements are the error strings
        errStr = val.validateHyperlinks(myMoLib)
        self.assertEqual(len(errStr), 0)

    def test_validateHyperlinks_new_file(self):
        """
        Test whether the `.mo` files point only have valid hyperlinks
        """
        import tempfile
        # Test My ModelicaLibrary
        import buildingspy.development.validator as v

        # Create a file with broken hyperlink
        with tempfile.TemporaryDirectory(prefix="tmp-buildingspy-") as tmpdirname:

            test_file = os.path.join(tmpdirname, "tmp_validate_hyperlinks.mo")
            with open(test_file, 'w') as f:
                f.write("""
                        some text
                        some other text
                        <img href=\\"modelica://link/to/nonexisting/image.png\\"/>
                        some other text
                        """)

            val = v.Validator()
            myMoLib = tmpdirname
            # Get a list whose elements are the error strings
            errStr = val.validateHyperlinks(myMoLib)
            self.assertEqual(len(errStr), 1)


if __name__ == '__main__':
    unittest.main()
