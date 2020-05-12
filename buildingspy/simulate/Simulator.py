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


class Simulator(bs._BaseSimulator):
    """Class to simulate a Modelica model.

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

    def __init__(self, modelName, simulator, outputDirectory='.', packagePath=None):
        import buildingspy.io.reporter as reporter
        import os

        if simulator != "dymola":
            raise ValueError("Argument 'simulator' needs to be set to 'dymola'.")

        super().__init__(
            modelName=modelName,
            outputDirectory=outputDirectory,
            packagePath=packagePath,
            outputFileList = ['run_simulate.mos', 'run_translate.mos', 'run.mos',
                              'dsfinal.txt', 'dsin.txt',
                              'dsmodel*', 'dymosim', 'dymosim.exe'],
            logFileList = ['BuildingsPy.log', 'run.mos', 'run_simulate.mos',
                           'run_translate.mos', 'simulator.log', 'translator.log', 'dslog.txt'])

        self._preProcessing_ = list()
        self._postProcessing_ = list()
        self.setStartTime(0)
        self.setStopTime(1)
        # If modelName=aa.bb.cc, then split returns [aa, bb, cc]
        # This is needed to get the short model name
#        rs = resultFile.split(".")
#        self._simulator_.update(resultFile=rs[len(rs) - 1])
        self.setResultFile(modelName.split(".")[-1])

        self.setSolver("radau")
        self._MODELICA_EXE = 'dymola'
        self._showGUI = False


    def addPreProcessingStatement(self, command):
        """Adds a pre-processing statement to the simulation script.

        :param command: A script statement.

        Usage: Type
           >>> from buildingspy.simulate.Simulator import Simulator
           >>> s=Simulator("myPackage.myModel", "dymola", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.addPreProcessingStatement("Advanced.StoreProtectedVariables:= true;")
           >>> s.addPreProcessingStatement("Advanced.GenerateTimers = true;")

        This will execute the two statements after the ``openModel`` and
        before the ``simulateModel`` statement.
        """
        self._preProcessing_.append(command)
        return

    def addPostProcessingStatement(self, command):
        """Adds a post-processing statement to the simulation script.

        :param statement: A script statement.

        This will execute ``command`` after the simulation, and before
        the log file is written.
        """
        self._postProcessing_.append(command)
        return


    def getSimulatorSettings(self):
        """Returns a list of settings for the parameter as (key, value)-tuples.

        :return: A list of parameters (key, value) pairs, as 2-tuples.

        This method is deprecated. Use :meth:`~Simulator.getParameters` instead.

        """
        raise DeprecationWarning(
            "The method Simulator.getSimulatorSettings() is deprecated. Use Simulator.getParameters() instead.")
        return self.getParameters()


    def exitSimulator(self, exitAfterSimulation=True):
        """ This function allows avoiding that the simulator terminates.

        :param exit: Set to ``False`` to avoid the simulator from terminating
                     after the simulation.

        This function is useful during debugging, as it allows to
        keep the simulator open after the simulation in order to
        inspect results or log messages.

        """
        self._exitSimulator = exitAfterSimulation
        return

    def showProgressBar(self, show=True):
        """ Enables or disables the progress bar.

        :param show: Set to *false* to disable the progress bar.

        If this function is not called, then a progress bar will be shown as the simulation runs.
        """
        self._showProgressBar = show
        return

    def _get_dymola_commands(self, working_directory, log_file, model_name, translate_only=False):
        """ Returns a string that contains all the commands required
            to run or translate the model.

        :param working_directory: The working directory for the simulation or translation.
        :param log_file: The name of the log file that will be written by Dymola.
        :param translate_only: Set to ```True``` to only translate the model without a simulation.
        """
        s = """
// File autogenerated by _get_dymola_commands
// Do not edit.
//cd("{working_directory}");
Modelica.Utilities.Files.remove("{log_file}");
openModel("package.mo");
OutputCPUtime:=true;
""".format(working_directory=working_directory,
           log_file=log_file)
        # Pre-processing commands
        for prePro in self._preProcessing_:
            s += prePro + '\n'

        s += "modelInstance={0};\n".format(model_name)

        if translate_only:
            s += "translateModel(modelInstance);\n"
        else:
            # Create string for numberOfIntervals
            intervals = ""
            if 'numberOfIntervals' in self._simulator_:
                intervals = ", numberOfIntervals={0}".format(
                    self._simulator_.get('numberOfIntervals'))
            s += """
simulateModel(modelInstance, startTime={start_time}, stopTime={stop_time}, method="{method}", tolerance={tolerance}, resultFile="{result_file}"{others});
""".format(start_time=self._simulator_.get('t0'),
                stop_time=self._simulator_.get('t1'),
                method=self._simulator_.get('solver'),
                tolerance=self._simulator_.get('eps'),
                result_file=self._simulator_.get('resultFile'),
                others=intervals)

        # Post-processing commands
        for posPro in self._postProcessing_:
            s += posPro + '\n'

        s += """savelog("{0}");\n""".format(log_file)
        if self._exitSimulator:
            s += "Modelica.Utilities.System.exit();\n"
        return s

    def simulate(self):
        """Simulates the model.

        This method
          1. Deletes dymola output files
          2. Copies the current directory, or the directory specified by the ``packagePath``
             parameter of the constructor, to a temporary directory.
          3. Writes a Modelica script to the temporary directory.
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

        # Delete dymola output files
        self.deleteOutputFiles()

        # Get directory name. This ensures for example that if the directory is called xx/Buildings
        # then the simulations will be done in tmp??/Buildings
        worDir = self._create_worDir()
        self._simulateDir_ = worDir
        # Copy directory
        shutil.copytree(os.path.abspath(self._packagePath), worDir,
                        ignore=shutil.ignore_patterns('*.svn', '*.git'))

        # Construct the model instance with all parameter values
        # and the package redeclarations
        dec = self._declare_parameters()
        dec.extend(self._modelModifiers_)

        mi = '"{mn}({dec})"'.format(mn=self.modelName, dec=','.join(dec))

        try:
            # Write the Modelica script
            runScriptName = os.path.join(worDir, "run.mos")
            with open(runScriptName, mode="w", encoding="utf-8") as fil:
                fil.write(self._get_dymola_commands(
                    working_directory=worDir,
                    log_file="simulator.log",
                    model_name=mi,
                    translate_only=False))
            # Copy files to working directory

            # Run simulation
            self._runSimulation(runScriptName,
                            self._simulator_.get('timeout'),
                            worDir)
            self._check_simulation_errors(worDir)
            self._copyResultFiles(worDir)
            self._deleteTemporaryDirectory(worDir)
        except Exception as e:  # Catch all possible exceptions
            em = f"Simulation failed in '{worDir}'\n   Exception: {e}.\n   You need to delete the directory manually.\n"
            self._reporter.writeError(em)

    def translate(self):
        """Translates the model.

        This method
          1. Deletes dymola output files
          2. Copies the current directory, or the directory specified by the ``packagePath``
             parameter of the constructor, to a temporary directory.
          3. Writes a Modelica script to the temporary directory.
          4. Starts the Modelica simulation environment from the temporary directory.
          5. Translates the model.
          6. Closes the Modelica simulation environment.
          7. Keeps translated output files in the temporary directory.

        This method requires that the directory that contains the executable *dymola*
        is on the system PATH variable. If it is not found, the function returns with
        an error message.

        """
        import os
        import shutil

        # Delete dymola output files
        self.deleteOutputFiles()

        # Get directory name. This ensures for example that if the directory is called xx/Buildings
        # then the simulations will be done in tmp??/Buildings
        worDir = self._create_worDir()
        self._translateDir_ = worDir
        # Copy directory
        shutil.copytree(os.path.abspath(self._packagePath), worDir)

        # Construct the model instance with all parameter values
        # and the package redeclarations
        dec = self._declare_parameters()
        dec.extend(self._modelModifiers_)

        mi = '"{mn}({dec})"'.format(mn=self.modelName, dec=','.join(dec))

        try:
            # Write the Modelica script
            runScriptName = os.path.join(worDir, "run_translate.mos")
            with open(runScriptName, mode="w", encoding="utf-8") as fil:
                fil.write(self._get_dymola_commands(
                    working_directory=worDir,
                    log_file="translator.log",
                    model_name=mi,
                    translate_only=True))
            # Copy files to working directory

            # Run translation
            self._runSimulation(runScriptName,
                                self._simulator_.get('timeout'),
                                worDir)
        except BaseException:
            self._reporter.writeError("Translation failed in '" + worDir + "'\n" +
                                      "   You need to delete the directory manually.")
            raise

    def showGUI(self, show=True):
        """ Call this function to show the GUI of the simulator.

        By default, the simulator runs without GUI
        """
        self._showGUI = show
        return

    def printModelAndTime(self):
        """ Prints the current time and the model name to the standard output.

        This method may be used to print logging information.
        """
        import time
        self._reporter.writeOutput("Model name       = " + self.modelName + '\n' +
                                   "Output directory = " + self._outputDir_ + '\n' +
                                   "Time             = " + time.asctime() + '\n')
        return

    def _runSimulation(self, mosFile, timeout, directory):
        """Runs a model translation or simulation.

        :param mosFile: .mos file
        :param timeout: Time out in seconds
        :param directory: The working directory

        """
        # Remove the working directory from the mosFile name.
        # This is needed for example if the simulation is run in a docker,
        # which may have a different file structure than the host.
        mo_fil = mosFile.replace(directory, ".")
        # List of command and arguments
        if self._showGUI:
            cmd = [self._MODELICA_EXE, mo_fil]
        else:
            cmd = [self._MODELICA_EXE, mo_fil, "/nowindow"]

        super()._runSimulation(cmd, timeout, directory)


    def _check_simulation_errors(self, worDir):
        """ Method that checks if errors occured during simulation.
        """
        import os
        from buildingspy.io.outputfile import get_errors_and_warnings
        path_to_logfile = os.path.join(worDir, 'simulator.log')
        ret = get_errors_and_warnings(path_to_logfile, 'dymola')
        if not ret["errors"]:
            pass
        else:
            for li in ret["errors"]:
                self._reporter.writeError(li)
            raise IOError
