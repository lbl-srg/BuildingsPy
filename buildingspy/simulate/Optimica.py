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
    :param simulator: The simulation engine. Currently, the only supported value is ``dymola``.
    :param outputDirectory: An optional output directory.
    :param packagePath: An optional path where the Modelica ``package.mo`` file is located.

    If the parameter ``outputDirectory`` is specified, then the
    output files and log files will be moved to this directory
    when the simulation is completed.
    Outputs from the python functions will be written to ``outputDirectory/BuildingsPy.log``.

    If the parameter ``packagePath`` is specified, the Simulator will copy this directory
    and all its subdirectories to a temporary directory when running the simulations.

    .. note:: Up to version 1.4, the environmental variable ``MODELICAPATH``
              has been used as the default value. This has been changed as
              ``MODELICAPATH`` can have multiple entries in which case it is not
              clear what entry should be used.
    """

    def __init__(self, modelName, outputDirectory='.', packagePath=None):
        import buildingspy.io.reporter as reporter
        import os

        super().__init__(
            modelName=modelName,
            outputDirectory=outputDirectory,
            packagePath=packagePath,
            outputFileList = ['*.fmu'],
            logFileList = ['BuildingsPy.log', '*_log.txt'])

        self.setSolver("CVode")
        self._MODELICA_EXE = 'jm_ipython.sh'

        self.setResultFile(f"{modelName.replace('.', '_')}_result")

        self._result_filter = []
        self._generate_html_diagnostics = False

    def simulate(self):
        """Simulates the model.

        This method
          1. Deletes output files
          2. Copies the current directory, or the directory specified by the ``packagePath``
             parameter of the constructor, to a temporary directory.
          3. Writes a script to the temporary directory.
          4. Starts the Modelica simulation environment from the temporary directory.
          5. Translates and simulates the model.
          6. Closes the Modelica simulation environment.
          7. Copies output files and deletes the temporary directory.

        This method requires that the directory that contains the executable *dymola*
        is on the system PATH variable. If it is not found, the function returns with
        an error message.

        """
        return self._translate_and_simulate(simulate=True)


    def translate(self):
        """Translates the model.

        This method
          1. Deletes output files
          2. Copies the current directory, or the directory specified by the ``packagePath``
             parameter of the constructor, to a temporary directory.
          3. Writes a script to the temporary directory.
          4. Starts the Modelica simulation environment from the temporary directory.
          5. Translates the model.
          6. Closes the Modelica simulation environment.
          7. Copies output files and deletes the temporary directory.

        This method requires that the directory that contains the executable *dymola*
        is on the system PATH variable. If it is not found, the function returns with
        an error message.

        """
        return self._translate_and_simulate(simulate=False)


    def _translate_and_simulate(self, simulate):
        """ Translates and optionally simulates the model.

        This method
          1. Deletes output files
          2. Copies the current directory, or the directory specified by the ``packagePath``
             parameter of the constructor, to a temporary directory.
          3. Writes a script to the temporary directory.
          4. Starts the Modelica simulation environment from the temporary directory.
          5. Translates and simulates the model.
          6. Closes the Modelica simulation environment.
          7. Copies output files and deletes the temporary directory.

        This method requires that the directory that contains the executable *dymola*
        is on the system PATH variable. If it is not found, the function returns with
        an error message.

        """
        import os
        import shutil
        import jinja2

        # Delete dymola output files
        self.deleteOutputFiles()

        # Get directory name. This ensures for example that if the directory is called xx/Buildings
        # then the simulations will be done in tmp??/Buildings
        worDirLib = self._create_worDir()

        # Optimica is usually started on level higher than Dymoal
        worDir = os.path.abspath(os.path.join(worDirLib, os.path.pardir))

        self._simulateDir_ = worDir
        # Copy directory
        shutil.copytree(os.path.abspath(self._packagePath), worDirLib,
                        ignore=shutil.ignore_patterns('*.svn', '*.git'))

        # Construct the model instance with all parameter values
        # and the package redeclarations
        dec = self._declare_parameters()
        dec.extend(self._modelModifiers_)

        if len(dec) == 0:
            model_modifier = ""
        else:
            model_modifier = '({dec})'.format(mn=self.modelName, dec=','.join(dec))


        file_name = os.path.join(worDir, "{}.py".format(self.modelName.replace(".", "_")))
        with open(file_name, mode="w", encoding="utf-8") as fil:
            path_to_template = os.path.join(os.path.dirname(__file__), os.path.pardir, "development")
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
                start_time=self._simulator_.get('t0') if self._simulator_.get('t0') is not None else 'mod.get_default_experiment_start_time()',
                final_time = self._simulator_.get('t1') if self._simulator_.get('t1') is not None else 'mod.get_default_experiment_stop_time()',
                result_file_name=f"{self._simulator_.get('resultFile')}.mat",
                simulate=simulate,
                time_out=-1, # timeout is handled by BuildingsPy directly and not by the generated script
                filter=self._result_filter,
                generate_html_diagnostics = self._generate_html_diagnostics)

            fil.write(txt)

        env = os.environ.copy()
        mod_path = os.getenv('MODELICAPATH')
        if mod_path == None:
            os.environ["MODELICAPATH"] = os.getcwd()
        else:
            os.environ["MODELICAPATH"] = ":".join([os.getcwd(), os.getenv('MODELICAPATH')])

        print(f"****** Starting simulation in {worDir}")
        try:
            super()._runSimulation(["jm_ipython.sh", file_name],
                self._simulator_.get('timeout'),
                worDir,
                env=env)

            self._check_simulation_errors(worDir)
            self._copyResultFiles(worDir)
#            self._deleteTemporaryDirectory(worDir)

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

        To list all variables whose name ends in "y", type

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
        solvers = ["CVode", "Radau5ODE", "RungeKutta34", "Dopri5", "RodasODE", "LSODAR", "ExplicitEuler", "ImplicitEuler"]
        if solver in solvers:
            self._simulator_.update(solver=solver)
        else:
            self._reporter.writeWarning(f"Solver {solver} is not supported. Supported are: {', '.join(solvers)}.")
        return

    def generateHtmlDiagnostics(self, generate=False):
        """ If set to `true`, html diagnostics will be generated.

        Note that this can generate huge files for large models.
        """
        self._generate_html_diagnostics = generate

    def deleteOutputFiles(self):
        """ Deletes the output files of the simulator.
        """
        filLis = [str(self._simulator_.get('resultFile')) + '.mat']
        self._deleteFiles(filLis)

    def deleteLogFiles(self):
        """ Deletes the log files of the Python simulator, e.g. the
            files ``BuildingsPy.log``, ``run.mos`` and ``simulator.log``.
        """
        filLis = []
        self._deleteFiles(filLis)

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