#!/usr/bin/env python
import os
import scipy.io
import jinja2
import datetime
import logging

# Set up a default log configuration that writes to a log file named 'buildingspy.log'
# The log file will be saved in the current directory
logging.basicConfig(format = "%(asctime)s %(name)-12s %(levelname)-8s %(message)s", \
                    level = logging.DEBUG,\
                    datefmt = "%m-%d %H:%M",
                    filename = os.path.join(os.curdir, "buildingspy.log"),
                    filemode = "w")

# Define handler that writes messages higher than INFO to the console
console = logging.StreamHandler()
# Set the new level for this logger
console.setLevel(level = logging.INFO)
# Set the format of the message
formatter = logging.Formatter("%(name)-12s %(levelname)-8s %(message)s")
console.setFormatter(formatter)
# Add to the default root logger
logging.getLogger("").addHandler(console)

# Generate the logger for this module
logger = logging.getLogger(__name__)

class RcModel:
    """This class represents a Resistive-Capacitance (RC)
    model that represents a simplification of the envelope of a
    building. The model can be generated using outputs
    provided by the BRCM Matlab toolbox and it generates an equivalent
    Modelica model.
    
    This class generates also a model that computes the average return 
    temperature of the zones. The average is based on a weighted average
    that uses as weights the volumes of the different zones.
    
    """

    def __init__(self):
        
        logger.debug("Initialize RcModel object")
        
        # State and input matrices
        self._A_ = None
        self._B_ = None
        
        # Names of the state variables and disturbances
        self._states_names_ = []
        self._dist_names_ = []
        
        # Array that contains the volumes of the zones
        self._zones_ = None
        
        # The location of the folder that contains the templates
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self._templates_dir_ = os.path.abspath(os.path.join(dir_path, "Templates"))
        
        # The names of the templates
        self._model_template_name_ = "model.jinja"
        self._model_avg_template_name_ = "model_average.jinja"

    def set_templates_details(self, dir_path = None, rc_model_template = None, avg_model_template = None):
        """This method defines the location and the names of the template files.
        
        :dir: The path of the directory that contains the ``*.jinja`` template files.
        :rc_model_template: The name of the template for the RC model.
        :avg_model_template: The name of the template for the average model. 
        
        If the directory or the files do not exist an exception is raised.
        If the template files do not have the ``.jinja`` extension an exception
        is raised.
        """
        
        logger.debug("Define template details")
        
        if dir_path != None:
            if os.path.exists(dir_path):
                logger.debug("Set template dir path to: %s" % str(dir_path))
                self._templates_dir_ = dir_path
            else:
                logger.error("The templates directory %s does not exist" % str(dir_path))
                raise OSError("The templates directory %s does not exist" % str(dir_path))
        
        if rc_model_template != None:
            # Verify is the file exists
            model_template_file = os.path.join(self._templates_dir_, rc_model_template)
            if not os.path.exists(model_template_file):
                msg = "The RC model template %s does not exist" % str(model_template_file)
                logger.error(msg)
                raise OSError(msg)
            else:
                # Verify if the extension is correct
                if rc_model_template.split(".")[-1] != "jinja":
                    msg = "The RC model template %s does not have the .jinja extension" % str(rc_model_template)
                    logger.error(msg)
                    raise ValueError(msg)
                else:
                    logger.debug("Set RC template file to: %s" % str(rc_model_template))
                    self._model_template_name_ = rc_model_template
        
        if avg_model_template != None:
            # Verify is the file exists
            model_template_file = os.path.join(self._templates_dir_, avg_model_template)
            if not os.path.exists(model_template_file):
                msg = "The avg model template %s does not exist" % str(model_template_file)
                logger.error(msg)
                raise OSError(msg)
            else:
                # Verify if the extension is correct
                if avg_model_template.split(".")[-1] != "jinja":
                    msg = "The avg model template %s does not have the .jinja extension" % str(avg_model_template)
                    logger.error(msg)
                    raise ValueError(msg)
                else:
                    logger.debug("Set Avg template file to: %s" % str(avg_model_template))
                    self._model_avg_template_name_ = avg_model_template

    def get_A(self):
        """
        This method returns the ``A`` state matrix
        """
        return self._A_
    
    def get_B(self):
        """
        This method returns the ``B`` input disturbances matrix
        """
        return self._B_
    
    def get_state_names(self):
        """
        This method returns the names of the state variables
        """
        return self._states_names_
    
    def get_disturbances_names(self):
        """
        This method returns the names of the disturbance variables
        """
        return self._dist_names_
    
    def get_zone_volumes(self):
        """
        This method returns an array that contains the volume of each zone
        """
        return self._zones_
    
    def load_from_brcm(self, mat_file_path):
        """This method load the data of a BRCM model exported as a ``*.mat``
        file.
        :mat_file_path: A string that represents the path of the ``*.mat`` files 
        that contains the data generated by the Matlab BRCM toolbox.

        The ``*.mat`` file needs to contain the following variables, otherwise the
        methowill generate an exception.
           
        * ``A``, the state matrix
        * ``Bv``, the input matrix
        * ``zone``, a matrix that contains the volume of each zone
        * ``state_x``, a matrix that contains the description of the states
        * ``state_v``, a matrix that contains the description of the disturbances

        """
        
        # Verify is the file exists
        if not os.path.exists(mat_file_path):
            msg = "The file %s does not exist" % str(mat_file_path)
            logger.error(msg)
            return False
        else:
            # Verify if the extension is correct
            (head, tail) = os.path.split(mat_file_path)
            if tail.split(".")[-1] != "mat":
                msg = "The file %s has the wrong extension, required *.mat files" % str(mat_file_path)
                logger.error(msg)
                return False
        
        # Read the *.mat file
        msg = "Reading file %s" % str(mat_file_path)
        logger.info(msg)
        workspace = scipy.io.loadmat(mat_file_path)
        
        # Check if the workspace contains all the required keywords
        if not self._test_mat_workspace_(workspace):
            msg = "The workspace does not contain the required keywords"
            logger.error(msg)
            return False
        
        msg = "Start reading the data from workspace..."
        logger.info(msg)
        
        # Read the Matrices A, B
        self._A_ = workspace["A"]
        self._B_ = workspace["Bv"]
        
        # Lambda function that extracts strings from object in the mat file
        f_get_string = lambda x: x[0][0]
        
        # Get the vectors that contain the names of the states and disturbances
        self._states_names_ = [f_get_string(x) for x in workspace["state_x"]]
        self._dist_names_ = [f_get_string(x) for x in workspace["state_v"]]
        
        # Get the matrix that contains the zone info
        self._zones_ = workspace["zone"]
        
        msg = "Workspace successfully read"
        logger.info(msg)
        
        return True
        
    def generate_modelica_rc_model(self, dir_path, model_name, description = \
                                   "This is the description of the RC model"):
        """This method generates a Modelica RC model,
        :dir_path: is the path of the foilder where the Modelica model
        should be generated. :model_name: is the name of the model that will be 
        generated.
        
        If successful, this method creates a file called ``<model_name>.mo`` in the
        folder ``<dir_path>/<model_name>.mo``.
        This method uses as templates the ``*.jinja`` files located in the folder
        ``self._templates_dir_``. The templates file is specified by 
        ``self._model_template_name_``.
        
        """
        msg = "Generating RC Modelica model: %s.mo" % str(model_name)
        logger.info(msg)
        
        # Initialize the environment that will be used to create the Modelica file
        # from its template
        loader = jinja2.FileSystemLoader(self._templates_dir_)
        environment = jinja2.Environment(loader = loader) 

        # Load the template for the RC model
        template_model = environment.get_template(self._model_template_name_)
        
        # Create the dictionary that will be used to render the model
        # from the template
        modelName = model_name
        description = description
        As = matrix_to_string(self._A_)
        Bs = matrix_to_string(self._B_)
        keywords = {"modelName": modelName, "description": description, "A": As, "B": Bs}
        keywords["N_zones"] = self._zones_.shape[0]
        keywords["N_states"] = self._A_.shape[0] 
        keywords["N_dist"] = self._B_.shape[1]
        keywords["N_inputs"] = len(self._dist_names_)
        keywords["date_time"] = datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p")
        keywords["state_vars"] = self._states_names_
        keywords["dist_vars"] = self._dist_names_
        keywords["Zones"] = self._zones_
        
        # Create the file path of the model
        model_file_path = os.path.abspath(os.path.join(dir_path, modelName+".mo" ))
        
        # Create the model and save it
        self._dump_template_(template_model, keywords, model_file_path)
        
        return
    
    def generate_modelica_avg_model(self, dir_path, model_name, description = \
                                   "This is the description of the average T model"):
        """This method generates a Modelica model, that computes the average
        temperature of the return air. The average is based on the volumes of each single
        zone.
        
        :dir_path: is the path of the foilder where the Modelica model
        should be generated. :model_name: is the name of the model that will be 
        generated.
        
        If successful, this method creates a file called ``<model_name>.mo`` in the
        folder ``<dir_path>/<model_name>.mo``.
        This method uses as templates the ``*.jinja`` files located in the folder
        ``self._templates_dir_``. The templates file is specified by 
        ``self._model_avg_template_name_``.
        
        """
        msg = "Generate Averaging Modelica model: %s.mo" % str(model_name)
        logger.info(msg)
        
        # Initialize the environment that will be used to create the Modelica file
        # from its template
        loader = jinja2.FileSystemLoader(self._templates_dir_)
        environment = jinja2.Environment(loader = loader) 

        # Load the template for the RC model
        template_model = environment.get_template(self._model_avg_template_name_)
        
        # Create the dictionary that will be used to render the model
        # from the template
        modelName = model_name
        description = description
        keywords = {"modelName": modelName, "description": description}
        keywords["N_zones"] = self._zones_.shape[0]
        keywords["Zones"] = self._zones_
        keywords["date_time"] = datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p")
        keywords["weigths"] = matrix_to_string(self._zones_[:,0]/sum(self._zones_[:,0]))
        
        # Create the file path of the model
        model_file_path = os.path.abspath(os.path.join(dir_path, modelName+".mo" ))
        
        # Create the model and save it
        self._dump_template_(template_model, keywords, model_file_path)
        
        return
    
    @staticmethod
    def _dump_template_(template, keywords, model_file_path):
        """
        This function renders a template and then save it to a file.
        
        :template: is the template used to renders the model (a ``*.jinja`` file)
        :keywords: is the dictionary of key-values used to generate the model using the template
        :model_file_name: is the file path of the model that will be generated
        """
        
        # Render the model
        modelicaText = template.render(keywords)
        
        msg = "\nContent of the Modelica generated model:\n%s" % str(modelicaText)
        logger.debug(msg)
        
        # Save the model to a file
        with open(model_file_path, "w") as f_w:
            f_w.write(modelicaText)
        
        msg = "Model saved as %s" % str(model_file_path)
        logger.info(msg)
        
        return
        
    @staticmethod
    def _test_mat_workspace_(workspace):
        """This method tests if the workspace imported by a ``*.mat`` file
        contains the necessary keywords. If the leywords are all present in the
        workspace the method returns ``True``, otherwise it returns ``False```.
        """
        keywords = ["A", "Bv", "zone", "state_x", "state_v"]
        
        try:
            for k in keywords:
                workspace[k]
            return True
        except KeyError, e:
            # Error, one of the keywords is not part of the workspace
            msg = "Missing keyword in the workspace: %s" % str(e)
            logger.exception(msg)
            return False

def matrix_to_string(M):
    """
    :M: is a Numpy matrix or array.
    This function converts ``M`` to a string that can
    be interpreted as a matrix or an array in Modelica.
    
    For example
    ```
    [[1,2],[2,3]]
    ```
    becomes
    ```
    "[1.000000, 2.000000; 2.000000, 3.000000]"
    ```
    
    while
    
    ```
    [1,2,2,3]
    ```
    becomes
    ```
    "{1.000000, 2.000000, 2.000000, 3.000000}"
    ```
    
    """
    try:
        # It's a Matrix
        (rows, cols) = M.shape
        Ms = "["
        for i in range(rows):
            for j in range(cols):
                Ms += "%.6f" % M[i,j]
                if j < cols-1:
                    Ms += ", "
                else:
                    if i < rows -1:
                        Ms += "; "
                    else:
                        Ms += "]"
    except ValueError:
        # It's an array
        cols = len(M)
        Ms = "{"
        for i in range(cols):
            Ms += "%.6f" % M[i]
            if i < cols-1:
                Ms += ", "
            else:
                Ms += "}"
                
    return Ms
