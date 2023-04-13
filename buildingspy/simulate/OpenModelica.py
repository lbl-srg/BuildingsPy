#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

  Class that translates and simulates a Modelica model with OpenModelica.

  For a similar class that uses Dymola, see :func:`buildingspy.simulate.Dymola`.

"""
import buildingspy.simulate.base_simulator as bs


class Simulator(bs._BaseSimulator):
    """Class to simulate a Modelica model with OpenModelica.

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

        modelNameUnderscore = modelName.replace('.', '_')

        super().__init__(
            modelName=modelName,
            outputDirectory=outputDirectory,
            packagePath=packagePath,
            outputFileList=[f"{modelNameUnderscore}.py",
                            f"{modelNameUnderscore}_buildingspy.json",
                            f"{modelName}_translate.mos",
                            f"{modelName}_info.json",
                            f"{modelName}.makefile",
                            f"{modelName}.libs",
                            f"{modelName}_init.xml",
                            f"{modelName}.log",
                            f"{modelName}",
                            f"{modelName}_simulate.mos",
                            f"{modelName}_res.mat"])

        self.setSolver("dassl")
        self._MODELICA_EXE = 'omc.py'
        self.setResultFile(f"{modelName}_res")

        self._result_filter = ".*"
        self._generate_html_diagnostics = False
        self._debug_solver = False
        self._debug_solver_interactive_mode = False

    def addParameters(self, dictionary):
        """Adds parameter declarations to the simulator.

        :param dictionary: A dictionary with the parameter values

        Usage: Type
           >>> from buildingspy.simulate.OpenModelica import Simulator
           >>> s=Simulator("myPackage.myModel", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.addParameters({'PID.k': 1.0, 'valve.m_flow_nominal' : 0.1})
           >>> s.addParameters({'PID.t': 10.0})

        This will add the three parameters ``PID.k``, ``valve.m_flow_nominal``
        and ``PID.t`` to the list of model parameters.

        For parameters that are arrays, use a syntax such as
           >>> from buildingspy.simulate.OpenModelica import Simulator
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
           >>> from buildingspy.simulate.OpenModelica import Simulator
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
           >>> from buildingspy.simulate.OpenModelica import Simulator
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
        """Translates and simulates the model.

        Usage: Type
           >>> from buildingspy.simulate.OpenModelica import Simulator
           >>> s=Simulator("MyModelicaLibrary.Examples.Constants", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.simulate() # doctest: +SKIP

        This method
          1. Deletes output files
          2. Writes a script to simulate the model.
          3. Starts the Modelica simulation environment.
          4. Translates and simulates the model.
          5. Closes the Modelica simulation environment.

        This method requires that the directory that contains the executable ``omc``
        is on the system ``PATH`` variable.
        If it is not found, the function raises an exception.

        """
        return self._translate_and_simulate(simulate=True)

    def translate(self):
        """Translates the model to generate a Functional Mockup Unit.

        Usage: Type
           >>> from buildingspy.simulate.OpenModelica import Simulator
           >>> s=Simulator("MyModelicaLibrary.Examples.Constants", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.translate() # doctest: +SKIP

        This method
          1. Deletes output files
          2. Writes a script to simulate the model.
          3. Starts the Modelica simulation environment.
          4. Translates the model.
          5. Closes the Modelica simulation environment.

        This method requires that the directory that contains the executable ``omc``
        is on the system ``PATH`` variable.
        If it is not found, the function raises an exception.

        """
        return self._translate_and_simulate(simulate=False)

    def _translate_and_simulate(self, simulate):
        """ Translates and optionally simulates the model.

        :param simulate: If ``true`` the model is simulated, otherwise it is only translated.

        This method
          1. Deletes output files
          2. Writes a script to simulate the model.
          3. Starts the Modelica simulation environment.
          4. Translates and simulates the model.
          5. Closes the Modelica simulation environment.

        This method requires that the directory that contains the executable ``omc``
        is on the system ``PATH`` variable.
        If it is not found, the function raises an exception.

        """
        import os
        import jinja2
#        import datetime

        from sys import platform

        # Delete output files
        self.deleteOutputFiles()

        worDir = self._outputDir_

        # Construct the model instance with all parameter values
        # and the package redeclarations
        dec = self._declare_parameters()
        dec.extend(self._modelModifiers_)

        if len(dec) == 0:
            model_modifier = ""
        else:
            model_modifier = '{dec}'.format(mn=self.modelName, dec=','.join(dec))

        file_name = "{}.py".format(self.modelName.replace(".", "_"))
##        self._time_stamp_old_files = datetime.datetime.now()
        with open(os.path.join(worDir, file_name), mode="w", encoding="utf-8") as fil:
            path_to_template = os.path.join(
                os.path.dirname(__file__), os.path.pardir, "development")
            env = jinja2.Environment(loader=jinja2.FileSystemLoader(path_to_template))

            template = env.get_template("openmodelica_run.template")

            txt = template.render(
                library_name=self.modelName.split(".")[0],
                package_path=self.getPackagePath(),
                model=self.modelName,
                modifiedModelName=f"{self.modelName.replace('.', '_')}_Modified",
                commentStringNonModifiedModel = "//" if len(model_modifier) > 0 else "",
                commentStringModifiedModel    = "//" if len(model_modifier) == 0 else "",
                model_modifier=model_modifier,
                ncp=self._simulator_.get('numberOfIntervals'),
                rtol=self._simulator_.get('eps'),
                solver=self._simulator_.get('solver'),
                start_time=self._simulator_.get('t0') if self._simulator_.get(
                    't0') is not None else 0,
                final_time=self._simulator_.get('t1') if self._simulator_.get(
                    't1') is not None else 1,
                result_file_name=f"{self._simulator_.get('resultFile')}.mat",
                simulate=simulate,
                time_out=self._simulator_.get('timeout'),
                filter=self._result_filter #,
                #generate_html_diagnostics=self._generate_html_diagnostics,
                #debug_solver=self._debug_solver,
                #debug_solver_interactive_mode=self._debug_solver_interactive_mode
                )

            fil.write(txt)

            if platform == "darwin":
                cmd = ["python3", f"./{file_name}"]
            else:
                cmd = ["python", f".{os.sep}{file_name}"]

        try:

            super()._runSimulation(cmd,
                                   self._simulator_.get('timeout'),
                                   worDir)

            self._check_simulation_errors(worDir=worDir, simulate=simulate)
# self._copyNewFiles(worDir)
# self._deleteTemporaryDirectory(worDir)

        except Exception as e:  # Catch all possible exceptions
            em = f"Simulation failed in '{worDir}'\n   Exception: {e}.\n   You need to delete the directory manually.\n"
            self._reporter.writeError(em)
            raise e

        # Copy result file name if needed
        if f"{self._simulator_.get('resultFile')}.mat" != f"{self.modelName}_res.mat":
            os.rename(f"{self.modelName}_res.mat", f"{self._simulator_.get('resultFile')}.mat")

    def setSolver(self, solver):
        """Sets the solver.

        :param solver: The name of the solver.

        The default solver is *dassl*.
        """
        # fixme: add more solvers
        solvers = [
            "dassl",
            "cvode"]
        if solver in solvers:
            self._simulator_.update(solver=solver)
        else:
            self._reporter.writeWarning(
                f"Solver {solver} is not supported. Supported are: {', '.join(solvers)}.")
        return

    def _check_simulation_errors(self, worDir, simulate):
        """ Method that checks if errors occured during simulation.

        :param worDir: Working directory.
        :param simulate: If ``true`` the model is supposed to have been simulated,
            and errors are checked also for simulation. Otherwise, errors are only checked
            for translation.
        """
        import os
        import json

        from buildingspy.io.outputfile import get_errors_and_warnings
        logFil = self.modelName.replace(".", "_") + '_buildingspy.json'
        path_to_logfile = os.path.join(worDir, logFil)
        if not os.path.exists(path_to_logfile):
            msg = f"Expected log file {path_to_logfile}, but file does not exist."
            self._reporter.writeError(msg)
            raise IOError(msg)

        with open(path_to_logfile, 'r') as f:
            js = json.loads(f.read())
            steps = ['translation', 'simulation'] if simulate else ['translation']
            for step in steps:
                if step not in js:
                    msg = f"Failed to invoke {step} for model {self.modelName}. Check {path_to_logfile}."
                    self._reporter.writeError(msg)
                    raise RuntimeError(msg)
                if js[step]['success'] is not True:
                    # Check if there was a timeout exception
                    if "exception" in js[step]:
                        if "TimeoutExpired" in js[step]['exception']:
                            msg = f"The {step} of {self.modelName} failed due to timeout. Check {path_to_logfile}."
                            self._reporter.writeError(msg)
                            raise TimeoutError(msg)
                    # Raise a runtime error
                    msg = f"The {step} of {self.modelName} failed. Check {path_to_logfile}."
                    self._reporter.writeError(msg)
                    raise RuntimeError(msg)
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
        self._deleteFiles([self._simulator_.get('resultFile') + ".mat"])
