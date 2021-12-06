#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

  Class that translates and simulates a Modelica model with Dymola.

  For a similar class that uses OPTIMICA, see :func:`buildingspy.simulate.Optimica`.

"""
import buildingspy.simulate.base_simulator as bs


class Simulator(bs._BaseSimulator):
    """Class to simulate a Modelica model.

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
            outputFileList=['run_simulate.mos', 'run_translate.mos', 'run.mos',
                            'dsfinal.txt', 'dsin.txt',
                            'dsmodel*', 'dymosim', 'dymosim.exe',
                            'BuildingsPy.log', 'run.mos', 'run_simulate.mos',
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
           >>> from buildingspy.simulate.Dymola import Simulator
           >>> s=Simulator("myPackage.myModel", packagePath="buildingspy/tests/MyModelicaLibrary")
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

        This method is deprecated. Use :meth:`~Dymola.getParameters` instead.

        """
        raise DeprecationWarning(
            "The method Dymola.getSimulatorSettings() is deprecated. Use Dymola.getParameters() instead.")
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
        import os
        # Note that model_name has quotes if it is of the form
        # "MyModelicaLibrary.Examples.BooleanParameters(p1=true,p2=false)"
        package_mo = os.path.join((model_name.split('.')[0]).strip('"'), "package.mo")

        s = """
// File autogenerated by _get_dymola_commands
// Do not edit.
//cd("{working_directory}");
openModel("{package_mo}", changeDirectory=false);
Modelica.Utilities.Files.remove("{log_file}");
OutputCPUtime:=true;
""".format(working_directory=working_directory,
           package_mo=package_mo,
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

    def addParameters(self, dictionary):
        """Adds parameter declarations to the simulator.

        :param dictionary: A dictionary with the parameter values

        Usage: Type
           >>> from buildingspy.simulate.Dymola import Simulator
           >>> s=Simulator("myPackage.myModel", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.addParameters({'PID.k': 1.0, 'valve.m_flow_nominal' : 0.1})
           >>> s.addParameters({'PID.t': 10.0})

        This will add the three parameters ``PID.k``, ``valve.m_flow_nominal``
        and ``PID.t`` to the list of model parameters.

        For parameters that are arrays, use a syntax such as
           >>> from buildingspy.simulate.Dymola import Simulator
           >>> s = Simulator("MyModelicaLibrary.Examples.Constants", packagePath="buildingspy/tests/MyModelicaLibrary")
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
           >>> from buildingspy.simulate.Dymola import Simulator
           >>> s=Simulator("myPackage.myModel", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.addParameters({'PID.k': 1.0, 'valve.m_flow_nominal' : 0.1})
           >>> s.getParameters()
           [('PID.k', 1.0), ('valve.m_flow_nominal', 0.1)]
        """
        return list(self._parameters_.items())

    def addModelModifier(self, modelModifier):
        """Adds a model modifier.

        :param modelModifier: A model modifier.

        Usage: Type
           >>> from buildingspy.simulate.Dymola import Simulator
           >>> s=Simulator("myPackage.myModel", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.addModelModifier('redeclare package MediumA = Buildings.Media.IdealGases.SimpleAir')

        This method adds a model modifier. The modifier is added to the list
        of model parameters. For example, the above statement would yield the
        command
        ``simulateModel(myPackage.myModel(redeclare package MediumA = Buildings.Media.IdealGases.SimpleAir), startTime=...``

        """
        self._modelModifiers_.append(modelModifier)
        return

    def simulate(self):
        """Simulates the model.

        This method
          1. Deletes output files
          2. Writes a script to simulate the model.
          3. Starts the Modelica simulation environment.
          4. Translates and simulates the model.
          5. Closes the Modelica simulation environment.

        This method requires that the directory that contains the executable ``dymola``
        is on the system ``PATH`` variable.
        If it is not found, the function raises an exception.

        """
        import os
        import shutil
        import datetime

        # Delete output files
        self.deleteOutputFiles()

        # Get directory name. This ensures for example that if the directory is called xx/Buildings
        # then the simulations will be done in tmp??/Buildings
        worDir = self._outputDir_

        # Construct the model instance with all parameter values
        # and the package redeclarations
        dec = self._declare_parameters()
        dec.extend(self._modelModifiers_)

        mi = '"{mn}({dec})"'.format(mn=self.modelName, dec=','.join(dec))

##        self._time_stamp_old_files = datetime.datetime.now()

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
# self._copyNewFiles(worDir)
# self._deleteTemporaryDirectory(worDir)
        except Exception as e:  # Catch all possible exceptions
            em = f"Simulation failed in '{worDir}'\n   Exception: {e}.\n   You need to delete the directory manually.\n"
            self._reporter.writeError(em)
            raise

    def translate(self):
        """Translates the model.

        This method
          1. Deletes output files
          2. Writes a script to simulate the model.
          3. Starts the Modelica simulation environment.
          4. Translates the model.
          5. Closes the Modelica simulation environment.

        This method requires that the directory that contains the executable ``dymola``
        is on the system ``PATH`` variable.
        If it is not found, the function raises an exception.

        """
        import os
        import shutil

        # Delete output files
        self.deleteOutputFiles()

        # Get directory name. This ensures for example that if the directory is called xx/Buildings
        # then the simulations will be done in tmp??/Buildings
        worDir = os.getcwd()
        self._translateDir_ = worDir
        # Copy directory
##        shutil.copytree(os.path.abspath(self._packagePath), worDir)

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

    def setSolver(self, solver):
        """Sets the solver.

        :param solver: The name of the solver.

        The default solver is *radau*.
        """
        self._simulator_.update(solver=solver)
        return

    def showGUI(self, show=True):
        """ Call this function to show the GUI of the simulator.

        By default, the simulator runs without GUI
        """
        self._showGUI = show
        return

    def _runSimulation(self, mosFile, timeout, directory):
        """Runs a model translation or simulation.

        :param mosFile: .mos file
        :param timeout: Time out in seconds
        :param directory: The working directory

        """
        import os
        # Remove the working directory from the mosFile name.
        # This is needed for example if the simulation is run in a docker,
        # which may have a different file structure than the host.
        mo_fil = mosFile.replace(directory, ".")
        # List of command and arguments
        if self._showGUI:
            cmd = [self._MODELICA_EXE, mo_fil]
        else:
            cmd = [self._MODELICA_EXE, mo_fil, "/nowindow"]

        env = super().prependToModelicaPath(os.environ.copy(), self._packagePath)

        super()._runSimulation(cmd, timeout, directory, env)

    def _check_simulation_errors(self, worDir):
        """ Method that checks if errors occured during simulation.
        """
        import os
        from buildingspy.io.outputfile import get_errors_and_warnings
        path_to_logfile = os.path.join(worDir, 'simulator.log')
        # `simulator.log` may not exist in case of process timeout.
        if os.path.exists(path_to_logfile):
            ret = get_errors_and_warnings(path_to_logfile, 'dymola')
            if not ret["errors"]:
                pass
            else:
                for li in ret["errors"]:
                    self._reporter.writeError(li)
                raise Exception(f"Simulation terminated with error. Check {path_to_logfile}.")
        else:
            em = f"Log file {path_to_logfile} does not exist."
            self._reporter.writeError(em)
            raise IOError(em)

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
        super()._deleteFiles([self._simulator_.get('resultFile') + "_result.mat"])
