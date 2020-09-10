#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

  Class that translates and simulates a Modelica model with OPTIMICA.

  Note that because OPTIMICA and JModelica have a similar API, and because
  they are invoked by the same script, this class
  should also work for JModelica.

  For a similar class that uses Dymola, see :func:`buildingspy.simulate.Dymola`.

"""

#
# import from future to make Python2 behave like Python3
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
#from builtins import *
from io import open
# end of from future import

import buildingspy.simulate.base_simulator as bs

try:
    # Python 2
    basestring
except NameError:
    # Python 3 or newer
    basestring = str


class Optimica(bs._BaseSimulator):
    """Class to simulate a Modelica model with OPTIMICA.

    :param modelName: The name of the Modelica model.
    :param outputDirectory: An optional output directory.
    :param packagePath: An optional path where the Modelica ``package.mo`` file is located.

    If the parameter ``outputDirectory`` is specified, then the
    output files and log files will be moved to this directory
    when the simulation is completed.
    Outputs from the python functions will be written to ``outputDirectory/BuildingsPy.log``.

    If the parameter ``packagePath`` is specified, then this directory
    and all its subdirectories will be copied to a temporary directory when running the simulations.

    """

    def __init__(self, modelName, outputDirectory='.', packagePath=None):
        import buildingspy.io.reporter as reporter
        import os

        super().__init__(
            modelName=modelName,
            outputDirectory=outputDirectory,
            packagePath=packagePath,
            outputFileList=['*.fmu'],
            logFileList=['BuildingsPy.log', '*_log.txt'])

        self.setSolver("CVode")
        self._MODELICA_EXE = 'jm_ipython.sh'
        self.setResultFile(f"{modelName.replace('.', '_')}_result")

        self._result_filter = []
        self._generate_html_diagnostics = False
        self._debug_solver = False

    def addParameters(self, dictionary):
        """Adds parameter declarations to the simulator.

        :param dictionary: A dictionary with the parameter values

        Usage: Type
           >>> from buildingspy.simulate.Optimica import Optimica
           >>> s=Optimica("myPackage.myModel", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.addParameters({'PID.k': 1.0, 'valve.m_flow_nominal' : 0.1})
           >>> s.addParameters({'PID.t': 10.0})

        This will add the three parameters ``PID.k``, ``valve.m_flow_nominal``
        and ``PID.t`` to the list of model parameters.

        For parameters that are arrays, use a syntax such as
           >>> from buildingspy.simulate.Optimica import Optimica
           >>> s = Optimica("MyModelicaLibrary.Examples.Constants", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.addParameters({'const1.k' : [2, 3]})
           >>> s.addParameters({'const2.k' : [[1.1, 1.2], [2.1, 2.2], [3.1, 3.2]]})

        Do not use curly brackets for the values of parameters, such as
        ``s.addParameters({'const1.k' : {2, 3}})``
        as Python converts this entry to ``{'const1.k': set([2, 3])}``.

        """
        self._parameters_.update(dictionary)
        return

    def getParameters(self):
        """Returns a list of parameters as (key, value)-tuples.

        :return: A list of parameters as (key, value)-tuples.

        Usage: Type
           >>> from buildingspy.simulate.Optimica import Optimica
           >>> s=Optimica("myPackage.myModel", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.addParameters({'PID.k': 1.0, 'valve.m_flow_nominal' : 0.1})
           >>> s.getParameters()
           [('PID.k', 1.0), ('valve.m_flow_nominal', 0.1)]
        """
        return list(self._parameters_.items())

    def addModelModifier(self, modelModifier):
        """Adds a model modifier.

        :param dictionary: A model modifier.

        Usage: Type
           >>> from buildingspy.simulate.Optimica import Optimica
           >>> s=Optimica("myPackage.myModel", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.addModelModifier('redeclare package MediumA = Buildings.Media.IdealGases.SimpleAir')

        This method adds a model modifier. The modifier is added to the list
        of model parameters. For example, the above statement would yield the
        command
        ``simulateModel(myPackage.myModel(redeclare package MediumA = Buildings.Media.IdealGases.SimpleAir), startTime=...``

        """
        self._modelModifiers_.append(modelModifier)
        return

    def simulate(self):
        """Translates and simulates the model.

        This method
          1. Deletes output files
          2. Writes a script to simulate the model.
          3. Starts the Modelica simulation environment.
          4. Translates and simulates the model.
          5. Closes the Modelica simulation environment.

        This method requires that the directory that contains the executable ``jm_ipython.sh``
        is on the system PATH variable. If it is not found, the function returns with
        an error message.

        """
        return self._translate_and_simulate(simulate=True)

    def translate(self):
        """Translates the model to generate a Functional Mockup Unit.

        This method
          1. Deletes output files
          2. Writes a script to simulate the model.
          3. Starts the Modelica simulation environment.
          4. Translates the model.
          5. Closes the Modelica simulation environment.

        This method requires that the directory that contains the executable ``jm_ipython.sh``
        is on the system PATH variable. If it is not found, the function returns with
        an error message.

        """
        return self._translate_and_simulate(simulate=False)

    def _translate_and_simulate(self, simulate):
        """ Translates and optionally simulates the model.

        This method
          1. Deletes output files
          2. Writes a script to simulate the model.
          3. Starts the Modelica simulation environment.
          4. Translates and simulates the model.
          5. Closes the Modelica simulation environment.

        This method requires that the directory that contains the executable ``jm_ipython.sh``
        is on the system PATH variable. If it is not found, the function returns with
        an error message.

        """
        import os
        import shutil
        import jinja2
        import datetime

        # Delete output files
        self.deleteOutputFiles()

##        # Get directory name. This ensures for example that if the directory is called xx/Buildings
##        # then the simulations will be done in tmp??/Buildings
##        worDirLib = self._create_worDir()

        # Optimica is usually started on level higher than the Buildings library
##        worDir = os.path.abspath(os.path.join(worDirLib, os.path.pardir))
        worDir = self._outputDir_

        self._simulateDir_ = worDir
        # Copy directory
##        shutil.copytree(os.path.abspath(self._packagePath), worDirLib,
##                        ignore=shutil.ignore_patterns('*.svn', '*.git'))

        # Construct the model instance with all parameter values
        # and the package redeclarations
        dec = self._declare_parameters()
        dec.extend(self._modelModifiers_)

        if len(dec) == 0:
            model_modifier = ""
        else:
            model_modifier = '({dec})'.format(mn=self.modelName, dec=','.join(dec))

        file_name = os.path.join(worDir, "{}.py".format(self.modelName.replace(".", "_")))
##        self._time_stamp_old_files = datetime.datetime.now()
        with open(file_name, mode="w", encoding="utf-8") as fil:
            path_to_template = os.path.join(
                os.path.dirname(__file__), os.path.pardir, "development")
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(path_to_template))

            template = env.get_template("optimica_run.template")

            # Note that filter argument must respect glob syntax ([ is escaped with []]) + JModelica mat file
            # stores matrix variables with no space e.g. [1,1].
            txt = template.render(
                model=self.modelName,
                model_modifier=model_modifier,
                ncp=self._simulator_.get('numberOfIntervals'),
                rtol=self._simulator_.get('eps'),
                solver=self._simulator_.get('solver'),
                start_time=self._simulator_.get('t0') if self._simulator_.get(
                    't0') is not None else 'mod.get_default_experiment_start_time()',
                final_time=self._simulator_.get('t1') if self._simulator_.get(
                    't1') is not None else 'mod.get_default_experiment_stop_time()',
                result_file_name=f"{self._simulator_.get('resultFile')}.mat",
                simulate=simulate,
                time_out=-1,  # timeout is handled by BuildingsPy directly and not by the generated script
                filter=self._result_filter,
                generate_html_diagnostics=self._generate_html_diagnostics,
                debug_solver=self._debug_solver)

            fil.write(txt)

        #osEnv = self.prependToModelicaPath(os.environ.copy(), os.getcwd())

#        print(f"****** Starting simulation in {worDir}")
        try:
            super()._runSimulation(["jm_ipython.sh", file_name],
                                   self._simulator_.get('timeout'),
                                   worDir,
                                   env=None)

            self._check_simulation_errors(worDir)
##            self._copyNewFiles(worDir)
##            self._deleteTemporaryDirectory(worDir)

        except Exception as e:  # Catch all possible exceptions
            em = f"Simulation failed in '{worDir}'\n   Exception: {e}.\n   You need to delete the directory manually.\n"
            self._reporter.writeError(em)

    def setResultFilter(self, filter):
        """ Specifies a list of variables that should be stored in the result file.

        :param: A list of variables that should be stored in the result file.

        Usage: To list only the variables of the instance `myStep.source`, type

           >>> from buildingspy.simulate.Optimica import Optimica
           >>> s=Optimica("myPackage.myModel", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.setResultFilter(["myStep.source.*"])

        To list all variables whose name ends in ``y``, type

           >>> from buildingspy.simulate.Optimica import Optimica
           >>> s=Optimica("myPackage.myModel", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.setResultFilter(["*y"])

        """
        self._result_filter = filter

    def setSolver(self, solver):
        """Sets the solver.

        :param solver: The name of the solver.

        The default solver is *CVode*.
        """
        solvers = [
            "CVode",
            "Radau5ODE",
            "RungeKutta34",
            "Dopri5",
            "RodasODE",
            "LSODAR",
            "ExplicitEuler",
            "ImplicitEuler"]
        if solver in solvers:
            self._simulator_.update(solver=solver)
        else:
            self._reporter.writeWarning(
                f"Solver {solver} is not supported. Supported are: {', '.join(solvers)}.")
        return

    def generateHtmlDiagnostics(self, generate=False):
        """ If set to `true`, html diagnostics will be generated.

        The html diagnostics will be generated in
        a directory whose name is equal to the model name,
        with ``.`` replaced by ``_``, and the string
        ``_html_diagnostics`` appended.

        .. note:: For large models, this can generate huge files
                  and increase translation time.
        """
        self._generate_html_diagnostics = generate

    def generateSolverDiagnostics(self, generate=False):
        """ If set to `true`, solver debug information will be generated
            and displayed.

        This is currently only used for the `CVode` solver.

        .. note:: This can generate huge files
                  and increase simulation time.
        """
        self._debug_solver = generate

    def _check_simulation_errors(self, worDir):
        """ Method that checks if errors occured during simulation.
        """
        import os
        import json

        from buildingspy.io.outputfile import get_errors_and_warnings
        logFil = self.modelName.replace(".", "_") + '_buidingspy.json'
        path_to_logfile = os.path.join(worDir, logFil)
        if not os.path.exists(path_to_logfile):
            msg = f"Expected log file {path_to_logfile}, but file does not exist."
            self._reporter.writeError(msg)
            raise IOError(msg)

        with open(path_to_logfile, 'r') as f:
            js = json.loads(f.read())
            for step in ['translation', 'simulation']:
                if step not in js:
                    msg = f"Failed to invoke {step} for model {self.modelName}."
                    self._reporter.writeError(msg)
                    return
                if js[step]['success'] is not True:
                    msg = f"The {step} of {self.modelName} failed. Check {logFil}"
                    self._reporter.writeError(msg)
                    return
        return

# Classes that are inherited. These are listed here
# so that they appear in the documentation.

    def setPackagePath(self, packagePath):
        super().setPackagePath(packagePath)

    def getOutputDirectory(self):
        return super().getOutputDirectory()

    def setOutputDirectory(self, outputDirectory):
        return super().setOutputDirectory(outputDirectory)

    def getPackagePath(self):
        return self._packagePath

    def setStartTime(self, t0):
        super().setStartTime(t0)
        return

    def setStopTime(self, t1):
        super().setStopTime(t1)
        return

    def setTolerance(self, eps):
        super().setTolerance(eps)

    def setNumberOfIntervals(self, n=500):
        super().setNumberOfIntervals(n=n)

    def deleteSimulateDirectory(self):
        super().deleteSimulateDirectory()
        return

    def setTimeOut(self, sec):
        super().setTimeOut(sec=sec)

    def setResultFile(self, resultFile):
        super().setResultFile(resultFile=resultFile)
        return

    def deleteOutputFiles(self):
        super().deleteOutputFiles()
        self._deleteFiles([self._simulator_.get('resultFile') + "_result.mat"])

    def deleteLogFiles(self):
        super().deleteLogFiles()
