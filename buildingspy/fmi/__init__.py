"""
This module provides functions to analyse FMUs.

"""


def get_dependencies(fmu_file_name):
    """Return the input and state dependencies of an FMU as a dictionary.

    :fmu_file_name: Name of the FMU file.

    Extracts the FMU ``fmu_file_name`` to a temporary directory,
    reads its `modelDescription.xml` file,
    and returns a dictionary with the dependencies of derivatives,
    outputs and initial unknowns.

    For example, if applied to an FMU that encapsulates the Modelica model

    .. code-block:: modelica

       block IntegratorGain "Block to demonstrate the FMU export"
         parameter Real k = -1 "Gain";
         Modelica.Blocks.Interfaces.RealInput u "Input";
         Modelica.Blocks.Interfaces.RealOutput y1
           "Output that depends on the state";
         Modelica.Blocks.Interfaces.RealOutput y2
           "Output that depends on the input";
         Real x(start=0) "State";
       equation
         der(x) = u;
         y1 = x;
         y2 = k*u;
       end IntegratorGain;

    The output will be as follows:

       >>> import os
       >>> import json
       >>> import buildingspy.fmi as f
       >>> fmu_name=os.path.join("buildingspy", "tests", "fmi", "IntegratorGain.fmu")
       >>> d=f.get_dependencies(fmu_name)
       >>> print(json.dumps(d, indent=2, separators=(',', ': '), sort_keys=True))
       {
         "Derivatives": {
           "der(x)": [
             "u"
           ]
         },
         "InitialUnknowns": {
           "der(x)": [
             "u"
           ],
           "y1": [
             "x"
           ],
           "y2": [
             "k",
             "u"
           ]
         },
         "Outputs": {
           "y1": [
             "x"
           ],
           "y2": [
             "u"
           ]
         }
       }

    """
    import tempfile
    import os
    import zipfile
    import shutil
    import xml.etree.ElementTree as ET

    # Unzip the fmu
    dirNam = tempfile.mkdtemp(prefix='tmp-buildingspy-fmi-')
    zip_file = zipfile.ZipFile(fmu_file_name)
    zip_file.extract('modelDescription.xml', dirNam)
    zip_file.close()
    # Parse its modelDescription.xml file
    xml_file = os.path.join(dirNam, 'modelDescription.xml')
    tree = ET.parse(xml_file)
    shutil.rmtree(dirNam)
    root = tree.getroot()

    # Create a dict that links the variable number to variable name
    variable_names = {}
    variable_counter = 0
    for model_variables in root.iter('ModelVariables'):
        this_root = model_variables
        for child in this_root:
            variable_counter += 1
            variable_names[variable_counter] = child.attrib['name']

    # Read dependencies from xml and write to dependency_graph
    dependencies = {}

    # Get all dependencies of the FMU and store them in a hierarchical dictionary
    for typ in ['InitialUnknowns', 'Outputs', 'Derivatives']:
        dependencies[typ] = {}
        for children in root.iter(typ):
            #this_root = outputs
            for child in children:
                variable = variable_names[int(child.attrib['index'])]
                # Exclude CPUtime and EventCounter, which are written
                # depending on the Dymola 2018FD01 configuration.
                if variable not in ["CPUtime", "EventCounter"]:
                    dependencies[typ][variable] = []
                    for ind_var in child.attrib['dependencies'].split(' '):
                        # If variables depend on nothing, there will be an empty string, these
                        # are therefore excluded.
                        if ind_var.strip() != "":
                            dependencies[typ][variable].append(variable_names[int(ind_var)])
    return dependencies
