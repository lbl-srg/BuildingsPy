#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import abc


class _BaseSimulator(object):
    """ Basic class to simulate a Modelica model.

    :param modelName: The name of the Modelica model.
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

    def __init__(
            self,
            modelName,
            outputDirectory,
            packagePath,
            outputFileList):
        import buildingspy.io.reporter as reporter
        import os

        # Set log file name for python script
        logFilNam = os.path.join(outputDirectory, "BuildingsPy.log")

        # Check if the packagePath parameter is correct
        self._packagePath = None
        if packagePath is None:
            self.setPackagePath(os.path.abspath('.'))
        else:
            self.setPackagePath(packagePath)

        self.modelName = modelName
        self._parameters_ = {}
        self._modelModifiers_ = list()

        self._simulator_ = {}

        self._outputDir_ = outputDirectory

        self._outputFileList = outputFileList

        # This call is needed so that the reporter can write to the working directory
        self._createDirectory(outputDirectory)

#        # This call is needed so that the reporter can write to the working directory
#        self._createDirectory(outputDirectory)
#        self._preProcessing_ = list()
#        self._postProcessing_ = list()
#        self._parameters_ = {}
#        self._modelModifiers_ = list()
        self.setStartTime(None)
        self.setStopTime(None)
        self.setTolerance(1E-6)
        self.setNumberOfIntervals()
#        self.setSolver("radau")
        self.setTimeOut(-1)
        self._MODELICA_EXE = None
        self._reporter = reporter.Reporter(fileName=logFilNam)
        self._showProgressBar = False
        self._showGUI = False
        self._exitSimulator = True
##        self._time_stamp_old_files = None

    def setPackagePath(self, packagePath):
        """ Set the path specified by ``packagePath``.

        :param packagePath: The path where the Modelica ``package.mo`` file is located.

        It checks whether the file ``package.mo`` exists in the directory ``packagePath``,
        and then sets the package path.
        Otherwise, a ``ValueError`` is raised.
        """
        import os

        # Check whether the package Path parameter is correct
        fil = os.path.join(packagePath, "package.mo")
        if not os.path.isfile(fil):
            msg = f"Argument packagePath={packagePath} must be a directory containing 'package.mo'. Did not find '{fil}'"
            raise ValueError(msg)

        # All the checks have been successfully passed
        self._packagePath = packagePath

    def _createDirectory(self, directoryName):
        """ Creates the directory *directoryName*

        :param directoryName: The name of the directory

        This method validates the directory *directoryName* and if the
        argument is valid and write permissions exists, it creates the
        directory. Otherwise, a *ValueError* is raised.
        """
        import os

        if directoryName != '.':
            if len(directoryName) == 0:
                raise ValueError(
                    "Specified directory is not valid. Set to '.' for current directory.")
            # Try to create directory
            if not os.path.exists(directoryName):
                os.makedirs(directoryName)
            # Check write permission
            if not os.access(directoryName, os.W_OK):
                raise ValueError("Write permission to '" + directoryName + "' denied.")

    @abc.abstractmethod
    def setSolver(self, solver):
        return

    def getOutputDirectory(self):
        """Returns the name of the output directory.

        :return: The name of the output directory.

        """
        return self._outputDir_

    def setOutputDirectory(self, outputDirectory):
        """Sets the name of the output directory.

        :param outputDirectory: The name of the output directory.
        :return: The name of the output directory.

        """
        self._outputDir_ = outputDirectory
        return self._outputDir_

    def getPackagePath(self):
        """Returns the path of the directory containing the Modelica package.

        :return: The path of the Modelica package directory.

        """
        return self._packagePath

    def setStartTime(self, t0):
        """Sets the start time.

        :param t0: The start time of the simulation in seconds.

        The default start time is 0.
        """
        self._simulator_.update(t0=t0)
        return

    def setStopTime(self, t1):
        """Sets the start time.

        :param t1: The stop time of the simulation in seconds.

        The default stop time is 1.
        """
        self._simulator_.update(t1=t1)
        return

    def setTolerance(self, eps):
        """Sets the solver tolerance.

        :param eps: The solver tolerance.

        The default solver tolerance is 1E-6.
        """
        self._simulator_.update(eps=eps)
        return

    def setNumberOfIntervals(self, n=500):
        """Sets the number of output intervals.

        :param n: The number of output intervals.

        The default is unspecified, which defaults to 500.
        """
        self._simulator_.update(numberOfIntervals=n)
        return

    def setTimeOut(self, sec):
        """Sets the time out after which the simulation will be killed.

        :param sec: The time out after which the simulation will be killed.

        The default value is -1, which means that the simulation will
        never be killed.
        """
        self._simulator_.update(timeout=sec)
        return

    def setResultFile(self, resultFile):
        """Sets the name of the result file (without extension).

        :param resultFile: The name of the result file (without extension).

        """
        # If resultFile=aa.bb.cc, then split returns [aa, bb, cc]
        # This is needed to get the short model name
#        rs = resultFile.split(".")
#        self._simulator_.update(resultFile=rs[len(rs) - 1])
        self._simulator_.update(resultFile=resultFile)
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

    def deleteOutputFiles(self):
        """ Deletes the output files of the simulator.
        """
        self._deleteFiles(self._outputFileList)

    def _deleteFiles(self, fileList):
        """ Deletes the output files of the simulator.

        :param fileList: List of files to be deleted.

        """
        import os
        import glob

        for ent in fileList:
            #            print(f"*** checking whether to delete {ent}")
            for fil in glob.glob(ent):
                try:
                    if os.path.exists(fil):
                     #                       print(f"    Deleting file: {fil}")
                        os.remove(fil)
                except OSError as e:
                    self._reporter.writeError("Failed to delete '" + fil + "' : " + e.strerror)
                    raise

    def _deleteTemporaryDirectory(self, worDir):
        """ Deletes the working directory.
            If this function is invoked with `worDir=None`, then it immediately returns.

        :param srcDir: The name of the working directory.

        """
        import shutil
        import os

        if worDir is None:
            return

        # For Dymola, walk one level up, since we appended the name of the current directory
        # to the name of the working directory
        if self._MODELICA_EXE == 'dymola':
            dirNam = os.path.split(worDir)[0]
        else:
            dirNam = worDir

        # Make sure we don't delete a root directory
        if dirNam.find('tmp-simulator-') == -1:
            self._reporter.writeError(
                "Failed to delete '" +
                dirNam +
                "' as it does not seem to be a valid directory name.")
            raise
        else:
            try:
                if os.path.exists(worDir):
                    shutil.rmtree(dirNam)
            except IOError as e:
                self._reporter.writeError("Failed to delete '" +
                                          worDir + ": " + e.strerror)
                raise

    def _isExecutable(self, program):
        import os
        import platform

        def is_exe(fpath):
            return os.path.exists(fpath) and os.access(fpath, os.X_OK)

        # Add .exe, which is needed on Windows 7 to test existence
        # of the program
        if platform.system() == "Windows":
            program = program + ".exe"

        if is_exe(program):
            return True
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return True
        return False

    def _create_worDir(self):
        """ Create working directory
        """
        import os
        import tempfile
        import getpass
        curDir = os.path.abspath(self._packagePath)
        ds = curDir.split(os.sep)
        dirNam = ds[len(ds) - 1]
        worDir = os.path.join(tempfile.mkdtemp(
            prefix='tmp-simulator-' + getpass.getuser() + '-'), dirNam)
        return worDir

    def _declare_parameters(self):
        """ Declare list of parameters
        """
        def to_modelica(arg):
            """ Convert to Modelica array.
            """
            # Check for strings and booleans
            if isinstance(arg, str):
                return '\\"' + arg + '\\"'
            elif isinstance(arg, bool):
                if arg is True:
                    return 'true'
                else:
                    return 'false'
            try:
                return '{' + ", ".join(to_modelica(x) for x in arg) + '}'
            except TypeError:
                return repr(arg)
        dec = list()

        for k, v in list(self._parameters_.items()):
            # Dymola requires vectors of parameters to be set in the format
            # p = {1, 2, 3} rather than in the format of python arrays, which
            # is p = [1, 2, 3].
            # Hence, we convert the value of the parameter if required.
            s = to_modelica(v)
            dec.append('{param}={value}'.format(param=k, value=s))

        return dec

    def _runSimulation(self, cmd, timeout, directory, env=None):
        """Runs a model translation or simulation.

        :param cmd: Array with command arguments
        :param timeout: Time out in seconds
        :param directory: The working directory

        """

        import sys
        import os
        import subprocess
        import time
        import datetime

        # Check if executable is on the path
        if not self._isExecutable(cmd[0]):
            em = f"Error: Did not find executable '", cmd[0], "'."
            em += "       Make sure it is on the PATH variable of your operating system."
            raise RuntimeError(em)

        # _packagePath is the path that contains the package.mo file.
        # Export its parent directory to the MODELICAPATH.
        # This is for example needed for
        # export USE_DOCKER=true
        # python buildingspy/tests/test_simulate_Optimica.py
        # Test_simulate_Simulator.test_setResultFilter
        osEnv = os.environ.copy() if env is None else env
        osEnv = self.prependToModelicaPath(osEnv, os.path.dirname(self._packagePath))

        # Run command
        try:
            self._simulationStartTime = datetime.datetime.now()
            pro = subprocess.Popen(args=cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   shell=False,
                                   cwd=directory,
                                   env=osEnv)
            timeout_exceeded = False
            terminatedProcess = False
            killedProcess = False
            # Tailored implementation of a timeout mechanism as it is not available
            # through `wait` or `communicate` methods in Python 2.
            if timeout > 0:
                while not timeout_exceeded and pro.poll() is None:
                    time.sleep(0.01)
                    elapsedTime = (datetime.datetime.now() - self._simulationStartTime).seconds
                    if elapsedTime > timeout:
                        timeout_exceeded = True
            else:
                pro.wait()

            if timeout_exceeded:
                # For Dymola only: manage process termination.
                # (For Optimica and JModelica this is managed at the lower level
                # in `*_run.template`.)
                if self._MODELICA_EXE == 'dymola':
                    # On unixlike systems, give the process a chance to close gracefully
                    # using `terminate` (on Windows `terminate` and `kill` are aliases).
                    # Then, if it is still running after `terminate_timeout`, kill the process.
                    terminate_timeout = 5
                    if self._showProgressBar:
                        # This output needed because of the progress bar
                        sys.stdout.write("\n")
                    self._reporter.writeError("Terminating simulation in " +
                                              directory + ".")
                    pro.terminate()
                    terminate_start_time = datetime.datetime.now()
                    while not terminatedProcess and not killedProcess:
                        time.sleep(0.1)
                        elapsedTime = (datetime.datetime.now() - terminate_start_time).seconds
                        if pro.poll() is not None:
                            terminatedProcess = True
                        if elapsedTime > terminate_timeout:
                            self._reporter.writeError("Killing simulation in " +
                                                      directory + ".")
                            pro.kill()
                            killedProcess = True
                    em = f"Process timeout: terminated process as it computed longer than {str(timeout)} seconds."
                    self._reporter.writeError(em)
                    pro.stdout.close()
                    pro.stderr.close()
                    raise TimeoutError(em)
            else:
                if self._showProgressBar:
                    fractionComplete = float(elapsedTime) / float(timeout)
                    self._printProgressBar(fractionComplete)

            # This output is needed because of the progress bar
            if self._showProgressBar:
                sys.stdout.write("\n")

            std_out = pro.stdout.read()
            if len(std_out) > 0:
                self._reporter.writeOutput(
                    f"*** Standard output stream from simulation:\n{std_out}")
            std_err = pro.stderr.read()
            if len(std_err) > 0:
                if pro.returncode != 0:
                    self._reporter.writeError(
                        f"*** Standard error stream from simulation:\n{std_err}")
                else:
                    # Optimica writes warnings such as missing IPOPT installation to stderr,
                    # but in this situation we want to continue unless it returns a non-zero
                    # exit code.
                    self._reporter.writeOutput(
                        f"*** Standard error stream from simulation:\n{std_err}")

            pro.stdout.close()
            pro.stderr.close()

        except OSError as e:
            print(("Execution of ", cmd, " failed:", e))
            raise

    def _printProgressBar(self, fractionComplete):
        """Prints a progress bar to the console.

        :param fractionComplete: The fraction of the time that is completed.

        """
        import sys
        nInc = 50
        count = int(nInc * fractionComplete)
        proBar = "|"
        for i in range(nInc):
            if i < count:
                proBar += "-"
            else:
                proBar += " "
        proBar += "|"
        print((proBar, int(fractionComplete * 100), "%\r",))
        sys.stdout.flush()

        return

# def _copyNewFiles(self, srcDir):
# """ Copies the output and log files of the simulator.
##
# :param srcDir: The source directory of the files
##
# """
##        import shutil
##        import os
##        import time
##
# for root, dirs, files in os.walk(srcDir):
# for name in files:
##                filename = os.path.join(root, name)
# if os.path.getmtime(filename) > self._time_stamp_old_files.timestamp():
##                    relativeName = filename[len(srcDir) + 1:]
##                    self.__copy_file(filename, os.path.join(self._outputDir_, relativeName))
##
# def __copy_file(self, srcFil, newFil):
##        import os
##        import shutil
##
# try:
# if os.path.exists(srcFil):
# Make directory. This allows subdirectories to be copied, such as
# generated by EnergyPlus
##                os.makedirs(os.path.dirname(newFil), exist_ok=True)
##                shutil.copy(srcFil, newFil)
# except IOError as e:
# self._reporter.writeError("Failed to copy '" +
# srcFil + "' to '" + newFil +
# "; : " + e.strerror)

    @staticmethod
    def prependToModelicaPath(env, path):
        ''' Prepends `path` to the dictionary `env` and returns it.

           :param env: A dictionary that may contain the key `MODELICAPATH`.
           :param path: The directory to add to the front of `MODELICAPATH`.
           :return: The dictionary `env` with an environment variable `MODELICAPATH` that has as its first entry `path`.

        Usage:

            >>> import os
            >>> from buildingspy.simulate.Optimica import Simulator
            >>> s=Simulator("myPackage.myModel", packagePath="buildingspy/tests/MyModelicaLibrary")
            >>> env = os.environ.copy()
            >>> env = s.prependToModelicaPath(env, os.getcwd())

         '''
        if 'MODELICAPATH' in env:
            env['MODELICAPATH'] = ":".join([path, env['MODELICAPATH']])
        else:
            env['MODELICAPATH'] = path
        return env
