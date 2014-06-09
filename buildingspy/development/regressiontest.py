#!/usr/bin/env python
#######################################################
# Script that runs all regression tests.
#
#
# MWetter@lbl.gov                            2011-02-23
#######################################################
from __future__ import division
import sys
import os


def runSimulation(worDir, cmd):
    ''' Run the simulation.

    :param worDir: The working directory.
    :param cmd: An array which is passed to the `args` argument of
                :mod:`subprocess.Popen`

    .. note:: This method is outside the class definition to
              allow parallel computing.

    '''

    import subprocess

    logFilNam=os.path.join(worDir, 'stdout.log')
    logFil = open(logFilNam, 'w')
    pro = subprocess.Popen(args=cmd,
                           stdout=logFil,
                           stderr=logFil,
                           shell=False,
                           cwd=worDir)
    try:
        retcode = pro.wait()

        logFil.close()
        if retcode != 0:
            print "Child was terminated by signal", retcode
            return retcode
        else:
            return 0
    except OSError as e:
        sys.stderr.write("Execution of '" + cmd + " runAll.mos /nowindow' failed.\n" +
                         "Working directory is '" + worDir + "'.")
        raise(e)
    except KeyboardInterrupt as e:
        pro.kill()
        sys.stderr.write("Users stopped simulation in %s.\n" % worDir)


class Tester:
    ''' Class that runs all regression tests using Dymola.

    Initiate with the following optional arguments:

    :param checkHtml: bool (default=True). Specify whether to load tidylib and
        perform validation of html documentation
    :param executable: {'dymola', 'omc'}.  Default is 'dymola', specifies the
        executable to use for running the regression test with :func:`~buildingspy.development.Tester.run`.
    :param cleanup: bool (default=True).  Specify whether to delete temporary directories.

    This class can be used to run all regression tests.
    It searches the directory ``CURRENT_DIRECTORY\Resources\Scripts\Dymola`` for
    all ``*.mos`` files that contain the string ``simulate``,
    where ``CURRENT_DIRECTORY`` is the name of the directory in which the Python
    script is started, as returned by the function :func:`getLibraryName`.
    All these files will be executed as part of the regression tests.
    Any variables or parameters that are plotted by these ``*.mos`` files
    will be compared to previous results that are stored in
    ``CURRENT_DIRECTORY\Resources\ReferenceResults\Dymola``.
    If no reference results exist, then they will be created.
    Otherwise, the accuracy of the new results is compared to the
    reference results. If they differ by more than a prescibed
    tolerance, a plot such as the one below is shown.

    .. figure:: img/unitTestPlot.png
       :width: 560 px

       Plot that compares the new results (solid line) of the regression test with the old results (dotted line).
       The blue line indicates the time where the largest error occurs.

    In this plot, the vertical line indicates the time where the biggest error
    occurs.
    The user is then asked to accept or reject the new results.

    To run the regression tests, type

       >>> import os
       >>> import buildingspy.development.regressiontest as r
       >>> rt = r.Tester()
       >>> myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
       >>> rt.setLibraryRoot(myMoLib)
       >>> rt.run() # doctest: +ELLIPSIS
       Using  ...  of ... processors to run unit tests.
       Number of models   :  1
                 blocks   :  0
                 functions:  0
       Generated  2  regression tests.
       <BLANKLINE>
       FMU export was not tested.
       Script that runs unit tests had 0 warnings and 0 errors.
       <BLANKLINE>
       See 'unitTests.log' for details.
       Unit tests completed successfully.
       <BLANKLINE>
       Execution time = ...

    To run regression tests only for a single package, call :func:`setSinglePackage`
    prior to :func:`run`.

    '''
    def __init__(self, check_html=True, executable="dymola", cleanup=True):
        ''' Constructor.
        '''
        import multiprocessing
        import buildingspy.io.reporter as rep

        # --------------------------
        # Class variables
        self._checkHtml = check_html
        self._libHome=os.path.abspath(".")
        self._modelicaCmd = executable
        # File to which the console output of the simulator is written to
        self._simulator_log_file = "simulator.log"
        # File to which statistics is written to
        self._statistics_log = "statistics.json"
        self._nPro = multiprocessing.cpu_count()
        self._batch = False

        # List of scripts that should be excluded from the regression tests
        #self._excludeMos=['Resources/Scripts/Dymola/Airflow/Multizone/Examples/OneOpenDoor.mos']
        self._excludeMos=[]

        # Number of data points that are used
        self._nPoi = 101

        # List of temporary directories that are used to run the simulations.
        self._temDir = []

        # Flag to delete temporary directories.
        self._deleteTemporaryDirectories = cleanup

        # Flag to use existing results instead of running a simulation
        self._useExistingResults = False

        '''
        List of dicts, each dict with all meta-information about a single model to be tested.
        keys equal to the ``*.mos`` file name, and values
                 containing a dictionary with keys ``matFil`` and ``y``.

                 The values of ``y`` are a list of the
                 form `[[a.x, a.y], [b.x, b.y1, b.y2]]` if the
                 mos file plots `a.x` versus `a.y` and `b.x` versus `(b.y1, b.y2)`.
        '''
        self._data = []
        self._reporter = rep.Reporter(os.path.join(os.getcwd(), "unitTests.log"))

        self._rootPackage = os.path.join(self._libHome, 'Resources', 'Scripts', 'Dymola')
        
        # By default, do not include export of FMUs.
        self._include_fmu_test = False

    def setLibraryRoot(self, rootDir):
        ''' Set the root directory of the library.

        :param rootDir: The top-most directory of the library.

        The root directory is the directory that contains the ``Resources`` folder
        and the top-level ``package.mo`` file.

        Usage: Type
           >>> import os
           >>> import buildingspy.development.regressiontest as r
           >>> rt = r.Tester()
           >>> myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
           >>> rt.setLibraryRoot(myMoLib)
        '''
        self._libHome = os.path.abspath(rootDir)
        self._rootPackage = os.path.join(self._libHome, 'Resources', 'Scripts', 'Dymola')
        self.isValidLibrary(self._libHome)

    def useExistingResults(self, dirs):
        ''' This function allows to use existing results, as opposed to running a simulation.

        :param dirs: A non-empty list of directories that contain existing results.

        This method can be used for testing and debugging. If called, then no simulation is
        run.
        If the directories
        ``['/tmp/tmp-Buildings-0-zABC44', '/tmp/tmp-Buildings-0-zQNS41']``
        contain previous results, then this method can be used as

        >>> import buildingspy.development.regressiontest as r
        >>> l=['/tmp/tmp-Buildings-0-zABC44', '/tmp/tmp-Buildings-0-zQNS41']
        >>> rt = r.Tester()
        >>> rt.useExistingResults(l)
        >>> rt.run() # doctest: +SKIP

        '''
        if len(dirs) == 0:
            raise ValueError("Argument 'dirs' of function 'useExistingResults(dirs)' must have at least one element.")

        self.setNumberOfThreads(len(dirs))
        self._temDir = dirs
        self.deleteTemporaryDirectories(False)
        self._useExistingResults = True

    def setNumberOfThreads(self, number):
        ''' Set the number of parallel threads that are used to run the regression tests.

        :param number: The number of parallel threads that are used to run the regression tests.

        By default, the number of parallel threads are set to be equal to the number of
        processors of the computer.
        '''
        self._nPro = number

    def batchMode(self, batchMode):
        ''' Set the batch mode flag.

        :param batchMode: Set to ``True`` to run without interactive prompts
                          and without plot windows.

        By default, the regression tests require the user to respond if results differ from previous simulations.
        This method can be used to run the script in batch mode, suppressing all prompts that require
        the user to enter a response. If run in batch mode, no new results will be stored.
        To run the regression tests in batch mode, enter

        >>> import os
        >>> import buildingspy.development.regressiontest as r
        >>> r = r.Tester()
        >>> r.batchMode(True)
        >>> r.run() # doctest: +SKIP

        '''
        self._batch = batchMode

    def include_fmu_tests(self, fmu_export):
        ''' Sets a flag that, if ``True``, also tests the export of FMUs.
        
        :param fmu_export: Set to ``True`` to test the export of FMUs.

        To run the unit tests and also test the export of FMUs, type
        >>> import os
        >>> import buildingspy.development.regressiontest as r
        >>> r = r.Tester()
        >>> r.include_fmu_tests(True)
        >>> r.run() # doctest: +SKIP

        '''
        self._include_fmu_test = fmu_export
        
    def getModelicaCommand(self):
        ''' Return the name of the modelica executable.

        :return: The name of the modelica executable.

        '''
        return self._modelicaCmd


    def isExecutable(self, program):
        """ Return ``True`` if the ``program`` is an executable
        """
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

    @staticmethod
    def isValidLibrary(library_home):
        ''' Returns true if the regression tester points to a valid library
            that implements the scripts for the regression tests.

        :param library_home: top-level directory of the library, such as ``Buildings``.
        :return: ``True`` if the library implements regression tests, ``False`` otherwise.
        '''
        topPackage = os.path.abspath(os.path.join(library_home, "package.mo"))
        if not os.path.isfile(topPackage):
            raise ValueError("Directory %s is not a Modelica library.\n    Expected file '%s'."
                             % (library_home, topPackage))
        srcDir = os.path.join(library_home, "Resources", "Scripts")
        if not os.path.exists(srcDir):
            raise ValueError("Directory %s is not a Modelica library.\n    Expected directories '%s'."
                             % (library_home, srcDir))

        return os.path.exists(os.path.join(library_home, "Resources", "Scripts"))

    def getLibraryName(self):
        ''' Return the name of the library that will be run by this regression test.

        :return: The name of the library that will be run by this regression test.
        '''
        return os.path.basename(self._libHome)

    def checkPythonModuleAvailability(self):
        ''' Check whether all required python modules are installed.

            If some modules are missing, then an `ImportError` is raised.
        '''
        requiredModules = ['buildingspy', 'matplotlib.pyplot', 'numpy', 'scipy.io']
        if self._checkHtml:
            requiredModules.append('tidylib')
        missingModules = []
        for module in requiredModules:
            try:
                __import__(module)
            except ImportError:
                missingModules.append(module)

        if len(missingModules) > 0:
            msg = "The following python module(s) are required but failed to load:\n"
            for mod in missingModules:
                msg += "  " + mod + "\n"
            msg += "You need to install these python modules to use this script.\n"
            raise ImportError(msg)

    def _checkKey(self, key, fileName, counter):
        ''' Check whether the file ``fileName`` contains the string ``key``
            as the first string on the first or second line.
            If ``key`` is found, increase the counter.
        '''

        filObj=open(fileName, 'r')
        filTex=filObj.readline()
        # Strip white spaces so we can test strpos for zero.
        # This test returns non-zero for partial classes.
        filTex.strip()
        strpos=filTex.find("within")
        if strpos == 0:
            # first line is "within ...
            # get second line
            filTex=filObj.readline()
            filTex.strip()
        strpos=filTex.find(key)
        if strpos == 0:
            counter += 1;
        filObj.close()
        return counter


    def _includeFile(self, fileName):
        ''' Returns true if the file need to be included in the list of scripts to run

        :param fileName: The name of the ``*.mos`` file.

        The parameter *fileName* need to be of the form
        *Resources/Scripts/Dymola/Fluid/Actuators/Examples/Damper.mos*
        or *Resources/Scripts/someOtherFile.ext*.
        This function checks if *fileName* exists in the global list
        self._excludeMos. During this check, all backward slashes will
        be replaced by a forward slash.
    '''
        pos=fileName.endswith('.mos')
        if pos > -1: # This is an mos file
            # Check whether the file is in the exclude list
            fileName = fileName.replace('\\', '/')
            # Remove all files, except a few for testing
    #        test=os.path.join('Resources','Scripts','Dymola','Controls','Continuous','Examples')
    ##        test=os.path.join('Resources', 'Scripts', 'Dymola', 'Fluid', 'Movers', 'Examples')
    ##        if fileName.find(test) != 0:
    ##            return False

            if (self._excludeMos.count(fileName) == 0):
                return True
            else:
                print "*** Warning: Excluded file ", fileName, " from the regression tests."
                return False
        else:
            False

    def setSinglePackage(self, packageName):
        '''
        Set the name of a single Modelica package to be tested.

        :param packageName: The name of the package to be tested.

        Calling this method will cause the regression tests to run
        only for the examples in the package ``packageName``, and in
        all its sub-packages. For example, if ``packageName = Annex60.Fluid.Sensors``,
        then a test of the ``Annex60`` library will run all examples in
        ``Annex60.Fluid.Sensors.*``.

        '''
        import string

        # Issue a warning to inform the user that not all tests are run
        self._reporter.writeWarning("""Regression tests are only run for '%s'.""" % packageName)
        # Remove the top-level package name as the unit test directory does not
        # contain the name of the library.
        pacPat = packageName[string.find(packageName, '.')+1:]
        pacPat = pacPat.replace('.', os.sep)
        rooPat = os.path.join(self._libHome, 'Resources', 'Scripts', 'Dymola', pacPat)
        # Verify that the directory indeed exists
        if not os.path.isdir(rooPat):
            msg = """Requested to test only package '%s', but directory
'%s' does not exist.""" % (packageName, rooPat)
            raise ValueError(msg)
        
        self._rootPackage = rooPat

    def setDataDictionary(self):
        ''' Build the data structures that are needed to parse the output files.

        '''
        import re

        for root, _, files in os.walk(self._rootPackage):
            pos=root.find('.svn')
            # skip .svn folders
            if pos == -1:
                for mosFil in files:
                    # Exclude the conversion scripts and also backup copies
                    # which have the extensions .mos~ if they are generated from emacs
                    if mosFil.endswith('.mos') and (not mosFil.startswith("Convert" + self.getLibraryName())):
                        matFil = ""
                        dat = {}
                        dat['ScriptDirectory'] = root[\
                            len(os.path.join(self._libHome, 'Resources', 'Scripts', 'Dymola'))+1:]
                        dat['ScriptFile'] = mosFil
                        dat['mustSimulate'] = False

                        # open the mos file and read its content.
                        # Path and name of mos file without 'Resources/Scripts/Dymola'
                        fMOS=open(os.path.join(root, mosFil), 'r')
                        Lines=fMOS.readlines()
                        fMOS.close()

                        # Remove white spaces
                        for i in range(len(Lines)):
                            Lines[i] = Lines[i].replace(' ', '')

                        # Set some attributes in the Data object
                        if self._includeFile(os.path.join(root, mosFil)):
                            for lin in Lines:
                                # Add the model name to the dictionary.
                                # This is needed to export the model as an FMU.
                                # Also, set the flag mustSimulate to True.
                                simCom=re.search('simulateModel\\(\s*".*"', lin)
                                if simCom is not None:
                                        modNam = re.sub('simulateModel\\(\s*"', '', simCom.string)
                                        modNam = modNam[0:modNam.index('"')]
                                        dat['mustSimulate'] = True
                                        dat['modelName'] = modNam
                                # parse startTime and stopTime, if any
                                for attr in ["startTime", "stopTime"]:
                                    pos = lin.find(attr)
                                    if pos > -1:
                                        # attribute found.  Get the value.
                                        posEq = lin.find('=', pos)
                                        posComma = lin.find(',', pos)
                                        posBracket = lin.find(')', pos)
                                        posEnd = min(posComma,posBracket)
                                        if posEnd < 0:
                                            posEnd = max(posComma,posBracket)
                                        valueString = lin[posEq+1:posEnd]
                                        dat[attr] = valueString

                        plotVars = []
                        iLin=0
                        for lin in Lines:
                            iLin=iLin+1
                            if 'y={' in lin:
                                try:
                                    var=re.search('{.*?}', lin).group()
                                except AttributeError:
                                    s =  "%s, line %s, could not be parsed.\n" % (mosFil, iLin)
                                    s +=  "The problem occurred at the line below:\n"
                                    s +=  "%s\n" % lin
                                    s += "Make sure that each assignment of the plot command is on one line.\n"
                                    s += "Regression tests failed with error.\n"
                                    self._reporter.writeError(s)
                                    raise
                                var=var.strip('{}"')
                                y = var.split('","')
                                # Replace a[1,1] by a[1, 1], which is required for the
                                # Reader to be able to read the result.
                                for i in range(len(y)):
                                    y[i] = y[i].replace(",", ", ")
                                plotVars.append(y)
                        if len(plotVars) == 0:
                            s =  "%s does not contain any plot command.\n" % mosFil
                            s += "You need to add a plot command to include its\n"
                            s += "results in the regression tests.\n"
                            self._reporter.writeError(s)

                        dat['ResultVariables'] = plotVars

                        # search for the result file
                        for lin in Lines:
                            if 'resultFile=\"' in lin:
                                matFil = re.search('(?<=resultFile=\")\w+', lin).group()
                                matFil =  matFil + '.mat'
                                break
                        # Some *.mos file only contain plot commands, but no simulation.
                        # Hence, if 'resultFile=' could not be found, try to get the file that
                        # is used for plotting.
                        if len(matFil) == 0:
                            for lin in Lines:
                                if 'filename=\"' in lin:
                                    matFil = re.search('(?<=filename=\")\w+', lin).group()
                                    matFil = matFil + '.mat'
                                    break
                        if len(matFil) == 0:
                            raise  ValueError('Did not find *.mat file in ' + mosFil)
                        dat['ResultFile'] = matFil
                        self._data.append(dat)
        # Make sure we found at least one unit test
        if len(self._data) == 0:
            msg = """Did not find any regression tests in '%s'.""" % self._rootPackage
            raise ValueError(msg)

        self._checkDataDictionary()
        return

    def _checkDataDictionary(self):
        ''' Check if the data used to run the regression tests do not have duplicate ``*.mat`` files.

            Since Dymola writes all ``*.mat`` files to the current working directory,
            duplicate ``*.mat`` file names would cause a simulation to overwrite the results
            of a previous simulation. This would make it impossible to compare the results
            to previously obtained results.

            If there are duplicate ``*.mat`` file names used, then this method throws
            a ``ValueError`` exception.

        '''
        s = set()
        errMes = ""
        for data in self._data:
            resFil = data['ResultFile']
            if data['mustSimulate']:
                if resFil in s:
                    errMes += "*** Error: Result file %s is generated by more than one script.\n" \
                        "           You need to make sure that all scripts use unique result file names.\n" % resFil
                else:
                    s.add(resFil)
        if len(errMes) > 0:
            raise ValueError(errMes)

    def _getTimeGrid(self, tMin, tMax, nPoi):
        '''
        Return the time grid for the output result interpolation

        :param tMin: Minimum time of the results.
        :param tMax: Maximum time of the results.
        :param nPoi: Number of result points.
        '''
        return [ tMin+float(i)/(nPoi-1)*(tMax-tMin) for i in range(nPoi) ]

    def _getSimulationResults(self, data, warnings, errors):
        '''
        Get the simulation results.

        :param data: The class that contains the data structure for the simulation results.
        :param warning: An empty list in which all warnings will be written.
        :param errors: An empty list in which all errors will be written.

        Extracts and returns the simulation results from the `*.mat` file as
        a list of dictionaries. Each element of the list contains a dictionary
        of results that need to be printed together.
        '''
        from buildingspy.io.outputfile import Reader
        from buildingspy.io.postprocess import Plotter

        def extractData(y, step):
            # Replace the last element with the last element in time,
            # [::step] may not extract the last time stamp, in which case
            # the final time changes when the number of event changes.
            r=y[::step]
            r[len(r)-1] = y[len(y)-1]
            return r

        # Get the working directory that contains the ".mat" file
        fulFilNam=os.path.join(data['ResultDirectory'], self.getLibraryName(), data['ResultFile'])
        ret=[]
        try:
            r=Reader(fulFilNam, "dymola")
        except IOError as e:
            errors.append("Failed to read %s generated by %s.\n%s\n" % (fulFilNam, data['ScriptFile'], e.strerror))
            return ret

        for pai in data['ResultVariables']: # pairs of variables that are plotted together
            dat=dict()
            for var in pai:
                time = []
                val = []
                try:
                    (time, val) = r.values(var)
                    # Make time grid to which simulation results
                    # will be interpolated.
                    # This reduces the data that need to be stored.
                    # It also makes it easier to compare accuracy
                    # in case that a slight change in the location of
                    # state events triggered a different output interval grid.
                    tMin=float(min(time))
                    tMax=float(max(time))
                    nPoi = min(self._nPoi, len(val))
                    ti = self._getTimeGrid(tMin, tMax, nPoi)
                except ZeroDivisionError as e:
                    s = "When processing " + fulFilNam + " generated by " + data['ScriptFile'] + ", caught division by zero.\n"
                    s += "   len(val)  = " + str(len(val)) + "\n"
                    s += "   tMax-tMin = " + str(tMax-tMin) + "\n"
                    warnings.append(s)
                    break

                except KeyError:
                    warnings.append("%s uses %s which does not exist in %s.\n" %
                                     (data['ScriptFile'], var, data['ResultFile']))
                else:
                    # Store time grid.
                    if ('time' not in dat):
                        dat['time']=[tMin, tMax]

                    if self._isParameter(val):
                        dat[var] = val
                    else:
                        dat[var]=Plotter.interpolate(ti, time, val)

            if len(dat) > 0:
                ret.append(dat)
        return ret

    def areResultsEqual(self, tOld, yOld, tNew, yNew, varNam, filNam):
        ''' Return `True` if the data series are equal within a tolerance.

        :param tOld: List of old time values.
        :param yOld: Old simulation results.
        :param tNew: Time stamps of new results.
        :param yNew: New simulation results.
        :param varNam: Variable name, used for reporting.
        :param filNam: File name, used for reporting.
        :return: A list with ``False`` if the results are not equal, and the time
                 of the maximum error, and a warning message or `None`.
                 In case of errors, the time of the maximum error may by `None`.
        '''
        import numpy as np
        from buildingspy.io.postprocess import Plotter

        def getTimeGrid(t):
            if len(t) == 2:
                return self._getTimeGrid(t[0], t[-1], self._nPoi)
            elif len(t) == self._nPoi:
                return t
            else:
                s = "The new time grid has %d points, but it must have 2 or %d points.\n\
            Stop processing %s\n" % (len(tNew), self._nPoi, filNam)
                raise ValueError(s)

        if (abs(tOld[-1]-tNew[-1]) > 1E-5):
            msg = """The new results and the reference results have a different end time.
            tNew = [%d, %d]
            tOld = [%d, %d]""" % (tNew[0], tNew[-1], tOld[0], tOld[-1])            
            return (False, min(tOld[-1], tNew[-1]), msg)

        if (abs(tOld[0]-tNew[0]) > 1E-5):
            msg = """The new results and the reference results have a different start time.
            tNew = [%d, %d]
            tOld = [%d, %d]""" % (tNew[0], tNew[-1], tOld[0], tOld[-1])            
            return (False, min(tOld[0], tNew[0]), msg)
        
        timMaxErr = 0

        tol=1E-3  #Tolerance

        # Interpolate the new variables to the old time stamps
        #
        # The next test may be true if a simulation stopped with an error prior to producing sufficient data points
        if len(yNew) < len(yOld) and len(yNew) > 2:
            warning = """%s: %s has fewer data points than reference results.
len(yOld) = %d,
len(yNew) = %d
Skipping error checking for this variable.""" % (filNam, varNam, len(yOld), len(yNew))
            return (False, None, warning)

        if len(yNew) > 2:
            # Some reference results contain already a time grid,
            # whereas others only contain the first and last time stamp.
            # Hence, we make sure to have the right time grid before we
            # call the interpolation.
            tGriOld = getTimeGrid(tOld)
            tGriNew = getTimeGrid(tNew)
            try:
                yInt = Plotter.interpolate(tGriOld, tGriNew, yNew)
            except IndexError:
                raise IndexError(
"""Data series have different length:
File=%s,
variable=%s,
len(tGriOld) = %d,
len(tGriNew) = %d,
len(yNew)    = %d""" % (filNam, varNam, len(tGriOld), len(tGriNew), len(yNew)))
        else:
            yInt = [yNew[0], yNew[0]]

        # If the variable is heatPort.T or heatPort.Q_flow, with lenght=2, then
        # it has been evaluated as a parameter in the Buildings library. In the Annex60
        # library, this may be a variable as the Buildings library uses a more efficient
        # implementation of the heatPort. Hence, we test for this special case, and
        # store the parameter as if it were a variable so that the reference result are not
        # going to be changed.
        if (varNam.endswith("heatPort.T") or varNam.endswith("heatPort.Q_flow")) and (len(yInt) == 2) \
        and len(yOld) != len(yInt):
            yInt = np.ones(len(yOld)) * yInt[0]
            
        # Compute error for the variable with name varNam
        if len(yOld) != len(yInt):
            # If yOld has two points, by yInt has more points, then
            # extrapolate yOld to nPoi
            t = self._getTimeGrid(tOld[0], tOld[-1], self._nPoi)
            if len(yOld) == 2 and len(yInt) == self._nPoi:
                t = self._getTimeGrid(t[0], t[-1], self._nPoi)
                yOld = Plotter.interpolate(t, tOld, yOld)
            # If yInt has only two data points, but yOld has more, then interpolate yInt
            elif len(yInt) == 2 and len(yOld) == self._nPoi:
                yInt = Plotter.interpolate(t, [tOld[0], tOld[-1]], yInt)            
            else:
                raise ValueError("""Program error, yOld and yInt have different lengths.
  Result file : %s
  Variable    : %s
  len(yOld)=%d
  len(yInt)=%d
  Stop processing.""" % (filNam, varNam, len(yOld), len(yInt)))

        errAbs=np.zeros(len(yInt))
        errRel=np.zeros(len(yInt))
        errFun=np.zeros(len(yInt))

        for i in range(len(yInt)):
            errAbs[i] = abs(yOld[i] - yInt[i])
            if np.isnan(errAbs[i]):
                raise ValueError('NaN in errAbs ' + varNam + " "  + str(yOld[i]) +
                                 "  " + str(yInt[i]) + " i, N " + str(i) + " --:" + str(yInt[i-1]) +
                                 " ++:", str(yInt[i+1]))
            if (abs(yOld[i]) > 10*tol):
                errRel[i] = errAbs[i] / abs(yOld[i])
            else:
                errRel[i] = 0
            errFun[i] = errAbs[i] + errRel[i]
        if max(errFun) > tol:
            iMax = 0
            eMax = 0
            for i in range(len(errFun)):
                if errFun[i] > eMax:
                    eMax = errFun[i]
                    iMax = i
            tGri = self._getTimeGrid(tOld[0], tOld[-1], self._nPoi)
            timMaxErr = tGri[iMax]
            warning = filNam + ": " + varNam + " has absolute and relative error = " + \
                ("%0.3e" % max(errAbs)) + ", " + ("%0.3e" % max(errRel)) + ".\n"
            if self._isParameter(yInt):
                warning += "             %s is a parameter.\n" % varNam
            else:
                warning += "             Maximum error is at t = %s\n" % str(timMaxErr)

            return (False, timMaxErr, warning)
        else:
            return (True, timMaxErr, None)

    def _isParameter(self, dataSeries):
        ''' Return `True` if `dataSeries` is from a parameter.
        '''
        import numpy as np
        if not (isinstance(dataSeries, np.ndarray) or isinstance(dataSeries, list)):
            raise TypeError("Program error: dataSeries must be a numpy.ndarr or a list. Received type " \
                                + str(type(dataSeries)) + ".\n")
        return (len(dataSeries) == 2)

    def _writeReferenceResults(self, refFilNam, yS):
        ''' Write the reference results.

        :param refFilNam: The name of the reference file.
        :param yS: The data points to be written to the file.

        This method writes the results in the form ``key=value``, with one line per entry.
        '''
        from datetime import date

        def formatFloat(value):
            return "%.20f" % value

        f=open(refFilNam, 'w')
        f.write('last-generated=' + str(date.today()) + '\n')
        # Set, used to avoid that data series that are plotted in two plots are
        # written twice to the reference data file.
        s = set()
        for pai in yS:
            for k, v in pai.items():
                if k not in s:
                    s.add(k)
                    f.write(k + '=')
                    # Use many digits, otherwise truncation errors occur that can be higher
                    # than the required accuracy.
                    formatted = [formatFloat(e) for e in v]
                    f.write(str(formatted).replace("'", ""))
                    f.write('\n')
        f.close()

    def _readReferenceResults(self, refFilNam):
        ''' Read the reference results.

        :param refFilNam: The name of the reference file.
        :return: A dictionary with the reference results.

        '''
        import numpy

        d = dict()
        f=open(refFilNam,'r')
        lines = f.readlines()
        f.close()

        # Compute the number of the first line that contains the results
        iSta=0
        for iLin in range(min(2, len(lines))):
            if "svn-id" in lines[iLin]:
                iSta=iSta+1
            if "last-generated" in lines[iLin]:
                iSta=iSta+1

        r = dict()
        for i in range(iSta, len(lines)):
            lin = lines[i].strip('\n')

            try:
                (key, value) = lin.split("=")
                s = (value[value.find('[')+1: value.rfind(']')]).strip()
                numAsStr=s.split(',')
            except ValueError as detail:
                s =  "%s could not be parsed.\n" % refFilNam
                self._reporter.writeError(s)
                raise TypeError(detail)

            val = []
            for num in numAsStr:
                # We need to use numpy.float64 here for the comparison to work
                val.append(numpy.float64(num))
            r[key] = val
        d['results'] = r
        return d

    def _askNoReferenceResultsFound(self, yS, refFilNam, ans):
        ''' Ask user what to do if no reference data were found
           :param yS: A list where each element is a dictionary of variable names and simulation
                      results that are to be plotted together.
           :param refFilNam: Name of reference file (used for reporting only).
           :param ans: A previously entered answer, either ``y``, ``Y``, ``n`` or ``N``.
           :return: A triple ``(updateReferenceData, foundError, ans)`` where ``updateReferenceData``
                    and ``foundError`` are booleans, and ``ans`` is ``y``, ``Y``, ``n`` or ``N``.

        '''
        updateReferenceData = False
        foundError = False

        if len(yS) > 0:
            sys.stdout.write("*** Warning: The old reference data had no results, but the new simulation produced results\n")
            sys.stdout.write("             for %s\n" % refFilNam)
            sys.stdout.write("             Accept new results?\n")
            while not (ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                ans = raw_input("             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")
            if ans == "y" or ans == "Y":
                # update the flag
                updateReferenceData = True
        return (updateReferenceData, foundError, ans)

    def _compareResults(self, matFilNam, oldRefFulFilNam, yS, refFilNam, ans):
        ''' Compares the new and the old results.

            :param matFilNam: Matlab file name.
            :param oldRefFilFilNam: File name including path of old reference files.
            :param yS: A list where each element is a dictionary of variable names and simulation
                           results that are to be plotted together.
            :param refFilNam: Name of the file with reference results (used for reporting only).
            :param ans: A previously entered answer, either ``y``, ``Y``, ``n`` or ``N``.
            :return: A triple ``(updateReferenceData, foundError, ans)`` where ``updateReferenceData``
                     and ``foundError`` are booleans, and ``ans`` is ``y``, ``Y``, ``n`` or ``N``.

        '''
        import matplotlib.pyplot as plt

        # Reset answer, unless it is set to Y or N
        if not (ans == "Y" or ans == "N"):
            ans = "-"
        updateReferenceData = False
        foundError = False
        verifiedTime = False

        #Load the old data (in dictionary format)
        d = self._readReferenceResults(oldRefFulFilNam)
        yR=d['results']

        if len(yR) == 0:
            return self._askNoReferenceResultsFound(yS, refFilNam, ans)

        # The old data contains results
        tR=yR.get('time')

        # Iterate over the pairs of data that are to be plotted together
        timOfMaxErr = dict()
        noOldResults = [] # List of variables for which no old results have been found
        for pai in yS:
            tS=pai['time']
            if not verifiedTime:
                verifiedTime = True

                # Check if the first and last time stamp are equal
                tolTim = 1E-3 # Tolerance for time
                if (abs(tR[0] - tS[0]) > tolTim) or abs(tR[-1] - tS[-1]) > tolTim:
                    print "*** Warning: Different simulation time interval in ", refFilNam, " and ", matFilNam
                    print "             Old reference points are for " , tR[0], ' <= t <= ', tR[len(tR)-1]
                    print "             New reference points are for " , tS[0], ' <= t <= ', tS[len(tS)-1]
                    foundError = True
                    while not (ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                        print "             Accept new results and update reference file in library?"
                        ans = raw_input("             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")
                    if ans == "y" or ans == "Y":
                        # Write results to reference file
                        updateReferenceData = True
                        return (updateReferenceData, foundError, ans)

            # The time interval is the same for the stored and the current data.
            # Check the accuracy of the simulation.
            for varNam in pai.keys(): # Iterate over the variable names that are to be plotted together
                if varNam != 'time':
                    if yR.has_key(varNam):
                        # Check results
                        if self._isParameter(pai[varNam]):
                            t=[min(tS), max(tS)]
                        else:
                            t=tS

                        (res, timMaxErr, warning) = self.areResultsEqual(tR, yR[varNam], \
                                                                         t, pai[varNam], \
                                                                         varNam, matFilNam)
                        if warning:
                            self._reporter.writeWarning(warning)
                        if not res:
                            foundError = True
                            timOfMaxErr[varNam] = timMaxErr
                    else:
                        # There is no old data series for this variable name
                        self._reporter.writeWarning("Did not find variable " + varNam + " in old results.")
                        foundError = True
                        noOldResults.append(varNam)

        # If the users selected "Y" or "N" (to not accept or reject any new results) in previous tests,
        # or if the script is run in batch mode, then don't plot the results.
        # If we found an error, plot the results, and ask the user to accept or reject the new values.
        if foundError and (not self._batch) and (not ans == "N") and (not ans == "Y"):
            print "             Acccept new file and update reference files? (Close plot window to continue.)"
            nPlo = len(yS)
            iPlo = 0
            plt.clf()
            for pai in yS:
                iPlo += 1
                plt.subplot(nPlo, 1, iPlo)
                # Iterate over the variable names that are to be plotted together
                color=['k', 'r', 'b', 'g', 'c', 'm']
                iPai = -1
                tS = pai['time']
                for varNam in pai.keys():
                    iPai += 1
                    if iPai > len(color)-1:
                        iPai = 0
                    if varNam != 'time':
                        if self._isParameter(pai[varNam]):
                            plt.plot([min(tS), max(tS)], pai[varNam],
                                     color[iPai] + '-', label='New ' + varNam)
                        else:
                            plt.plot(self._getTimeGrid(tS[0], tS[-1], len(pai[varNam])),
                                     pai[varNam],
                                     color[iPai] + '-', label='New ' + varNam)

                        # Test to make sure that this variable has been found in the old results
                        if noOldResults.count(varNam) == 0:
                            if self._isParameter(yR[varNam]):
                                plt.plot([min(tR), max(tR)], yR[varNam],
                                         color[iPai] + '.', label='Old ' + varNam)
                            else:
                                plt.plot(self._getTimeGrid(tR[0], tR[-1], len(yR[varNam])),
                                         yR[varNam],
                                         color[iPai] + '.', label='Old ' + varNam)
                        # Plot the location of the maximum error
                        if varNam in timOfMaxErr:
                            plt.axvline(x=timOfMaxErr[varNam])

                leg = plt.legend(loc='best', fancybox=True)
                leg.get_frame().set_alpha(0.5) # transparent legend
                plt.xlabel('time')
                plt.grid(True)
                if iPlo == 1:
                    plt.title(matFilNam)
            plt.show()
            while not (ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                ans = raw_input("             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")
            if ans == "y" or ans == "Y":
                # update the flag
                updateReferenceData = True
        return (updateReferenceData, foundError, ans)


    def _checkReferencePoints(self, ans):
        ''' Check reference points from each regression test and compare it with the previously
            saved reference points of the same test stored in the library home folder.
            If all the reference points are not within a certain tolerance with the previous results,
            show a warning message containing the file name and path.
            If there is no ``.mat`` file of the reference points in the library home folder,
            ask the user whether it should be generated.
        '''

        #Check if the directory "self._libHome\\Resources\\ReferenceResults\\Dymola" exists, if not create it.
        refDir=os.path.join(self._libHome, 'Resources', 'ReferenceResults', 'Dymola')
        if not os.path.exists(refDir):
            os.makedirs(refDir)

        for data in self._data:
            # Name of the reference file, which is the same as that matlab file name but with another extension
            if self._includeFile(data['ScriptFile']):
                # Convert 'aa/bb.mos' to 'aa_bb.txt'
                mosFulFilNam = os.path.join(self.getLibraryName(),
                                            data['ScriptDirectory'], data['ScriptFile'])
                mosFulFilNam = mosFulFilNam.replace(os.sep, '_')
                refFilNam=os.path.splitext(mosFulFilNam)[0] + ".txt"

                try:
                    # extract reference points from the ".mat" file corresponding to "filNam"
                    warnings = []
                    errors = []
                    yS=self._getSimulationResults(data, warnings, errors)
                    for entry in warnings:
                        self._reporter.writeWarning(entry)
                    for entry in errors:
                        self._reporter.writeError(entry)
                except UnicodeDecodeError as e:
                    em = "UnicodeDecodeError({0}): {1}".format(e.errno, e.strerror)
                    em += "Output file of " + data['ScriptFile'] + " is excluded from unit tests.\n"
                    em += "The model appears to contain a non-asci character\n"
                    em += "in the comment of a variable, parameter or constant.\n"
                    em += "Check " + data['ScriptFile'] + " and the classes it instanciates.\n"
                    self._reporter.writeError(em)
                else:
                    # Reset answer, unless it is set to Y or N
                    if not (ans == "Y" or ans == "N"):
                        ans = "-"

                    updateReferenceData = False
                    # check if reference results already exists in library
                    oldRefFulFilNam=os.path.join(refDir, refFilNam)
                    # If the reference file exists, and if the reference file contains results, compare the results.
                    if os.path.exists(oldRefFulFilNam):
                        # compare the new reference data with the old one
                        [updateReferenceData, _, ans]=self._compareResults(
                            data['ResultFile'], oldRefFulFilNam, yS, refFilNam, ans)
                    else:
                        # Reference file does not exist
                        print "*** Warning: Reference file ", refFilNam, " does not yet exist."
                        while not (ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                            print "             Create new file?"
                            ans = raw_input("             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")
                        if ans == "y" or ans == "Y":
                            updateReferenceData = True
                    if updateReferenceData:    # If the reference data of any variable was updated
                        # Make dictionary to save the results and the svn information
                        self._writeReferenceResults(oldRefFulFilNam, yS)
            else:
                self._reporter.writeWarning("Output file of " + data['ScriptFile'] + " is excluded from result test.")

        return ans

    def _checkSimulationError(self, errorFile):
        ''' Check whether the simulation had any errors, and
            write the error messages to ``self._reporter``.
        '''
        import json
        
        # Read the json file with the statistics
        fil = open(self._statistics_log, "r")
        stat = json.load(fil)['testCase']

        # Error counters
        iChe = 0
        iSim = 0
        iFMU = 0
        iJac = 0
        iCon = 0
        iIni = 0
        checkedFMU = False
        # Check for errors
        for ele in stat:
            if ele['check']['result'] is False:
                iChe = iChe + 1
                self._reporter.writeError("'%s' failed model check." % ele["model"])
            if ele['simulate']['result'] is False:
                iSim = iSim + 1
                self._reporter.writeError("'%s' failed to simulate." % ele["simulate"]["command"])
            else:
                # Simulation succeeeded. Check for problems.
                if ele['simulate']["numerical Jacobians"] > 0:
                    self._reporter.writeWarning("'%s' had a numerical Jacobian." % ele["simulate"]["command"])
                    iJac = iJac + 1
                if ele['simulate']["unused connector"] > 0:
                    self._reporter.writeWarning("'%s' had unused connector variables." % ele["simulate"]["command"])
                    iCon = iCon + 1
                if ele['simulate']["unspecified initial conditions"] > 0:
                    self._reporter.writeWarning("'%s' had unspecified initial conditions." % ele["simulate"]["command"])
                    iIni = iIni + 1
            if ele.has_key('FMUExport'):
                if ele['FMUExport']['result'] is False:
                    iFMU = iFMU + 1
                    self._reporter.writeError("'%s' FMU export failed." % ele["model"])
                checkedFMU = True

        if iChe > 0:
            print "Number of models that failed check               :", iChe
        if iSim > 0:
            print "Number of models that failed to simulate         :", iSim
        if iJac > 0:
            print "Number of models with numerical Jacobian         :", iJac
        if iCon > 0:
            print "Number of models with ununsed connector variables:", iCon
        if iIni > 0:
            print "Number of models with unspecified initial conditions:", iIni
        if iFMU > 0:
            print "Number of models that failed to export as an FMU :", iFMU
        if not checkedFMU:
            print "FMU export was not tested."

        self._reporter.writeOutput("Script that runs unit tests had " + \
                                        str(self._reporter.getNumberOfWarnings()) + \
                                        " warnings and " + \
                                        str(self._reporter.getNumberOfErrors()) + \
                                        " errors.\n")
        sys.stdout.write("See 'unitTests.log' for details.\n")

        if self._reporter.getNumberOfErrors() > 0:
            return 1
        if self._reporter.getNumberOfWarnings() > 0:
            return 2
        else:
            self._reporter.writeOutput("Unit tests completed successfully.\n")
            return 0

    def printNumberOfClasses(self):
        ''' Print the number of models, blocks and functions to the
            standard output stream
        '''

        iMod=0
        iBlo=0
        iFun=0
        for root, _, files in os.walk(self._libHome):
            pos=root.find('.svn')
            # skip .svn folders
            if pos == -1:
                for filNam in files:
                    # find .mo files
                    pos=filNam.find('.mo')
                    posExa=root.find('Examples')
                    if pos > -1 and posExa == -1:
                        # find classes that are not partial
                        filFulNam=os.path.join(root, filNam)
                        iMod = self._checkKey("model", filFulNam, iMod)
                        iBlo = self._checkKey("block", filFulNam, iBlo)
                        iFun = self._checkKey("function", filFulNam, iFun)
        print "Number of models   : ", str(iMod)
        print "          blocks   : ", str(iBlo)
        print "          functions: ", str(iFun)

    def _getModelCheckCommand(self, mosFilNam):
        ''' Return lines that conduct a model check in pedantic mode.

        :param mosFilNam: The name of the ``*.mos`` file

        This function return a command of the form
        ``checkModel("Buildings.Controls.Continuous.Examples.LimPID")``
        '''

        def getModelName(mosFil, line):
            try:
                iSta = line.index('\"') + 1
                iEnd = line.index('\"', iSta)
                return line[iSta:iEnd]
            except ValueError as e:
                em = str(e) + "\n"
                em += "Did not find model name in '%s'\n" % mosFil
                self._reporter.writeError(em)
                raise ValueError(em)

        fil = open(mosFilNam, "r+")
        retVal = None
        for lin in fil.readlines():
            if "simulateModel" in lin:
                if self._modelicaCmd == 'dymola':
                    retVal = 'checkModel("{}")'.format(getModelName(mosFilNam, lin))
                elif self._modelicaCmd == 'omc':
                    retVal = "checkModel({})".format(getModelName(mosFilNam, lin))
                break;
        fil.close()
        return retVal

    def _removePlotCommands(self, mosFilNam):
        ''' Remove all plot commands from the mos file.

        :param mosFilNam: The name of the ``*.mos`` file

        This function removes all plot commands from the file ``mosFilNam``.
        This allows to work around a bug in Dymola 2012 which can cause an exception
        from the Windows operating system, or which can cause Dymola to hang on Linux.
        '''
        fil = open(mosFilNam, "r+")
        lines = fil.readlines()
        fil.close()
        linWri = []
        goToPlotEnd = False
        for i in range(len(lines)):
            if not goToPlotEnd:
                if (lines[i].count("removePlots(") == 0) and (lines[i].count("createPlot(") == 0):
                    linWri.append(i)
                elif (lines[i].count("createPlot(")) > 0:
                    goToPlotEnd = True
            else:
                if (lines[i].count(";") > 0):
                    goToPlotEnd = False
        # Write file
        filWri = open(mosFilNam, "w")
        for i in range(len(linWri)):
            filWri.write(lines[linWri[i]])
        filWri.close()

    def _writeRunscripts(self):
        """
        Create the runAll.mos scripts, one per processor (self._nPro)

        The commands in the script depend on the executable: 'dymola' or 'omc'
        """

        def _printEndOfJsonItem(isLastItem, closeElement, fileHandle, logFileName):
            if isLastItem:
                fileHandle.write("Modelica.Utilities.Streams.print(\"    }\", \"%s\")\n" % logFileName);                
                fileHandle.write("Modelica.Utilities.Streams.print(\"  }\", \"%s\")\n" % logFileName);                                
                fileHandle.write("Modelica.Utilities.Streams.print(\"]}\", \"%s\")\n" % logFileName);
            else:
                if closeElement:
                    fileHandle.write("Modelica.Utilities.Streams.print(\"    }\", \"%s\")\n" % logFileName);                
                fileHandle.write("Modelica.Utilities.Streams.print(\"  },\", \"%s\")\n" % logFileName);                



        nUniTes = 0

        nTes = len(self._data)
        for iPro in range(min(self._nPro, nTes)):

            runFil=open(os.path.join(self._temDir[iPro], self.getLibraryName(), "runAll.mos"), 'w')
            runFil.write("// File autogenerated for process "
                         + str(iPro+1) + " of " + str(self._nPro) + "\n")
            runFil.write("// File created for execution by {}. Do not edit.\n".format(self._modelicaCmd))

            if self._modelicaCmd == 'dymola':
                runFil.write('openModel("package.mo");\n')
            elif self._modelicaCmd == 'omc':
                runFil.write('loadModel(Modelica, {"3.2"});\n')
                runFil.write('getErrorString();\n')
                runFil.write('loadFile("package.mo");\n')

            # Add a flag so that translation info appears in console output.
            # This allows checking for numerical derivatives.
            # Dymola will write this output to a file when savelog(filename) is called.
            # However, the runtime log will be in dslog.txt.
            if self._modelicaCmd == 'dymola':
                runFil.write("Advanced.TranslationInCommandLog := true;\n")
                # Set flag to support string parameters, which is required for the weather data file.
                # fixme: this is for Dymola 2015 if self._include_fmu_test:
                # fixme: this is for Dymola 2015     runFil.write("Advanced.AllowStringParameters = true;\n")
                runFil.write("Modelica.Utilities.Files.remove(\"%s\");\n" % self._simulator_log_file)
                # Store the variable for pedantic mode
                runFil.write("OriginalAdvancedPedanticModelica = Advanced.PedanticModelica;\n")
            
            runFil.write("Modelica.Utilities.Files.remove(\"%s\");\n" % self._statistics_log)
            
            runFil.write(r"""
Modelica.Utilities.Streams.print("{\"testCase\" : [", "%s");
""" % self._statistics_log)
            # Count the number of experiments that need to be simulated.
            # This is needed to properly close the json brackets.
            nItem = 0
            for i in range(iPro, nTes, self._nPro):
                if self._data[i]['mustSimulate']:
                    nItem = nItem + 1
            iItem = 0
            # Write unit tests for this process
            for i in range(iPro, nTes, self._nPro):
                # Check if this mos file should be simulated
                if self._data[i]['mustSimulate']:
                    isLastItem = (iItem == nItem-1)
                    self._data[i]['ResultDirectory'] = self._temDir[iPro]
                    mosFilNam = os.path.join(self.getLibraryName(),
                                             "Resources", "Scripts", "Dymola",
                                             self._data[i]['ScriptDirectory'],
                                             self._data[i]['ScriptFile'])
                    absMosFilNam = os.path.join(self._temDir[iPro], mosFilNam)

                    values = {"mosWithPath": mosFilNam,
                              "checkCommand": self._getModelCheckCommand(absMosFilNam),                                  
                              "checkCommandString": self._getModelCheckCommand(absMosFilNam).replace('\"', r'\\\"'),
                              "scriptDir": self._data[i]['ScriptDirectory'],
                              "scriptFile": self._data[i]['ScriptFile'],
                              "modelName": self._data[i]['modelName'],
                              "modelName_underscore":  self._data[i]['modelName'].replace(".", "_"),
                              "statisticsLog": self._statistics_log,
                              "simulatorLog": self._simulator_log_file} 

                    
                    # Add checkModel(...) in pedantic mode
                    if self._modelicaCmd == 'dymola':
                        # Delete command log, modelName.simulation.log and dslog.txt
                        runFil.write("Modelica.Utilities.Files.remove(\"%s.simulator.log\");\n" % values["modelName"])
                        runFil.write("Modelica.Utilities.Files.remove(\"dslog.txt\");\n")
                        runFil.write("clearlog();\n")                        
                        runFil.write("Advanced.PedanticModelica = true;\n")
                        runFil.write("Advanced.PedanticModelica = OriginalAdvancedPedanticModelica;\n")

                    if self._modelicaCmd == 'omc':
                        runFil.write('getErrorString();\n')

                    # Write line for run script
                    if self._modelicaCmd == 'dymola':
                        # fixme: add model check
                        # Remove dslog.txt, run a simulation, rename dslog.txt, and
                        # scan this log file for errors.
                        # This is needed as RunScript returns true even if the simulation failed.
                        template = r"""
rCheck = {checkCommand};                        
rScript=RunScript("Resources/Scripts/Dymola/{scriptDir}/{scriptFile}");
savelog("{modelName}.simulator.log");
if Modelica.Utilities.Files.exist("dslog.txt") then
  Modelica.Utilities.Files.move("dslog.txt", "{modelName}.dslog.log");
end if;
"""
                        runFil.write(template.format(**values))
                        
                        if self._include_fmu_test:
                            template = r"""
rTran=translateModelFMU("{modelName}", false, "", "2", "me", false);
"""
                            runFil.write(template.format(**values))

                    #######################################################################################
                    # Write commands for checking translation and simulation results.
                    if self._modelicaCmd == 'dymola':
                        template = r"""
Modelica.Utilities.Streams.print("    {{ \"file\" :  \"{mosWithPath}\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("      \"model\" : \"{modelName}\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("      \"check\" : {{", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"command\" : \"{checkCommandString};\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"result\"  : " + String(rCheck), "{statisticsLog}");
Modelica.Utilities.Streams.print("      }},", "{statisticsLog}");
"""
                        runFil.write(template.format(**values))
                        
                        template = r"""
if Modelica.Utilities.Files.exist("{modelName}.dslog.log") then
  lines=Modelica.Utilities.Streams.readFile("{modelName}.dslog.log");
  iSuc=sum(Modelica.Utilities.Strings.count(lines, "Integration terminated successfully"));
else
  Modelica.Utilities.Streams.print("dslog.txt was not generated.", "{modelName}.log");
  iSuc=0;
end if;
if Modelica.Utilities.Files.exist("{modelName}.simulator.log") then  
  lines=Modelica.Utilities.Streams.readFile("{modelName}.simulator.log");
  iJac=sum(Modelica.Utilities.Strings.count(lines, "Number of numerical Jacobians: 0"));
  lJac=sum(Modelica.Utilities.Strings.count(lines, "Number of numerical Jacobians:"));  
  iCon=sum(Modelica.Utilities.Strings.count(lines, "Warning: The following connector variables are not used in the model"));
  iIni=sum(Modelica.Utilities.Strings.count(lines, "Dymola has selected default initial condition"));  
else
  Modelica.Utilities.Streams.print("dslog.txt was not generated.", "{modelName}.simulator.log");
  iJac=0;
  lJac=0;
  iCon=0;
  iIni=0;
end if;
Modelica.Utilities.Streams.print("      \"simulate\" : {{", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"command\" : \"RunScript(\\\"Resources/Scripts/Dymola/{scriptDir}/{scriptFile}\\\");\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"result\"  : " + String(iSuc > 0) + ",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"numerical Jacobians\"  : " + String(iJac-lJac) + ",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"unused connector\"  : " + String(iCon) + ",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"unspecified initial conditions\"  : " + String(iIni > 0), "{statisticsLog}");
"""
                        runFil.write(template.format(**values))
                        _printEndOfJsonItem(isLastItem and (not self._include_fmu_test), 
                                            not self._include_fmu_test, 
                                            runFil, 
                                            self._statistics_log);
                        
                        if self._include_fmu_test:                            
                            template = r"""
Modelica.Utilities.Streams.print("      \"FMUExport\" : {{", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"command\" : \"translateModelFMU(\\\"{modelName}\\\", false, \\\"\\\", \\\"2\\\", \\\"me\\\", false);\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"result\"  : " + String(rTran == "{modelName_underscore}"), "{statisticsLog}");
"""
                            runFil.write(template.format(**values))
                            _printEndOfJsonItem(isLastItem, 
                                                True, 
                                                runFil, 
                                                self._statistics_log);

                    elif self._modelicaCmd == 'omc':
                        template("""
runScript("Resources/Scripts/Dymola/{scriptDir}/{scriptFile}");
getErrorString();
""")
                        runFil.write(template.format(**values))
                    self._removePlotCommands(absMosFilNam)
                    nUniTes = nUniTes + 1
                    iItem = iItem + 1                    
            runFil.write("Modelica.Utilities.System.exit();\n")
            runFil.close()

        # For files that do not require a simulation, we need to set the path of the result files.
        for dat in self._data:
            if not dat['mustSimulate']:
                matFil = dat['ResultFile']
                for allDat in self._data:
                    if allDat['mustSimulate']:
                        resFil = allDat['ResultFile']
                        if resFil == matFil:
                            dat['ResultDirectory']=allDat['ResultDirectory']
                            break

        print "Generated ", nUniTes, " regression tests.\n"

    def deleteTemporaryDirectories(self, delete):
        ''' Flag, if set to ``False``, then the temporary directories will not be deleted
        after the regression tests are run.

        :param delete: Flag, set to ``False`` to avoid the temporary directories to be deleted.

        Unless this method is called prior to running the regression tests with ``delete=False``,
        all temporary directories will be deleted after the regression tests.
        '''
        self._deleteTemporaryDirectories = delete

    # Create the list of temporary directories that will be used to run the unit tests
    def _setTemporaryDirectories(self):
        import tempfile
        import shutil

        self._temDir = []

        # Make temporary directory, copy library into the directory and
        # write run scripts to directory
        for iPro in range(self._nPro):
            #print "Calling parallel loop for iPro=", iPro, " self._nPro=", self._nPro
            dirNam = tempfile.mkdtemp(prefix='tmp-' + self.getLibraryName() + '-'+ str(iPro) +  "-")
            self._temDir.append(dirNam)
            # Directory that contains the library as a sub directory
            libDir = self._libHome

            shutil.copytree(libDir,
                            os.path.join(dirNam, self.getLibraryName()),
                            symlinks=True,
                            ignore=shutil.ignore_patterns('.svn', '.mat', 'request.', 'status.'))
        return


    def run(self):
        ''' Run all regression tests and checks the results.

        :return: 0 if no errros occurred during the regression tests,
                 otherwise a non-zero value.

        This method

        - creates temporary directories for each processors,
        - copies the directory ``CURRENT_DIRECTORY`` into these
          temporary directories,
        - creates run scripts that run all regression tests,
        - runs these regression tests,
        - collects the dymola log files from each process,
        - writes the combined log file ``dymola.log``
          to the current directory,
        - compares the results of the new simulations with
          reference results that are stored in ``Resources/ReferenceResults``,
        - writes the message `Regression tests completed successfully.`
          if no error occured,
        - returns 0 if no errors occurred, or non-zero otherwise.

        '''
        import buildingspy.development.validator as v

        import multiprocessing
        import shutil
        import time
        import functools
        import json
        import glob
        
        #import pdb;pdb.set_trace()

        self.checkPythonModuleAvailability()

        self.setDataDictionary()

        # Reset the number of processors to use no more processors than there are
        # examples to be run
        self.setNumberOfThreads(min(multiprocessing.cpu_count(), len(self._data), self._nPro))

        retVal = 0
        # Start timer
        startTime = time.time()
        # Process command line arguments

        # Check if executable is on the path
        if not self._useExistingResults:
            if not self.isExecutable(self._modelicaCmd):
                print "Error: Did not find executable '", self._modelicaCmd, "'."
                return 3

        # Check current working directory
        if not self.isValidLibrary(self._libHome):
            print "*** %s is not a valid Modelica library." % self._libHome
            print "*** The current directory is ", os.getcwd()
            print "*** Expected directory ", os.path.abspath(os.path.join(self._libHome, "Resources", "Scripts"))
            print "*** Exit with error. Did not do anything."
            return 2

        print "Using ", self._nPro, " of ", multiprocessing.cpu_count(), " processors to run unit tests."
        # Count number of classes
        self.printNumberOfClasses()

        # Validate html
        if self._checkHtml:
            val = v.Validator()
            errMsg = val.validateHTMLInPackage(self._libHome)
            for i in range(len(errMsg)):
                if i == 0:
                    self._reporter.writeError("The following malformed html syntax has been found:\n%s" % errMsg[i])
                else:
                    self._reporter.writeError(errMsg[i])

        # Run simulations
        if not self._useExistingResults:
            self._setTemporaryDirectories()
        self._writeRunscripts()
        if not self._useExistingResults:
            libNam = self.getLibraryName()
            if self._modelicaCmd == 'dymola':
                cmd    = [self.getModelicaCommand(), "runAll.mos", "/nowindow"]
            elif self._modelicaCmd == 'omc':
                cmd    = [self.getModelicaCommand(), "runAll.mos"]
            if self._nPro > 1:
                po = multiprocessing.Pool(self._nPro)
                po.map(functools.partial(runSimulation,
                                         cmd=cmd),
                       map(lambda x: os.path.join(x, libNam), self._temDir))
            else:
                runSimulation(os.path.join(self._temDir[0], libNam), cmd)

            # Concatenate simulator output files into one file
            logFil = open(self._simulator_log_file, 'w')
            for d in self._temDir:
                for temLogFilNam in glob.glob( os.path.join(d, self.getLibraryName(), '*.simulator.log') ):
                    if os.path.exists(temLogFilNam):
                        fil=open(temLogFilNam,'r')
                        data=fil.read()
                        fil.close()
                        logFil.write(data)
                    else:
                        self._reporter.writeError("Log file '" + temLogFilNam + "' does not exist.\n")
                        retVal = 1
            logFil.close()

            # Concatenate simulator statistics into one file
            logFil = open(self._statistics_log, 'w')
            stat = list()
            for d in self._temDir:
                temLogFilNam = os.path.join(d, self.getLibraryName(), self._statistics_log)
                if os.path.exists(temLogFilNam):
                    temSta=open(temLogFilNam, 'r')
                    try:
                        cas = json.load(temSta)["testCase"]
                        # Iterate over all test cases of this output file
                        for ele in cas:
                            stat.append(ele)
                    except ValueError as e:
                        self._reporter.writeError("Decoding '%s' failed: %s" % (temLogFilNam, e.message))
                        raise
                    temSta.close()
                else:
                    self._reporter.writeError("Log file '" + temLogFilNam + "' does not exist.\n")
                    retVal = 1
            # Dump an array of testCase objects
            json.dump({"testCase": stat}, logFil, indent=4, separators=(',', ': '))
            logFil.close()
           
            
        # check logfile if omc
        if self._modelicaCmd == 'omc':
            self._analyseOMStats(filename = self._simulator_log_file, nModels=len(self._data))

        # Check reference results
        if self._batch:
            ans = "N"
        else:
            ans = "-"

        if self._modelicaCmd == 'dymola':
            ans = self._checkReferencePoints(ans)

        # Delete temporary directories
        if self._deleteTemporaryDirectories:
            for d in self._temDir:
                shutil.rmtree(d)

        # Check for errors
        if self._modelicaCmd == 'dymola':
            if retVal == 0:
                retVal = self._checkSimulationError(self._simulator_log_file)
            else:
                self._checkSimulationError(self._simulator_log_file)

        # Print list of files that may be excluded from unit tests
        if len(self._excludeMos) > 0:
            print "*** Warning: The following files may be excluded from the regression tests:\n"
            for fil in self._excludeMos:
                print "            ", fil

        # Print time
        elapsedTime = time.time()-startTime
        print "Execution time = %.3f s" % elapsedTime

        # Delete statistics file
        os.remove(self._statistics_log)
                
        return retVal

    def _get_test_models(self, folder=None, packages=None):
        """
        Return a list with the full path of test models that were found in ``packages``.

        :param folder: The path to the library to be searched.
        :param packages: The names of packages containing test models, such as ``Examples`` and ``Tests``
        :return: A list with the full paths to the ``.mo`` files of the found models.
        """
        if folder is None:
            folder = self._temDir[0]

        res = []
        for root, __, paths in os.walk(folder):
            # check if this root has to be analysed
            if packages is None:
                checkroot = True
            elif os.path.split(root)[-1] in packages:
                checkroot = True
            else:
                checkroot = False
            if checkroot:
                # take the path if it's a model
                for path in paths:
                    if path.endswith('.mo') and not path.endswith('package.mo'):
                        res.append(os.path.join(root, path))
        return res

    def _model_from_mo(self, mo_file):
        """Return the model name from a .mo file"""
        # split the path of the mo_file
        splt = mo_file.split(os.sep)
        # find the root of the library name
        root = splt.index(self.getLibraryName())
        # recompose but with '.' instead of path separators
        model = '.'.join(splt[root:])
        # remove the '.mo' at the end
        return model[:-3]


    def test_JModelica(self, cmpl=True, load=False, simulate=False,
                       packages=['Examples'], number=-1):
        """
        Test the library compliance with JModelica.org.

        This is the high-level method to test a complete library, even if there
        are no specific ``.mos`` files in the library for regression testing.

        This method sets self._nPro to 1 as it only works on a single core.
        It also executes self.setTemporaryDirectories()

        :param cpml: Set to ``True`` for the model to be compiled.
        :param load: Set to ``True`` to load the model from the FMU.
        :param simulate: Set to ``True`` to cause the model to be simulated.
        :param packages: Set to an array whose elements are the packages
                         that contain the test models of the library.
        :param number: Number of models to test. Set to ``-1`` to test
                       all models.

        Usage:

          1. Open a JModelica environment
             (ipython or pylab with JModelica environment variables set).
          2. cd to the root folder of the library
          3. type the following commands:

             >>> t = Tester() # doctest: +SKIP
             >>> t.testJmodelica(...) # doctest: +SKIP

        """

        from pymodelica import compile_fmu
        from pyfmi import load_fmu
        import shutil
        import sys

        from cStringIO import StringIO

        if number < 0:
            number = 1e15
        old_stdout = sys.stdout

        self.setNumberOfThreads(1)
        self._setTemporaryDirectories()

        tempdir = self._temDir[0]

        # return a list with pathnames of the .mo files to be tested
        tests = self._get_test_models(packages=['Examples'])
        compiler_options = {'extra_lib_dirs': [tempdir]}

        # statistics
        stats = {}
        for mo_file in tests:
            if len(stats) >= number:
                break
            # we keep all results for this model in a dictionary
            stats[mo_file] = {}
            model = self._model_from_mo(mo_file)
            if cmpl:
                sys.stdout = mystdout = StringIO()
                try:
                    fmu = compile_fmu(model,
                                      mo_file,
                                      compiler_options=compiler_options,
                                      compile_to=tempdir)
                except Exception as e:
                    stats[mo_file]['compilation_ok'] = False
                    stats[mo_file]['compilation_log'] = mystdout.getvalue()
                    stats[mo_file]['compilation_err'] = str(e)
                else:
                    stats[mo_file]['compilation_ok'] = True
                    stats[mo_file]['compilation_log'] = mystdout.getvalue()

                sys.stdout = old_stdout
                mystdout.close()
            else:
                # cmpl = False
                stats[mo_file]['compilation_ok'] = False
                stats[mo_file]['compilation_log'] = 'Not attempted'

            if load and stats[mo_file]['compilation_ok']:
                sys.stdout = mystdout = StringIO()
                try:
                    loaded_fmu = load_fmu(fmu)
                except Exception as e:
                    stats[mo_file]['load_ok'] = False
                    stats[mo_file]['load_log'] = mystdout.getvalue()
                    stats[mo_file]['load_err'] = str(e)
                else:
                    stats[mo_file]['load_ok'] = True
                    stats[mo_file]['load_log'] = mystdout.getvalue()
                    if simulate:
                        try:
                            loaded_fmu.simulate()
                        except Exception as e:
                            stats[mo_file]['sim_ok'] = False
                            stats[mo_file]['sim_log'] = mystdout.getvalue()
                            stats[mo_file]['sim_err'] = str(e)
                        else:
                            stats[mo_file]['sim_ok'] = True
                            stats[mo_file]['sim_log'] = mystdout.getvalue()
                            
                    else:
                        stats[mo_file]['sim_ok'] = False
                        stats[mo_file]['sim_log'] = 'Not attempted'
                
                sys.stdout = old_stdout
                mystdout.close()
            else:
                # no loading attempted
                stats[mo_file]['load_ok'] = False
                stats[mo_file]['load_log'] = 'Not attempted'
                stats[mo_file]['sim_ok'] = False
                stats[mo_file]['sim_log'] = 'Not attempted'

        # Delete temporary directories
        if self._deleteTemporaryDirectories:
            for d in self._temDir:
                shutil.rmtree(d)

        self._jmstats = stats
        self._analyseJMStats(load=load, simulate=simulate)

    def _analyseJMStats(self, load=False, simulate=False):
        """
        Analyse the statistics dictionary resulting from
        a _test_Jmodelica() call.
        
        :param load: Set to ``True`` to load the model from the FMU.
        :param simulate: Set to ``True`` to cause the model to be simulated.
        """

        count_cmpl = lambda x: [True for _, v in x.items()
                                if v['compilation_ok']]
        list_failed_cmpl = lambda x: [k for k, v in x.items()
                                      if not v['compilation_ok']]
        count_load = lambda x: [True for _, v in x.items() if v['load_ok']]
        list_failed_load = lambda x: [k for k, v in x.items()
                                      if not v['load_ok']]

        count_sim = lambda x: [True for _, v in x.items() if v['sim_ok']]
        list_failed_sim = lambda x: [k for k, v in x.items()
                                      if not v['sim_ok']]

        nbr_tot = len(self._jmstats)
        nbr_cmpl = len(count_cmpl(self._jmstats))
        nbr_load = len(count_load(self._jmstats))
        nbr_sim = len(count_sim(self._jmstats))

        print '\n'
        print 70*'#'
        print "Tested {} models:\n  * {} compiled \
successfully (={:.1%})"\
              .format(nbr_tot,
                      nbr_cmpl, float(nbr_cmpl)/float(nbr_tot))
        if load:
            print "  * {} loaded successfully (={:.1%})".format(nbr_load, float(nbr_load)/float(nbr_tot))
        
        if simulate: 
            print "  * {} simulated successfully (={:.1%})".format(nbr_sim, float(nbr_sim)/float(nbr_tot))
            
        print "\nFailed compilation for the following models:"
        for p in list_failed_cmpl(self._jmstats):
            print "  * {}".format(p.split(os.sep)[-1].split('.mo')[0])

        if load:            
            print "\nFailed loading for the following models:"
            for p in list_failed_load(self._jmstats):
                print "  * {}".format(p.split(os.sep)[-1].split('.mo')[0])
                
        if simulate:            
            print "\nFailed simulation for the following models:"
            for p in list_failed_sim(self._jmstats):
                print "  * {}".format(p.split(os.sep)[-1].split('.mo')[0])

        print "\nMore detailed information is stored in self._jmstats"        
        print 70*'#'

    def _writeOMRunScript(self, worDir, models, cmpl, simulate):
        """
        Write an OpenModelica run script to test model compliance

        :param: wordir: path to working directory
        :param: models is a list of model names, typically obtained from
        :func:`~buildingspy.regressiontest.Tester._get_test_models`
        :param: cmpl, simulate: booleans specifying if the models have to be
        compiled and simulated respectively.

        """

        mosfilename = os.path.join(worDir, 'OMTests.mos')

        with open(mosfilename, 'w') as mosfile:
            # preamble
            mosfile.write('//Automatically generated script for testing model compliance with OpenModelica.\n')
            mosfile.write('loadModel(Modelica, {"3.2"});\n')
            mosfile.write('getErrorString();\n')
            mosfile.write('loadModel('+self.getLibraryName()+');\n\n')

            # one line per model
            comp = ['checkModel(' + m + '); getErrorString();\n' for m in models]
            sim = ['simulate(' + m + '); getErrorString();\n' for m in models]

            for c,s in zip(comp, sim):
                if cmpl:
                    mosfile.write(c)
                if simulate:
                    mosfile.write(s)

        self._reporter.writeOutput('OpenModelica script {} created'.format(mosfilename))
        return mosfilename

    def test_OpenModelica(self, cmpl=True, simulate=False,
                      packages=['Examples'], number=-1):
        """
        Test the library compliance with OpenModelica.

        This is the high-level method to test a complete library, even if there
        are no specific ``.mos`` files in the library for regression testing.

        This method sets self._nPro to 1 as it only works on a single core. It also
        executes self.setTemporaryDirectories()

        :param cpml: Set to ``True`` for the model to be compiled.
        :param simulate: Set to ``True`` to cause the model to be simulated (from 0 to 1s).
        :param packages: Set to a list whose elements are the packages that contain the test models of the
          library
        :param number: Number of models to test. Set to ``-1`` to test all models.

        Usage:

          1. In a python console or script, cd to the root folder of the library

             >>> t = Tester()
             >>> t.test_OpenModelica() # doctest: +ELLIPSIS, +REPORT_NDIFF
             OpenModelica script ...OMTests.mos created
             Logfile created: ...OMTests.log
             Starting analysis of logfile
             <BLANKLINE>
             <BLANKLINE>
             ######################################################################
             Tested 2 models:
               * 0 compiled successfully (=0.0%)
             <BLANKLINE>
             Successfully checked models:
             Failed model checks:
               * BuildingsPy.buildingspy.tests.MyModelicaLibrary.Examples.Constants
               * BuildingsPy.buildingspy.tests.MyModelicaLibrary.Examples.MyStep
             <BLANKLINE>
             More detailed information is stored in self._omstats
             ######################################################################


        """
        import shutil
        import subprocess
        # fixme: Why is there a number as an argument?
        # Isn't it sufficient to select the package to be tested?
        if number < 0:
            number = int(1e15)


        self.setNumberOfThreads(1)
        self._setTemporaryDirectories()

        worDir = self._temDir[0]

        # return a list with pathnames of the .mo files to be tested

        tests = self._get_test_models(packages=packages)
        if len(tests) == 0:
                raise RuntimeError("Did not find any examples to test.")
        self._ommodels = sorted([self._model_from_mo(mo_file) for mo_file in tests[:number]])

        mosfile = self._writeOMRunScript(worDir=worDir, models=self._ommodels,
                                         cmpl=cmpl, simulate=simulate)
        
        env = os.environ.copy() # will be passed to the subprocess.Popen call
        
        # Check whether OPENMODELICALIBRARY is set.
        # If it is not set, try to use /usr/lib/omlibrary if it exists.
        # if it does not exist, stop with an error.
        if env.has_key('OPENMODELICALIBRARY'):
            # append worDir
            env['OPENMODELICALIBRARY'] += os.pathsep + worDir
        else:
            if os.path.exists('/usr/lib/omlibrary'):
                env['OPENMODELICALIBRARY'] = worDir + ':/usr/lib/omlibrary'
            else:
                raise OSError(\
                    "Environment flag 'OPENMODELICALIBRARY' must be set, or '/usr/lib/omlibrary' must be present.")

        # get the executable for omc, depending on platform
        if sys.platform == 'win32':
            try:
                omc = os.path.join(env['OPENMODELICAHOME'], 'bin', 'omc') 
            except KeyError:
                raise OSError("Environment flag 'OPENMODELICAHOME' must be set")
        else:
            # we suppose the omc executable is known
            omc = 'omc'


        try:
            logFilNam=mosfile.replace('.mos', '.log')
            with open(logFilNam, 'w') as logFil:
                retcode = subprocess.Popen(args=[omc, '+d=initialization', mosfile],
                                           stdout=logFil,
                                           stderr=logFil,
                                           shell=False,
                                           env=env,
                                           cwd=worDir).wait()

            if retcode != 0:
                print "Child was terminated by signal", retcode
                return retcode

        except OSError as e:
            sys.stderr.write("Execution of omc +d=initialization " + mosfile + " failed.\n" +
                             "Working directory is '" + worDir + "'.")
            raise(e)
        else:
            # process the log file
            print "Logfile created: {}".format(logFilNam)
            print "Starting analysis of logfile"
            f = open(logFilNam, 'r')
            self._omstats = f.readlines()
            f.close()            
            self._analyseOMStats(lines=self._omstats, models=self._ommodels, simulate=simulate)

            # Delete temporary directories
            if self._deleteTemporaryDirectories:
                for d in self._temDir:
                    shutil.rmtree(d)

    def _analyseOMStats(self, lines=None, models=None, simulate=False):
        """
        Analyse the log file of the OM compatibility test.

        :param lines: lines of the log file. 
        :param nModels: number of models that were tested.
        :param simulate: True if simulation was tested
        
        A list of models is passed to this function because it is easier to 
        get an overview of the FAILED models based on a list of all tested
        models.  
        """
        
        if lines is None:
            lines = self._omstats
        if models is None:
            models = self._ommodels
        
        check_ok, sim_ok = 0, 0
        check_nok, sim_nok = 0, 0
        models_check_ok, models_check_nok, models_sim_ok, models_sim_nok = [],[],[],[]

        for line in lines:
            if line.find('resultFile = "') > 0:
                if line.find('""') > 0:
                    sim_nok += 1
                else:
                    sim_ok += 1
                    # Seems like OpenModelica always uses '/' as file separator
                    models_sim_ok.append(line.split('/')[-1].split('_res.mat')[0])
            elif line.find('Check of ') > 0 :
                if line.find(' completed successfully.') > 0:
                    check_ok += 1
                    models_check_ok.append(line.split('Check of')[-1].split('completed successfully')[0].strip())
                else:
                    # we never get in this clause
                    pass

        # get the total number of tested models 
        check_nok = len(models) - check_ok
        sim_nok = len(models) - sim_ok
            
        # get failed models
        models_check_nok = models[:]
        for m in models_check_ok:
            models_check_nok.remove(m)
        
        if simulate:
            models_sim_nok = models[:]
            for m in models_sim_ok:
                models_sim_nok.remove(m)            
        
        print '\n'
        print 70*'#'
        print "Tested {} models:\n  * {} compiled successfully (={:.1%})"\
          .format(check_ok+check_nok,
                  check_ok, float(check_ok)/float(check_ok+check_nok))
        if simulate: 
            print "  * {} simulated successfully (={:.1%})".format(sim_ok, float(sim_ok)/float(sim_ok+sim_nok))

        print "\nSuccessfully checked models:"
        for m in models_check_ok:
            print "  * {}".format(m)
        print "Failed model checks:"
        for m in models_check_nok:
            print "  * {}".format(m)
        
        if simulate:
            print "\nSuccessfully simulated models:"
            for m in models_sim_ok:
                print "  * {}".format(m)
            print "Failed model simulations:"
            for m in models_sim_nok:
                print "  * {}".format(m)
                    
        print "\nMore detailed information is stored in self._omstats"
        print 70*'#'
