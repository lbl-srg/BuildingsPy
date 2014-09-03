#!/usr/bin/env python


class Simulator:
    """Class to simulate a Modelica model.

    :param modelName: The name of the Modelica model.
    :param simulator: The simulation engine. Currently, the only supported value is ``dymola``.
    :param outputDirectory: An optional output directory.
    :param packagePath: An optional path where the Modelica package.mo file is located. 

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

        ## Check arguments and make output directory if needed
        if simulator != "dymola":
            raise ValueError("Argument 'simulator' needs to be set to 'dymola'.")
        # Set log file name for python script
        logFilNam = os.path.join(outputDirectory, "BuildingsPy.log")

        self.modelName = modelName
        self._outputDir_ = outputDirectory
        
        # Check if the package Path parameter is correct
        self._packagePath = None
        if packagePath == None:
            self.setPackagePath(os.path.abspath('.'))
        else:
            self.setPackagePath(packagePath)
                    
        ## This call is needed so that the reporter can write to the working directory
        self._createDirectory(outputDirectory)
        self._preProcessing_ = list()
        self._postProcessing_ = list()
        self._parameters_ = {}
        self._modelModifiers_ = list()
        self._simulator_ = {}
        self.setStartTime(0)
        self.setStopTime(1)
        self.setTolerance(1E-6)
        self.setSolver("radau")
        self.setResultFile(modelName)
        self.setTimeOut(-1)
        self._MODELICA_EXE='dymola'
        self._reporter = reporter.Reporter(fileName=logFilNam)
        self._showProgressBar = True
        self._showGUI = False
        self._exitSimulator = True


    def setPackagePath(self, packagePath):
        ''' Set the path specified by ``packagePath``.
        
        :param packagePath: The path where the Modelica package to be loaded is located.
        
        It first checks whether the path exists and whether it is a directory. 
        If both conditions are satisfied, the path is set.
        Otherwise, a ``ValueError`` is raised.
        '''
        import os
        
        # Check whether the package Path parameter is correct
        if os.path.exists(packagePath) == False:
            msg = "Argument packagePath=%s does not exist." % packagePath
            raise ValueError(msg)

        if os.path.isdir(packagePath) == False:
            msg = "Argument packagePath=%s must be a directory " % packagePath
            msg +="containing a Modelica package."
            raise ValueError(msg)

        # Check whether the file package.mo exists in the directory specified
#        fileMo = os.path.abspath(os.path.join(packagePath, "package.mo"))
        #if os.path.isfile(fileMo) == False:
            #msg = "The directory '%s' does not contain the required " % packagePath
            #msg +="file '%s'." %fileMo
            #raise ValueError(msg)

        # All the checks have been successfully passed
        self._packagePath = packagePath
                    

    def _createDirectory(self, directoryName):
        ''' Creates the directory *directoryName*

        :param directoryName: The name of the directory

        This method validates the directory *directoryName* and if the
        argument is valid and write permissions exists, it creates the
        directory. Otherwise, a *ValueError* is raised.
        '''
        import os

        if directoryName != '.':
            if len(directoryName) == 0:
                raise ValueError("Specified directory is not valid. Set to '.' for current directory.")
            # Try to create directory
            if not os.path.exists(directoryName):
                os.makedirs(directoryName)
            # Check write permission
            if not os.access(directoryName, os.W_OK):
                raise ValueError("Write permission to '" + directoryName + "' denied.")

    def addPreProcessingStatement(self, command):
        '''Adds a pre-processing statement to the simulation script.

        :param statement: A script statement.

        Usage: Type
           >>> from buildingspy.simulate.Simulator import Simulator
           >>> s=Simulator("myPackage.myModel", "dymola", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.addPreProcessingStatement("Advanced.StoreProtectedVariables:= true;")
           >>> s.addPreProcessingStatement("Advanced.GenerateTimers = true;")

        This will execute the two statements after the ``openModel`` and
        before the ``simulateModel`` statement.
        '''
        self._preProcessing_.append(command)
        return

    def addPostProcessingStatement(self, command):
        '''Adds a post-processing statement to the simulation script.

        :param statement: A script statement.

        This will execute ``command`` after the simulation, and before
        the log file is written.
        '''
        self._postProcessing_.append(command)
        return

    def addParameters(self, dictionary):
        '''Adds parameter declarations to the simulator.

        :param dictionary: A dictionary with the parameter values

        Usage: Type
           >>> from buildingspy.simulate.Simulator import Simulator
           >>> s=Simulator("myPackage.myModel", "dymola", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.addParameters({'PID.k': 1.0, 'valve.m_flow_nominal' : 0.1})
           >>> s.addParameters({'PID.t': 10.0})

        This will add the three parameters ``PID.k``, ``valve.m_flow_nominal``
        and ``PID.t`` to the list of model parameters.

        For parameters that are arrays, use a syntax such as
           >>> from buildingspy.simulate.Simulator import Simulator
           >>> s = Simulator("MyModelicaLibrary.Examples.Constants", "dymola", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.addParameters({'const1.k' : [2, 3]})
           >>> s.addParameters({'const2.k' : [[1.1, 1.2], [2.1, 2.2], [3.1, 3.2]]})

        Do not use curly brackets for the values of parameters, such as
        ``s.addParameters({'const1.k' : {2, 3}})``
        as Python converts this entry to ``{'const1.k': set([2, 3])}``.

        '''
        self._parameters_.update(dictionary)
        return

    def getParameters(self):
        '''Returns a list of parameters as (key, value)-tuples.

        :return: A list of parameters as (key, value)-tuples.

        Usage: Type
           >>> from buildingspy.simulate.Simulator import Simulator
           >>> s=Simulator("myPackage.myModel", "dymola", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.addParameters({'PID.k': 1.0, 'valve.m_flow_nominal' : 0.1})
           >>> s.getParameters()
           [('valve.m_flow_nominal', 0.1), ('PID.k', 1.0)]
        '''
        return self._parameters_.items()

    def getOutputDirectory(self):
        '''Returns the name of the output directory.

        :return: The name of the output directory.

        '''
        return self._outputDir_
    
    def getPackagePath(self):
        '''Returns the path of the directory containing the Modelica package.

        :return: The paht of the Modelica package directory.

        '''
        return self._packagePath
        
    def addModelModifier(self, modelModifier):
        '''Adds a model modifier.

        :param dictionary: A model modifier.

        Usage: Type
           >>> from buildingspy.simulate.Simulator import Simulator
           >>> s=Simulator("myPackage.myModel", "dymola", packagePath="buildingspy/tests/MyModelicaLibrary")
           >>> s.addModelModifier('redeclare package MediumA = Buildings.Media.IdealGases.SimpleAir')

        This method adds a model modifier. The modifier is added to the list
        of model parameters. For example, the above statement would yield the
        command
        ``simulateModel(myPackage.myModel(redeclare package MediumA = Buildings.Media.IdealGases.SimpleAir), startTime=...``

        '''
        self._modelModifiers_.append(modelModifier)
        return

    def getSimulatorSettings(self):
        '''Returns a list of settings for the parameter as (key, value)-tuples.

        :return: A list of parameters (key, value) pairs, as 2-tuples.

        This method is deprecated. Use :meth:`~Simulator.getParameters` instead.

        '''
        raise DeprecationWarning("The method Simulator.getSimulatorSettings() is deprecated. Use Simulator.getParameters() instead.")
        return self.getParameters()

    def setStartTime(self, t0):
        '''Sets the start time.

        :param t0: The start time of the simulation in seconds.

        The default stop time is 1.
        '''
        self._simulator_.update(t0=t0)
        return

    def setStopTime(self, t1):
        '''Sets the start time.

        :param t0: The start time of the simulation in seconds.

        The default start time is 0.
        '''
        self._simulator_.update(t1=t1)
        return

    def setTimeOut(self, sec):
        '''Sets the time out after which the simulation will be killed.

        :param sec: The time out after which the simulation will be killed.

        The default value is -1, which means that the simulation will
        never be killed.
        '''
        self._simulator_.update(timeout=sec)
        return

    def setTolerance(self, eps):
        '''Sets the solver tolerance.

        :param eps: The solver tolerance.

        The default solver tolerance is 1E-6.
        '''
        self._simulator_.update(eps=eps)
        return

    def setSolver(self, solver):
        '''Sets the solver.

        :param solver: The name of the solver.

        The default solver is *radau*.
        '''
        self._simulator_.update(solver=solver)
        return

    def setNumberOfIntervals(self, n):
        '''Sets the number of output intervals.

        :param n: The number of output intervals.

        The default is unspecified, which defaults by Dymola to 500.
        '''
        self._simulator_.update(numberOfIntervals=n)
        return

    def setResultFile(self, resultFile):
        '''Sets the name of the result file (without extension).

        :param resultFile: The name of the result file (without extension).

        '''
        # If resultFile=aa.bb.cc, then split returns [aa, bb, cc]
        # This is needed to get the short model name
        rs=resultFile.split(".")
        self._simulator_.update(resultFile=rs[len(rs)-1])
        return

    def exitSimulator(self, exitAfterSimulation=True):
        ''' This function allows avoiding that the simulator terminates.

        :param exit: Set to ``False`` to avoid the simulator from terminating
                     after the simulation.

        This function is useful during debugging, as it allows to
        keep the simulator open after the simulation in order to
        inspect results or log messages.

        '''
        self._exitSimulator = exitAfterSimulation
        return

    def simulate(self):
        '''Simulates the model.

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

        '''
        import sys
        import os
        import tempfile
        import getpass
        import shutil


        def to_modelica(arg):
            """ Convert to Modelica array.
            """
            # Check for strings and booleans
            if isinstance(arg, str):
                return repr(arg)
            elif isinstance(arg, bool):
                if arg is True:
                    return 'true'
                else:
                    return 'false'
            try:
                return '{' + ", ".join(to_modelica(x) for x in arg) + '}'
            except TypeError:
                return repr(arg)

        # Delete dymola output files
        self.deleteOutputFiles()

        # Get directory name. This ensures for example that if the directory is called xx/Buildings
        # then the simulations will be done in tmp??/Buildings
        curDir = os.path.abspath(self._packagePath)
        ds=curDir.split(os.sep)
        dirNam=ds[len(ds)-1]
        worDir = os.path.join(tempfile.mkdtemp(prefix='tmp-simulator-' + getpass.getuser() + '-'), dirNam)
        # Copy directory
        shutil.copytree(os.path.abspath(self._packagePath), worDir)

        # Construct the model instance with all parameter values
        # and the package redeclarations
        dec = list()
        for k, v in self._parameters_.items():
            # Dymola requires vectors of parameters to be set in the format
            # p = {1, 2, 3} rather than in the format of python arrays, which 
            # is p = [1, 2, 3].
            # Hence, we convert the value of the parameter if required.
            s = to_modelica(v)
            dec.append('{param}={value}'.format(param=k, value=s))

        dec.extend(self._modelModifiers_)

        mi = '"{mn}({dec})"'.format(mn=self.modelName, dec=','.join(dec))

        try:
            # Write the Modelica script
            runScriptName = os.path.join(worDir, "run.mos")
            fil=open(runScriptName, "w")
            fil.write("// File autogenerated\n")
            fil.write("// Do not edit.\n")
            fil.write('cd("' + worDir + '");\n')
            fil.write("Modelica.Utilities.Files.remove(\"simulator.log\");\n")
            fil.write("openModel(\"package.mo\");\n")
            fil.write('OutputCPUtime:=true;\n')
            # Pre-processing commands
            for prePro in self._preProcessing_:
                fil.write(prePro + '\n')

            fil.write('modelInstance=' + mi + ';\n')
            fil.write('simulateModel(modelInstance, ')
            fil.write('startTime=' + str(self._simulator_.get('t0')) + \
                          ', stopTime='  + str(self._simulator_.get('t1')) + \
                          ', method="' + self._simulator_.get('solver') + '"' + \
                          ', tolerance=' + str(self._simulator_.get('eps')) + \
                          ', resultFile="' + str(self._simulator_.get('resultFile')
                                                 + '"'))
            if self._simulator_.has_key('numberOfIntervals'):
                fil.write(', numberOfIntervals=' +
                          str(self._simulator_.get('numberOfIntervals')))
            fil.write(');\n')
            # Post-processing commands
            for posPro in self._postProcessing_:
                fil.write(posPro + '\n')

            fil.write("savelog(\"simulator.log\");\n")
            if self._exitSimulator:
                fil.write("Modelica.Utilities.System.exit();\n")
            fil.close()
            # Copy files to working directory

            # Run simulation
            self._runSimulation(runScriptName,
                                 self._simulator_.get('timeout'),
                                 worDir)
            self._copyResultFiles(worDir)
            self._deleteTemporaryDirectory(worDir)
        except: # Catch all possible exceptions
            sys.exc_info()[1]
            self._reporter.writeError("Simulation failed in '" + worDir + "'\n"
                                       + "   You need to delete the directory manually.")
            raise

    def deleteOutputFiles(self):
        ''' Deletes the output files of the simulator.
        '''
        filLis=['buildlog.txt', 'dsfinal.txt', 'dsin.txt', 'dslog.txt',
                'dsmodel*', 'dymosim', 'dymosim.exe',
                str(self._simulator_.get('resultFile')) + '.mat',
                'request.', 'status', 'failure', 'stop']
        self._deleteFiles(filLis)

    def deleteLogFiles(self):
        ''' Deletes the log files of the Python simulator, e.g. the
            files ``BuildingsPy.log``, ``run.mos`` and ``simulator.log``.
        '''
        filLis=['BuildingsPy.log', 'run.mos', 'simulator.log']
        self._deleteFiles(filLis)

    def _deleteFiles(self, fileList):
        ''' Deletes the output files of the simulator.

        :param fileList: List of files to be deleted.

        '''
        import os

        for fil in fileList:
            try:
                if os.path.exists(fil):
                    os.remove(fil)
            except OSError as e:
                self._reporter.writeError("Failed to delete '" + fil + "' : " + e.strerror)

    def showGUI(self, show=True):
        ''' Call this function to show the GUI of the simulator.

        By default, the simulator runs without GUI
        '''
        self._showGUI = show;
        return

    def printModelAndTime(self):
        ''' Prints the current time and the model name to the standard output.

        This method may be used to print logging information.
        '''
        import time
        self._reporter.writeOutput("Model name       = " + self.modelName + '\n' +
                                    "Output directory = " + self._outputDir_ + '\n' +
                                    "Time             = " + time.asctime() + '\n')
        return

    def _copyResultFiles(self, srcDir):
        ''' Copies the output files of the simulator.

        :param srcDir: The source directory of the files

        '''
        import shutil
        import os

        if self._outputDir_ != '.':
            self._createDirectory(self._outputDir_)
        filLis=['run.mos', 'simulator.log', 'dslog.txt',
                self._simulator_.get('resultFile') + '.mat']
        for fil in filLis:
            srcFil = os.path.join(srcDir, fil)
            newFil = os.path.join(self._outputDir_, fil)
            try:
                if os.path.exists(srcFil):
                    shutil.copy(srcFil, newFil)
            except IOError as e:
                self._reporter.writeError("Failed to copy '" +
                                           srcFil + "' to '" + newFil +
                                           "; : " + e.strerror)

    def _deleteTemporaryDirectory(self, worDir):
        ''' Deletes the working directory.

        :param srcDir: The name of the working directory.

        '''
        import shutil
        import os

        # Walk one level up, since we appended the name of the current directory to the name of the working directory
        dirNam=os.path.split(worDir)[0]
        # Make sure we don't delete a root directory
        if dirNam.find('tmp-simulator-') == -1:
            self._reporter.writeError("Failed to delete '" +
                                       dirNam + "' as it does not seem to be a valid directory name.")
        else:
            try:
                if os.path.exists(worDir):
                    shutil.rmtree(dirNam)
            except IOError as e:
                self._reporter.writeError("Failed to delete '" +
                                           worDir + ": " + e.strerror)

    def _isExecutable(self, program):
        import os
        import platform

        def is_exe(fpath):
            return os.path.exists(fpath) and os.access(fpath, os.X_OK)

        # Add .exe, which is needed on Windows 7 to test existence
        # of the program
        if platform.system() == "Windows":
            program=program + ".exe"

        if is_exe(program):
            return True
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return True
        return False

    def _runSimulation(self, mosFile, timeout, directory):
        '''Runs the simulation.

        :param mosFile: The Modelica *mos* file name, including extension
        :param timeout: Time out in seconds
        :param directory: The working directory

        '''

        import sys
        import subprocess
        import time
        import datetime

        # List of command and arguments
        if self._showGUI:
            cmd=[self._MODELICA_EXE, mosFile]
        else:
            cmd=[self._MODELICA_EXE, mosFile, "/nowindow"]
#        cmd=[self._MODELICA_EXE, mosFile]
#        cmd=["sleep", "1"]

        # Check if executable is on the path
        if not self._isExecutable(cmd[0]):
            print "Error: Did not find executable '", cmd[0], "'."
            print "       Make sure it is on the PATH variable of your operating system."
            exit(3)
        # Run command
        try:
            staTim = datetime.datetime.now()
            self._reporter.writeOutput("Starting simulation in '" +
                                        directory + "' at " +
                                        str(staTim))
            pro = subprocess.Popen(args=cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   shell=False,
                                   cwd=directory)
            killedProcess=False
            if timeout > 0:
                while pro.poll() is None:
                    time.sleep(0.01)
                    elapsedTime = (datetime.datetime.now() - staTim).seconds

                    if elapsedTime > timeout:
                        # First, terminate the process. Then, if it is still
                        # running, kill the process

                        if killedProcess == False:
                            killedProcess=True
                            # This output needed because of the progress bar
                            sys.stdout.write("\n")
                            self._reporter.writeError("Terminating simulation in "
                                             + directory + ".")
                            pro.terminate()
                        else:
                            self._reporter.writeError("Killing simulation in "
                                             + directory + ".")
                            pro.kill()
                    else:
                        if self._showProgressBar:
                            fractionComplete = float(elapsedTime)/float(timeout)
                            self._printProgressBar(fractionComplete)

            else:
                pro.wait()
            # This output is needed because of the progress bar
            if not killedProcess:
                sys.stdout.write("\n")

            if not killedProcess:
                self._reporter.writeOutput("*** Standard output stream from simulation:\n" + pro.stdout.read())
                self._reporter.writeError("Standard error stream from simulation:\n" + pro.stderr.read())
            else:
                self._reporter.writeError("Killed process as it computed longer than " +
                             str(timeout) + " seconds.")

        except OSError as e:
            print "Execution of ", cmd, " failed:", e

    def showProgressBar(self, show=True):
        ''' Enables or disables the progress bar.

        :param show: Set to *false* to disable the progress bar.

        If this function is not called, then a progress bar will be shown as the simulation runs.
        '''
        self._showProgressBar = show
        return

    def _printProgressBar(self, fractionComplete):
        '''Prints a progress bar to the console.

        :param fractionComplete: The fraction of the time that is completed.

        '''
        import sys
        nInc = 50
        count=int(nInc*fractionComplete)
        proBar = "|"
        for i in range(nInc):
            if i < count:
                proBar += "-"
            else:
                proBar += " "
        proBar += "|"
        print proBar, int(fractionComplete*100), "%\r",
        sys.stdout.flush()
