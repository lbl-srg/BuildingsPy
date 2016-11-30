#!/usr/bin/env python
#######################################################
# Script that runs all regression tests.
#
#
# MWetter@lbl.gov                            2011-02-23
#######################################################
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import sys
import os
from io import open

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
    logFil = open(logFilNam, mode="w", encoding="utf-8")
    pro = subprocess.Popen(args=cmd,
                           stdout=logFil,
                           stderr=logFil,
                           shell=False,
                           cwd=worDir)
    try:
        retcode = pro.wait()

        logFil.close()
        if retcode != 0:
            print("Child was terminated by signal {}".format(retcode))
            return retcode
        else:
            return 0
    except OSError as e:
        sys.stderr.write("Execution of '" + " ".join(map(str, cmd)) + " failed.\n" +
                         "Working directory is '" + worDir + "'.")
        raise(e)
    except KeyboardInterrupt as e:
        pro.kill()
        sys.stderr.write("Users stopped simulation in %s.\n" % worDir)


class Tester:
    ''' Class that runs all regression tests using Dymola.

    Initiate with the following optional arguments:

    :param check_html: bool (default=True). Specify whether to load tidylib and
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

    For Dymola, the regression tests also store and compare the following statistics
    for the initialization problem and the time domain simulation:

     #. The number and the size of the linear system of equations,
     #. the number and the size of the nonlinear system of equations, and
     #. the number of the numerical Jacobians.

    To run the regression tests, type

       >>> import os
       >>> import buildingspy.development.regressiontest as r
       >>> rt = r.Tester()
       >>> myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
       >>> rt.setLibraryRoot(myMoLib)
       >>> rt.run() # doctest: +ELLIPSIS
       Using ... of ... processors to run unit tests.
       Number of models   : 2
                 blocks   : 0
                 functions: 0
       Generated 5 regression tests.
       <BLANKLINE>
       Script that runs unit tests had 0 warnings and 0 errors.
       <BLANKLINE>
       See 'simulator.log' for details.
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
        import buildingspy.development.error_dictionary as e

        # --------------------------
        # Class variables
        self._checkHtml = check_html
        # Set the default directory for the library.
        # We are not calling setLibraryRoot because the
        # function checks for the argument to be a valid
        # library directory. This is also checked in run(),
        # hence for the default value in this constructor,
        # we do not verify whether the directory contains
        # a valid library.
        self._libHome = os.path.abspath(".")
        self._rootPackage = os.path.join(self._libHome, 'Resources', 'Scripts', 'Dymola')

        # Set the executable
        if executable == 'dymola' or executable == 'omc':
            self._modelicaCmd = executable
        else:
            raise ValueError(
                "Value of 'executable' of constructor 'Tester' must be 'dymola' or 'omc'. Received '{}'.".format(executable))
        # File to which the console output of the simulator is written to
        self._simulator_log_file = "simulator.log"
        # File to which statistics is written to
        self._statistics_log = "statistics.json"
        self._nPro = multiprocessing.cpu_count()
        self._batch = False
        self._pedanticModelica = False

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

        # Write result dictionary that is used by OpenModelica's regression testing
#        self.writeOpenModelicaResultDictionary()

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

        # By default, include export of FMUs.
        self._include_fmu_test = True

        # Variable that contains the figure size in inches.
        # This variable is set after the first plot has been rendered.
        # If a user resizes the plot, then the next plot will be displayed with
        # the same size.
        self._figSize = None

        # Dictionary with error messages, error counter and messages written to the user
        self._error_dict = e.ErrorDictionary()

        # By default, do not show the GUI of the simulator
        self._showGUI = False

    def _initialize_error_dict(self):
        """ Initialize the error dictionary.

        """
        import buildingspy.development.error_dictionary as e
        self._error_dict = e.ErrorDictionary()

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

    def showGUI(self, show=True):
        ''' Call this function to show the GUI of the simulator.

        By default, the simulator runs without GUI
        '''
        self._showGUI = show;
        return

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

    def pedanticModelica(self, pedanticModelica):
        ''' Set the pedantic Modelica mode flag.

        :param pedanticModelica: Set to ``True`` to run the unit tests in the pedantic Modelica mode.

        By default, regression tests are run in non-pedantic Modelica mode.
        This however will be changed in the near future.

        >>> import os
        >>> import buildingspy.development.regressiontest as r
        >>> r = r.Tester()
        >>> r.pedanticModelica(True)
        >>> r.run() # doctest: +SKIP

        '''
        self._pedanticModelica = pedanticModelica


    def include_fmu_tests(self, fmu_export):
        ''' Sets a flag that, if ``False``, does not test the export of FMUs.

        :param fmu_export: Set to ``True`` to test the export of FMUs (default), or ``False``
                           to not test the FMU export.

        To run the unit tests but do not test the export of FMUs, type

        >>> import os
        >>> import buildingspy.development.regressiontest as r
        >>> r = r.Tester()
        >>> r.include_fmu_tests(False)
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

        filObj=open(fileName, mode="r", encoding="utf-8")
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
                print("*** Warning: Excluded file {} from the regression tests.".format(fileName))
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
        # Set data dictionary as it may have been generated earlier for the whole library.
        self._data = []
        self.setDataDictionary()


    def writeOpenModelicaResultDictionary(self):
        ''' Write in ``Resources/Scripts/OpenModelica/compareVars`` files whose
        name are the name of the example model, and whose content is::

            compareVars :=
              {
                "controler.y",
                "sensor.T",
                "heater.Q_flow"
              };

        These files are then used in the regression testing that is done by the
        OpenModelica development team.

        '''
        # Create the data dictionary.
        self._data = []
        self.setDataDictionary();

        # Directory where files will be stored
        desDir=os.path.join(self._libHome, "Resources", "Scripts", "OpenModelica", "compareVars")
        if not os.path.exists(desDir):
            os.makedirs(desDir)
        # Loop over all experiments and write the files.
        for experiment in self._data:
            if 'modelName' in experiment and experiment['mustSimulate']:
                if 'ResultVariables' in experiment:
                    # For OpenModelica, don't group variables into those
                    # who should be plotted together, as all are plotted in
                    # the same plot.
                    res = []
                    for pair in experiment['ResultVariables']:
                        for var in pair:
                            res.append(var)
                    # Content of the file.
                    filCon = "compareVars :=\n  {\n    \"%s\"\n  };\n" % ("\",\n    \"".join(res))
                    # File name.
                    filNam = os.path.join(desDir, experiment['modelName'] + ".mos")
                    # Write the file
                    with open(filNam, mode="w", encoding="utf-8") as fil:
                        fil.write(filCon)

    @staticmethod
    def get_plot_variables(line):
        ''' For a string of the form `*y={aa,bb,cc}*`, optionally with whitespace characters,
        return the list `[aa, bb, cc]`.
        If the string does not contain `y = ...`, return `None`.

        A usage may be as follows. Note that the second call returns `None` as
        it has a different format.

          >>> import buildingspy.development.regressiontest as r
          >>> r.Tester.get_plot_variables('y = {"a", "b", "c"}')
          [u'a', u'b', u'c']
          >>> r.Tester.get_plot_variables('... x}, y = {"a", "b", "c"}, z = {...')
          [u'a', u'b', u'c']
          >>> r.Tester.get_plot_variables("y=abc") is None
          True

        '''
        import re
        import shlex

        # This evaluates for example
        #   re.search("y.*=.*{.*}", "aay = {aa, bb, cc}aa").group()
        #   'y = {aa, bb, cc}'
        var=re.search("y\s*=\s*{.*}", line)
        if var is None:
            return None
        s = var.group()
        s=re.search('{.*?}', s).group()
        s=s.strip('{}')
        # Use the lexer module as simply splitting by "," won't work because arrays have
        # commas in the form "a[1, 1]", "a[1, 2]"
        lexer = shlex.shlex(s)
        lexer.quotes = '"'
        lexer.whitespace = ", \t" # Skip commas, otherwise they are also returned as a token
        y = list(lexer)

        for i in range(len(y)):
            # Remove quotes as we deal with a string already
            y[i] = y[i].replace('"', '')
            # Strip whitespace characters
            y[i] = y[i].strip()
            # Replace a[1,1] by a[1, 1], which is required for the
            # Reader to be able to read the result.
            # Also, replace multiple white spaces with a single white space as
            # reading .mat is picky. For example, it refused to read a[1,1] or a[1,  1]
            y[i] = re.sub(',\W*', ', ', y[i])
        return y


    def setDataDictionary(self):
        ''' Build the data structures that are needed to parse the output files.

        '''
        import re

        def _get_attribute_value(line, keyword, dat):
            ''' Get the value of an attribute in the `.mos` file.

                This function will remove leading and ending quotes.

                :param line: The line that contains the keyword and the value.
                :param keyword: The keyword
                :param dat: The data dictionary to which dat[keyword] = value will be written.

            '''

            pos = lin.find(keyword)
            if pos > -1:
                posEq = line.find('=', pos)
                posComma = line.find(',', pos)
                posBracket = line.find(')', pos)
                posEnd = min(posComma,posBracket)
                if posEnd < 0:
                    posEnd = max(posComma,posBracket)
                entry = line[posEq+1:posEnd]
                dat[keyword] = re.sub(r'^"|"$', '', entry)
            return

        # Check if the data dictionary has already been set, in
        # which case we return doing nothing.
        # This is needed because methods append to the dictionary, which
        # can lead to double entries.
        if len(self._data) > 0:
            return

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
                        dat['mustSimulate']  = False
                        dat['mustExportFMU'] = False

                        # open the mos file and read its content.
                        # Path and name of mos file without 'Resources/Scripts/Dymola'
                        fMOS=open(os.path.join(root, mosFil), mode="r", encoding="utf-8")
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
                                        dat['TranslationLogFile'] = modNam + ".translation.log"
                                # parse startTime and stopTime, if any
                                if dat['mustSimulate']:
                                    for attr in ["startTime", "stopTime"]:
                                        _get_attribute_value(lin, attr, dat)

                                # Check if this model need to be translated as an FMU.
                                pos = lin.find("translateModelFMU")
                                if pos > -1:
                                    dat['mustExportFMU'] = True
                                if dat['mustExportFMU']:
                                    for attr in ["modelToOpen", "modelName"]:
                                        _get_attribute_value(lin, attr, dat)
                                    # The .mos script allows modelName="", in which case
                                    # we set the model name to be the entry of modelToOpen
                                    if dat.has_key("modelName") and dat["modelName"] == "" or (dat.has_key("modelName")):
                                        if dat.has_key("modelToOpen"):
                                            dat["modelName"] = dat["modelToOpen"]


                            # We are finished iterating over all lines of the .mos
                            # For FMU export, if modelName="", then Dymola uses the
                            # Modelica class name, with "." replaced by "_".
                            # If the Modelica class name consists of "_", then they
                            # are replaced by "_0".
                            # Hence, we update dat['modelName'] if needed.
                            if dat['mustExportFMU']:
                                # Strip quotes from modelName and modelToOpen
                                dat['FMUName'] = dat['modelName'].strip('"')
                                dat['modelToOpen'] = dat['modelToOpen'].strip('"')

                                # Update the name of the FMU if modelName is "" in .mos file.
                                if len(dat["FMUName"]) == 0:
                                    dat['FMUName'] = dat['modelToOpen']
                                # Update the FMU name, for example to change
                                # Buildings.Fluid.FMI.Examples.FMUs.IdealSource_m_flow to
                                # Buildings_Fluid_FMI_Examples_FMUs_IdealSource_0m_0flow
                                dat['FMUName'] = dat['FMUName'].replace("_", "_0").replace(".", "_")
                                dat['FMUName'] = dat['FMUName'] + ".fmu"

                            # Plot variables are only used for those models that need to be simulated.
                            if dat['mustSimulate']:
                                plotVars = []
                                iLin=0
                                for lin in Lines:
                                    iLin=iLin+1
                                    try:
                                        y = self.get_plot_variables(lin)
                                        if y is not None:
                                            plotVars.append(y)
                                    except AttributeError:
                                        s =  "%s, line %s, could not be parsed.\n" % (mosFil, iLin)
                                        s +=  "The problem occurred at the line below:\n"
                                        s +=  "%s\n" % lin
                                        s += "Make sure that each assignment of the plot command is on one line.\n"
                                        s += "Regression tests failed with error.\n"
                                        self._reporter.writeError(s)
                                        raise

                                if len(plotVars) == 0:
                                    s =  "%s does not contain any plot command.\n" % mosFil
                                    s += "You need to add a plot command to include its\n"
                                    s += "results in the regression tests.\n"
                                    self._reporter.writeError(s)

                                dat['ResultVariables'] = plotVars

                                # search for the result file
                                for lin in Lines:
                                    if 'resultFile=\"' in lin:
                                        matFil = re.search('(?<=resultFile=\")[a-zA-Z0-9_\.]+', lin).group()
                                        # Add the .mat extension as this is not included in the resultFile entry.
                                        matFil =  matFil + '.mat'
                                        break
                                # Some *.mos file only contain plot commands, but no simulation.
                                # Hence, if 'resultFile=' could not be found, try to get the file that
                                # is used for plotting.
                                if len(matFil) == 0:
                                    for lin in Lines:
                                        if 'filename=\"' in lin:
                                            # Note that the filename entry already has the .mat extension.
                                            matFil = re.search('(?<=filename=\")[a-zA-Z0-9_\.]+', lin).group()
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
        ''' Check if the data used to run the regression tests do not have duplicate ``*.fmu`` files
            and ``*.mat`` names.

            Since Dymola writes all ``*.fmu`` and ``*.mat`` files to the current working directory,
            duplicate file names would cause a translation or simulation to overwrite the files
            of a previous test. This would make it impossible to check the FMU export
            and to compare the results to previously obtained results.

            If there are duplicate ``.fmu`` and ``*.mat`` file names used, then this method raises
            a ``ValueError`` exception.

        '''
        s_fmu = set()
        s_mat = set()
        errMes = ""
        for data in self._data:
            if data.has_key('ResultFile'):
                resFil = data['ResultFile']
                if data['mustSimulate']:
                    if resFil in s_mat:
                        errMes += "*** Error: Result file %s_mat is generated by more than one script.\n" \
                            "           You need to make sure that all scripts use unique result file names.\n" % resFil
                    else:
                        s_mat.add(resFil)
        for data in self._data:
            if data.has_key('FMUName'):
                fmuFil = data['FMUName']
                if fmuFil in s_fmu:
                    errMes += "*** Error: FMU file {} is generated by more than one script.\n" \
                        "           You need to make sure that all scripts use unique result file names.\n".format(fmuFil)
                else:
                    s_fmu.add(fmuFil)
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
        Get the simulation results for a single unit test.

        :param data: The class that contains the data structure for the simulation results.
        :param warning: A list to which all warnings will be appended.
        :param errors: A list to which all errors will be appended.

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
                        try:
                            dat[var]=Plotter.interpolate(ti, time, val)
                        except ValueError as e:
                            msg = "Failed to process %s generated by %s.\n%s\n" (fulFilNam, data['ScriptFile'], e.strerror)
                            errors.append(msg)
                            return ret

            if len(dat) > 0:
                ret.append(dat)
        return ret

    def _getTranslationStatistics(self, data, warnings, errors):
        '''
        Get the translation statistics for a single unit test.

        :param data: The class that contains the data structure for the simulation results.
        :param warning: A list to which all warnings will be appended.
        :param errors: A list to which all errors will be appended.
        :return: The translation log from the `*.translation.log` file as
        a list of dictionaries.

        Extracts and returns the translation log from the `*.translation.log` file as
        a list of dictionaries.
        In case of an error, this method returns `None`.
        '''
        import buildingspy.io.outputfile as of

        # Get the working directory that contains the ".log" file
        fulFilNam=os.path.join(data['ResultDirectory'], self.getLibraryName(), data['TranslationLogFile'])
        return of.get_model_statistics(fulFilNam, "dymola")


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

        def getTimeGrid(t, nPoi = self._nPoi):
            if len(t) == 2:
                return self._getTimeGrid(t[0], t[-1], nPoi)
            elif len(t) == nPoi:
                return t
            else:
                s = "The new time grid has %d points, but it must have 2 or %d points.\n\
            Stop processing %s\n" % (len(tNew), nPoi, filNam)
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
            tGriOld = getTimeGrid(tOld, len(yNew))
            tGriNew = getTimeGrid(tNew, min(len(yNew), self._nPoi))
            try:
                yInt = Plotter.interpolate(tGriOld, tGriNew, yNew)
            except (IndexError, ValueError):
                em = """Data series have different length:
File=%s,
variable=%s,
len(tGriOld) = %d,
len(tGriNew) = %d,
len(yNew)    = %d.""" % (filNam, varNam, len(tGriOld), len(tGriNew), len(yNew))
                self._reporter.writeError(em)
                raise ValueError(em)
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

    def format_float(self, value):
        retVal = "%.20f" % value
        # Cut trailing zeros to avoid output such as 1.0000000
        i = len(retVal)-1;
        for pos in xrange(i, 0, -1):
            if retVal[pos] != '0':
                i = pos+1
                break
        return retVal[:i]


    def _writeReferenceResults(self, refFilNam, y_sim, y_tra):
        ''' Write the reference results.

        :param refFilNam: The name of the reference file.
        :param y_sim: The data points to be written to the file.
        :param y_tra: The dictionary with the translation log.

        This method writes the results in the form ``key=value``, with one line per entry.
        '''
        from datetime import date
        import json

        f=open(refFilNam, mode="w", encoding="utf-8")
        f.write('last-generated=' + str(date.today()) + '\n')
        for stage in ['initialization', 'simulation', 'fmu-dependencies']:
            if y_tra.has_key(stage):
#                f.write('statistics-%s=\n%s\n' % (stage, _pretty_print(y_tra[stage])))
                f.write('statistics-%s=\n%s\n' % (stage, json.dumps(y_tra[stage], indent=2)))
        # FMU exports do not have simulation results.
        # Hence, we preclude them if y_sim == None
        if y_sim is not None:
            # Set, used to avoid that data series that are plotted in two plots are
            # written twice to the reference data file.
            s = set()
            for pai in y_sim:
                for k, v in pai.items():
                    if k not in s:
                        s.add(k)
                        f.write(k + '=')
                        # Use many digits, otherwise truncation errors occur that can be higher
                        # than the required accuracy.
                        formatted = [self.format_float(e) for e in v]
                        f.write(str(formatted).replace("'", ""))
                        f.write('\n')
        f.close()

    def _readReferenceResults(self, refFilNam):
        ''' Read the reference results.

        :param refFilNam: The name of the reference file.
        :return: A dictionary with the reference results.

        If the simulation statistics was found in the reference results,
        then the return value also has an entry
        `statistics-simulation={'numerical Jacobians': '0', 'nonlinear': ' ', 'linear': ' '}`,
        where the value is a dictionary. Otherwise, this key is not present.

        '''
        import numpy
        import ast

        d = dict()
        f=open(refFilNam, mode="r", encoding="utf-8")
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
        iLin = iSta
        while iLin < len(lines):
            lin = lines[iLin].strip('\n')
            try:
                (key, value) = lin.split("=")
                # Check if this is a statistics-* entry.
                if key.startswith("statistics-"):
                    # Call ast.literal_eval as value is a string that needs to be
                    # converted to a dictionary.

                    # The json string was pretty printed over several lines.
                    # Add to value the next line, unless it contains "-" or it does not exist.
                    value = value.strip()
                    while (iLin < len(lines)-1 and lines[iLin+1].find('=') == -1):
                        value = value + lines[iLin+1].strip('\n').strip()
                        iLin += 1
                    d[key] = ast.literal_eval(value)
                else:
                    s = (value[value.find('[')+1: value.rfind(']')]).strip()
                    numAsStr=s.split(',')
                    val = []
                    for num in numAsStr:
                        # We need to use numpy.float64 here for the comparison to work
                        val.append(numpy.float64(num))
                    r[key] = val
            except ValueError as detail:
                s =  "%s could not be parsed.\n" % refFilNam
                self._reporter.writeError(s)
                raise TypeError(detail)
            iLin += 1
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

    def _check_statistics(self, old_res, y_tra, stage, foundError, newStatistics, mat_file_name):
        ''' Checks the simulation or translation statistics and return
            `True` if there is a new statistics, or a statistics is no longer present, or if `newStatistics == True`.
        '''
        r = newStatistics
        if old_res.has_key('statistics-%s' % stage):
            # Found old statistics.
            # Check whether the new results have also such a statistics.
            if y_tra.has_key(stage):
                # Check whether it changed.
                for key in old_res['statistics-%s' % stage]:
                    if y_tra[stage].has_key(key):
                        if not self.are_statistics_equal(old_res['statistics-%s' % stage][key], y_tra[stage][key]):
                            if foundError:
                                self._reporter.writeWarning("%s: Translation statistics for %s and results changed for %s.\n Old = %s\n New = %s"
                                                            % (mat_file_name, stage, key, old_res['statistics-%s' % stage][key], y_tra[stage][key]))
                            else:
                                self._reporter.writeWarning("%s: Translation statistics for %s changed for %s, but results are unchanged.\n Old = %s\n New = %s"
                                                            % (mat_file_name, stage, key, old_res['statistics-%s' % stage][key], y_tra[stage][key]))

                            r = True
                    else:
                        self._reporter.writeWarning("%s: Found translation statistics for %s for %s in old but not in new results.\n Old = %s"
                                                    % (mat_file_name, stage, key, old_res['statistics-%s' % stage][key]))
                        r = True
            else:
                # The new results have no such statistics.
                self._reporter.writeWarning("%s: Found translation statistics for %s in old but not in new results." % (mat_file_name, stage))
                r = True
        else:
            # The old results have no such statistics.
            if y_tra.has_key(stage):
                # The new results have such statistics, hence the statistics changed.
                self._reporter.writeWarning("%s: Found translation statistics for %s in new but not in old results." % (mat_file_name, stage))
                r = True
        return r

    def _compareResults(self, matFilNam, oldRefFulFilNam, y_sim, y_tra, refFilNam, ans):
        ''' Compares the new and the old results.

            :param matFilNam: Matlab file name.
            :param oldRefFilFilNam: File name including path of old reference files.
            :param y_sim: A list where each element is a dictionary of variable names and simulation
                           results that are to be plotted together.
            :param y_tra: A dictionary with the translation statistics.
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
        # If previously the user chose to update all refererence data, then
        # we set updateReferenceData = True
        if ans == "Y":
            updateReferenceData = True
        foundError = False
        verifiedTime = False

        #Load the old data (in dictionary format)
        old_results = self._readReferenceResults(oldRefFulFilNam)
        # Numerical results of the simulation
        y_ref=old_results['results']

        if len(y_ref) == 0:
            return self._askNoReferenceResultsFound(y_sim, refFilNam, ans)

        # The old data contains results
        t_ref=y_ref.get('time')

        # Iterate over the pairs of data that are to be plotted together
        timOfMaxErr = dict()
        noOldResults = [] # List of variables for which no old results have been found
        for pai in y_sim:
            t_sim=pai['time']
            if not verifiedTime:
                verifiedTime = True

                # Check if the first and last time stamp are equal
                tolTim = 1E-3 # Tolerance for time
                if (abs(t_ref[0] - t_sim[0]) > tolTim) or abs(t_ref[-1] - t_sim[-1]) > tolTim:
                    print("*** Warning: Different simulation time interval in {} and {}".format(refFilNam, matFilNam))
                    print("             Old reference points are for {} <= t <= {}".format(t_ref[0], t_ref[len(t_ref)-1]))
                    print("             New reference points are for {} <= t <= {}".format(t_sim[0], t_sim[len(t_sim)-1]))
                    foundError = True
                    while not (ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                        print("             Accept new results and update reference file in library?")
                        ans = raw_input("             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")
                    if ans == "y" or ans == "Y":
                        # Write results to reference file
                        updateReferenceData = True
                        return (updateReferenceData, foundError, ans)

            # The time interval is the same for the stored and the current data.
            # Check the accuracy of the simulation.
            for varNam in pai.keys(): # Iterate over the variable names that are to be plotted together
                if varNam != 'time':
                    if y_ref.has_key(varNam):
                        # Check results
                        if self._isParameter(pai[varNam]):
                            t=[min(t_sim), max(t_sim)]
                        else:
                            t=t_sim

                        (res, timMaxErr, warning) = self.areResultsEqual(t_ref, y_ref[varNam], \
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

        # Compare the simulation statistics
        # There are these cases:
        # 1. The old reference results have no statistics, in which case new results may be written.
        # 2. The old reference results have statistics, and they are the same or different.
        # Statistics of the simulation model
        newStatistics = False
        for stage in ['initialization', 'simulation']:
            # Updated newStatistics if there is a new statistic. The other
            # arguments remain unchanged.
            newStatistics = self._check_statistics(old_results, y_tra, stage, foundError, newStatistics, matFilNam)


        # If the users selected "Y" or "N" (to not accept or reject any new results) in previous tests,
        # or if the script is run in batch mode, then don't plot the results.
        # If we found an error, plot the results, and ask the user to accept or reject the new values.
        if (foundError or newStatistics) and (not self._batch) and (not ans == "N") and (not ans == "Y"):
            print("             For {},".format(refFilNam))
            print("             accept new file and update reference files? (Close plot window to continue.)")
            nPlo = len(y_sim)
            iPlo = 0
            plt.clf()
            for pai in y_sim:
                iPlo += 1

                plt.subplot(nPlo, 1, iPlo)
                # Iterate over the variable names that are to be plotted together
                color=['k', 'r', 'b', 'g', 'c', 'm']
                iPai = -1
                t_sim = pai['time']
                for varNam in pai.keys():
                    iPai += 1
                    if iPai > len(color)-1:
                        iPai = 0
                    if varNam != 'time':
                        if self._isParameter(pai[varNam]):
                            plt.plot([min(t_sim), max(t_sim)], pai[varNam],
                                     color[iPai] + '-', label='New ' + varNam)
                        else:
                            plt.plot(self._getTimeGrid(t_sim[0], t_sim[-1], len(pai[varNam])),
                                     pai[varNam],
                                     color[iPai] + '-', label='New ' + varNam)

                        # Test to make sure that this variable has been found in the old results
                        if noOldResults.count(varNam) == 0:
                            if self._isParameter(y_ref[varNam]):
                                # for parameters, don't just draw a dot, as these are hard to see as they are on the box
                                plt.plot([min(t_ref), max(t_ref)], y_ref[varNam],
                                         color[iPai] + 'x', markersize=10, label='Old ' + varNam)
                            else:
                                plt.plot(self._getTimeGrid(t_ref[0], t_ref[-1], len(y_ref[varNam])),
                                         y_ref[varNam],
                                         color[iPai] + '.', label='Old ' + varNam)
                        # Plot the location of the maximum error
                        if varNam in timOfMaxErr:
                            plt.axvline(x=timOfMaxErr[varNam])

                leg = plt.legend(loc='right', fancybox=True)
                leg.get_frame().set_alpha(0.5) # transparent legend
                plt.xlabel('time')
                plt.grid(True)
                if iPlo == 1:
                    plt.title(matFilNam)

            # Store the graphic objects.
            # The first plot is shown using the default size.
            # Afterwards, the plot is resized to have the same size as
            # the previous plot.
            gcf = plt.gcf()
            if self._figSize is not None:
                gcf.set_size_inches(self._figSize, forward=True)

            # Display the plot
            plt.show()
            # Store the size for reuse in the next plot.
            self._figSize=gcf.get_size_inches()

            while not (ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                ans = raw_input("             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")
            if ans == "y" or ans == "Y":
                # update the flag
                updateReferenceData = True
        return (updateReferenceData, foundError, ans)


    def are_statistics_equal(self, s1, s2):
        ''' Compare the simulation statistics `s1` and `s2` and
            return `True` if they are equal, or `False` otherwise.

        '''
        x = s1.strip()
        y = s2.strip()
        if x == y:
            return True
        # If they have a comma, such as from 1, 20, 1, 14, then split it,
        # sort it, and compare the entries for equality
        g = lambda s: s.replace(" ", "").split(",")
        sp1 = sorted(g(x))
        sp2 = sorted(g(y))
        # If the list have different lengths, they are not equal
        if len(sp1) != len(sp2):
            return False
        # They are of equal lengths, compare each element
        for i in range(len(sp1)):
            if sp1[i] != sp2[i]:
                return False

        return True



    def _compare_and_rewrite_fmu_dependencies(self, new_dependencies, reference_file_path, reference_file_name, ans):
        ''' Compares whether the ``.fmu`` dependencies have been changed.
            If they are the same, this function does nothing.
            If they do not exist in the reference results, it askes to generate them.
            If they differ from the reference results, it askes whether to accept the new ones.

            :param new_dependencies: A dictionary with the new dependencies.
            :param reference_file_path: Path to the file with reference results.
            :param reference_file_name: Name of the file with reference results.
            :param ans: A previously entered answer, either ``y``, ``Y``, ``n`` or ``N``.
            :return: A tuple consisting of a boolean ``updated_reference_data`` and the value of ``ans``.

        '''
        # Absolute path to the reference file
        abs_ref_fil_nam = os.path.join(reference_file_path, reference_file_name)
        # Put dependencies in data format needed to write to the reference result file
        y_tra = dict()
        y_tra['fmu-dependencies'] = new_dependencies

        # Check whether the reference results exist.
        if not os.path.exists(abs_ref_fil_nam):
            print("*** Warning: Reference file {} does not yet exist.".format(reference_file_name))
            while not (ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                print("             Create new file?")
                ans = raw_input("             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")
            if ans == "y" or ans == "Y":
                self._writeReferenceResults(abs_ref_fil_nam, None, y_tra)
                self._reporter.writeWarning("*** Warning: Wrote new reference file %s." %
                                            reference_file_name)
            else:
                self._reporter.writeWarning("*** Warning: Did not write new reference file %s." %
                                            reference_file_name)
            return [True, ans]

        # The file that may contain the reference results exist.
        old_dep = self._readReferenceResults(abs_ref_fil_nam)
        # Check whether it contains a key 'statistics-fmu-dependencies'
        if old_dep.has_key('statistics-fmu-dependencies'):
            # Compare the statistics for each section
            found_differences = False
            for typ in ['InitialUnknowns', 'Outputs', 'Derivatives']:
                if old_dep['statistics-fmu-dependencies'][typ] != new_dependencies[typ]:
                    print("*** Warning: Reference file {} has different FMU statistics for '{}'.".format(reference_file_name, typ))
                    found_differences = True
            if found_differences:
                while not (ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                    print("             Rewrite file?")
                    ans = raw_input("             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")
                if ans == "y" or ans == "Y":
                    self._writeReferenceResults(abs_ref_fil_nam, None, y_tra)
                    self._reporter.writeWarning("*** Warning: Rewrote reference file %s due to new FMU statistics." %
                                                reference_file_name)
            return [found_differences, ans]


        else:
            # The old file has no statistics. Ask to rewrite it.
            print("*** Warning: Reference file {} has no FMU statistics.".format(reference_file_name))
            while not (ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                print("             Rewrite file?")
                ans = raw_input("             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")
            if ans == "y" or ans == "Y":
                self._writeReferenceResults(abs_ref_fil_nam, None, y_tra)
                self._reporter.writeWarning("*** Warning: Rewrote reference file %s as the old one had no FMU statistics." %
                                            reference_file_name)
            return [True, ans]


    def _check_fmu_statistics(self, ans):
        ''' Check the fmu statistics from each regression test and compare it with the previously
            saved statistics stored in the library home folder.
            If the statistics differs,
            show a warning message containing the file name and path.
            If there is no statistics stored in the reference results in the library home folder,
            ask the user whether it should be generated.

            This function returns 1 if the statistics differ, or if the ``.fmu`` file
            is not found. The function returns 0 if there were no problems.
        '''
        import buildingspy.fmi as fmi

        retVal = 0
        #Check if the directory "self._libHome\\Resources\\ReferenceResults\\Dymola" exists, if not create it.
        refDir=os.path.join(self._libHome, 'Resources', 'ReferenceResults', 'Dymola')
        if not os.path.exists(refDir):
            os.makedirs(refDir)

        for data in self._data:
            # Name of the reference file, which is the same as that matlab file name but with another extension.
            # Only check data for FMU exort.
            if self._includeFile(data['ScriptFile']) and data['mustExportFMU']:
                # Convert 'aa/bb.mos' to 'aa_bb.txt'
                mosFulFilNam = os.path.join(self.getLibraryName(),
                                            data['ScriptDirectory'], data['ScriptFile'])
                mosFulFilNam = mosFulFilNam.replace(os.sep, '_')
                refFilNam=os.path.splitext(mosFulFilNam)[0] + ".txt"
                fmu_fil=os.path.join(data['ResultDirectory'], self.getLibraryName(), data['FMUName'])
                try:
                    # Get the new dependency
                    dep_new=fmi.get_dependencies(fmu_fil)
                    # Compare it with the stored results, and update the stored results if
                    # needed and requested by the user.
                    [updated_reference_data, ans] = self._compare_and_rewrite_fmu_dependencies(dep_new,
                                                         refDir,
                                                         refFilNam,
                                                         ans)
                    # Reset answer, unless it is set to Y or N
                    if not (ans == "Y" or ans == "N"):
                        ans = "-"
                    if updated_reference_data:
                        retVal = 1

                except UnicodeDecodeError as e:
                    em = "UnicodeDecodeError({0}): {1}.\n".format(e.errno, e.strerror)
                    em += "Output file of " + data['ScriptFile'] + " is excluded from unit tests.\n"
                    em += "The model appears to contain a non-asci character\n"
                    em += "in the comment of a variable, parameter or constant.\n"
                    em += "Check " + data['ScriptFile'] + " and the classes it instanciates.\n"
                    self._reporter.writeError(em)
                except IOError as e:
                    em = "IOError({0}): {1}.\n".format(e.errno, e.strerror)
                    em += "Output file of " + data['ScriptFile'] + " is excluded from unit tests because\n"
                    em += "the file " + fmu_fil + " does not exist\n."
                    self._reporter.writeError(em)
        return retVal

    def _checkReferencePoints(self, ans):
        ''' Check reference points from each regression test and compare it with the previously
            saved reference points of the same test stored in the library home folder.
            If all the reference points are not within a certain tolerance with the previous results,
            show a warning message containing the file name and path.
            If there is no ``.mat`` file of the reference points in the library home folder,
            ask the user whether it should be generated.

            This function return 1 if reading reference results or reading the translation
            statistics failed. In this case, the calling method should not attempt to do
            further processing. The function returns 0 if there were no problems. In
            case of wrong simulation results, this function also returns 0, as this is
            not considered an error in executing this function.
        '''
        #Check if the directory "self._libHome\\Resources\\ReferenceResults\\Dymola" exists, if not create it.
        refDir=os.path.join(self._libHome, 'Resources', 'ReferenceResults', 'Dymola')
        if not os.path.exists(refDir):
            os.makedirs(refDir)

        for data in self._data:
            # Name of the reference file, which is the same as that matlab file name but with another extension.
            # Only check data that need to be simulated. This excludes the FMU export from this test.
            if self._includeFile(data['ScriptFile']) and data['mustSimulate']:
                # Convert 'aa/bb.mos' to 'aa_bb.txt'
                mosFulFilNam = os.path.join(self.getLibraryName(),
                                            data['ScriptDirectory'], data['ScriptFile'])
                mosFulFilNam = mosFulFilNam.replace(os.sep, '_')
                refFilNam=os.path.splitext(mosFulFilNam)[0] + ".txt"


                try:
                    # extract reference points from the ".mat" file corresponding to "filNam"
                    warnings = []
                    errors = []
                    # Get the simulation results
                    y_sim=self._getSimulationResults(data, warnings, errors)
                    # Get the translation statistics
                    y_tra=self._getTranslationStatistics(data, warnings, errors)
                    for entry in warnings:
                        self._reporter.writeWarning(entry)
                    for entry in errors:
                        self._reporter.writeError(entry)
                        # If there were errors when getting the results or translation statistics,
                        # then return
                        return 1
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
                            data['ResultFile'], oldRefFulFilNam, y_sim, y_tra, refFilNam, ans)
                    else:
                        # Reference file does not exist
                        print("*** Warning: Reference file {} does not yet exist.".format(refFilNam))
                        while not (ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                            print("             Create new file?")
                            ans = raw_input("             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")
                        if ans == "y" or ans == "Y":
                            updateReferenceData = True
                    if updateReferenceData:    # If the reference data of any variable was updated
                        # Make dictionary to save the results and the svn information
                        self._writeReferenceResults(oldRefFulFilNam, y_sim, y_tra)
            else:
                # Tests that export FMUs do not have an output file. Hence, we do not warn about these cases.
                if not data['mustExportFMU']:
                    self._reporter.writeWarning("Output file of " + data['ScriptFile'] + " is excluded from result test.")
        return 0

    def _checkSimulationError(self, errorFile):
        ''' Check whether the simulation had any errors, and
            write the error messages to ``self._reporter``.
        '''
        import json

        # Read the json file with the statistics
        if not os.path.isfile(self._statistics_log):
            raise IOError("Statistics file {} does not exist.".format(self._statistics_log))

        fil = open(self._statistics_log, mode="r", encoding="utf-8")
        try:
            stat = json.load(fil)['testCase']
        except ValueError as e:
            raise ValueError("Failed to parse {}.\n{}".format(self._statistics_log, str(e)))


        # Error counters
        iChe = 0
        iSim = 0
        iFMU = 0
        # Check for errors
        for ele in stat:
            if ele['check']['result'] is False:
                iChe = iChe + 1
                self._reporter.writeError("Model check failed for '%s'." % ele["model"])
            if ele.has_key('simulate') and ele['simulate']['result'] is False:
                iSim = iSim + 1
                self._reporter.writeError("Simulation failed for '%s'." % ele["simulate"]["command"])
            elif ele.has_key('FMUExport') and ele['FMUExport']['result'] is False:
                iFMU = iFMU + 1
                self._reporter.writeError("FMU export failed for '%s'." % ele["FMUExport"]["command"])

            # Check for problems.
            # First, determine whether we had a simulation or an FMU export
            if ele.has_key('simulate'):
                key = 'simulate'
            else:
                key = 'FMUExport'

            for k, v in self._error_dict.get_dictionary().iteritems():
                if ele[key][k] > 0:
                    self._reporter.writeWarning(v["model_message"].format(ele[key]["command"]))
                    self._error_dict.increment_counter(k)

        if iChe > 0:
            print("Number of models that failed check                           : {}".format(iChe))
        if iSim > 0:
            print("Number of models that failed to simulate                     : {}".format(iSim))
        if iFMU > 0:
            print("Number of models that failed to export as an FMU             : {}".format(iFMU))

        # Write summary messages
        for _, v in self._error_dict.get_dictionary().iteritems():
            counter = v['counter']
            if counter > 0:
                print(v['summary_message'].format(counter))

        self._reporter.writeOutput("Script that runs unit tests had " + \
                                        str(self._reporter.getNumberOfWarnings()) + \
                                        " warnings and " + \
                                        str(self._reporter.getNumberOfErrors()) + \
                                        " errors.\n")
        sys.stdout.write("See '{}' for details.\n".format(self._simulator_log_file))

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
        print("Number of models   : {!s}".format(iMod))
        print("          blocks   : {!s}".format(iBlo))
        print("          functions: {!s}".format(iFun))

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

        fil = open(mosFilNam, mode="r+", encoding="utf-8")
        retVal = None
        for lin in fil.readlines():
            if "simulateModel" in lin or "modelToOpen" in lin:
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
        fil = open(mosFilNam, mode="r+", encoding="utf-8")
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
        filWri = open(mosFilNam, mode="w", encoding="utf-8")
        for i in range(len(linWri)):
            filWri.write(lines[linWri[i]])
        filWri.close()

    def _write_runscripts(self):
        """
        Create the runAll.mos scripts, one per processor (self._nPro)

        The commands in the script depend on the executable: 'dymola' or 'omc'
        """

        def _write_translation_checks(runFil, values):
            template = r"""
if Modelica.Utilities.Files.exist("{modelName}.translation.log") then
  lines=Modelica.Utilities.Streams.readFile("{modelName}.translation.log");
else
  Modelica.Utilities.Streams.print("{modelName}.translation.log was not generated.", "{modelName}.log");
  lines=String();
end if;

// Count the zero numerical Jacobians separately
iJac=sum(Modelica.Utilities.Strings.count(lines, "Number of numerical Jacobians: 0"));
"""
            runFil.write(template.format(**values))

            # Do the other tests
            for _, v in self._error_dict.get_dictionary().iteritems():
                template = r"""  {}=sum(Modelica.Utilities.Strings.count(lines, "{}"));
"""
                runFil.write(template.format(v["buildingspy_var"], v["tool_message"]))


        def _write_translation_stats(runFil, values):

            for k, v in self._error_dict.get_dictionary().iteritems():
                if k != "numerical Jacobians":
                    template = r"""
Modelica.Utilities.Streams.print("        \"{}\"  : " + String({}) + ",", "{}");"""
                    runFil.write(template.format(k, v["buildingspy_var"], values['statisticsLog']))

            # Write the numerical Jacobians separately as this requires subtraction of two counters.
            # As this is the last entry, there also is no terminating comma.
            template = r"""
Modelica.Utilities.Streams.print("        \"numerical Jacobians\"  : " + String(lJac-iJac), "{statisticsLog}");
"""
            runFil.write(template.format(**values))


            # Close the bracket for the JSON object
            runFil.write("""Modelica.Utilities.Streams.print("      }", """ + '"' + values['statisticsLog'] + '"' + ");\n")

        def _print_end_of_json(isLastItem, fileHandle, logFileName):
            if isLastItem:
                fileHandle.write("Modelica.Utilities.Streams.print(\"    }\", \"%s\")\n" % logFileName);
                fileHandle.write("Modelica.Utilities.Streams.print(\"  ]\", \"%s\")\n" % logFileName);
                fileHandle.write("Modelica.Utilities.Streams.print(\"}\", \"%s\")\n" % logFileName);
            else:
                fileHandle.write("Modelica.Utilities.Streams.print(\"  },\", \"%s\")\n" % logFileName);

        nUniTes = 0

        # Count how many tests need to be simulated.
        nTes = len(self._data)
        # Reduced the number of processors if there are fewer examples than processors
        if nTes < self._nPro:
            self.setNumberOfThreads(nTes)

        for iPro in range(self._nPro):

            runFil=open(os.path.join(self._temDir[iPro], self.getLibraryName(), "runAll.mos"), mode="w", encoding="utf-8")
            runFil.write("// File autogenerated for process {} of {}\n".format(iPro+1, self._nPro))
            runFil.write("// File created for execution by {}. Do not edit.\n".format(self._modelicaCmd))

            if self._modelicaCmd == 'dymola':
                # Disable parallel computing as this can give slightly different results.
                runFil.write('Advanced.ParallelizeCode = false;\n')
                # Set the pedantic Modelica mode
                if self._pedanticModelica:
                    runFil.write('Advanced.PedanticModelica = true;\n')
                else:
                    runFil.write('Advanced.PedanticModelica = false;\n')
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
                runFil.write("Modelica.Utilities.Files.remove(\"%s\");\n" % self._simulator_log_file)

            runFil.write("Modelica.Utilities.Files.remove(\"%s\");\n" % self._statistics_log)

            runFil.write(r"""
Modelica.Utilities.Streams.print("{\"testCase\" : [", "%s");
""" % self._statistics_log)
            # Count the number of experiments that need to be simulated or exported as an FMU.
            # This is needed to properly close the json brackets.
            nItem = 0
            for i in range(iPro, nTes, self._nPro):
                if self._data[i]['mustSimulate'] or (self._include_fmu_test and self._data[i]['mustExportFMU']):
                    nItem = nItem + 1
            iItem = 0
            # Write unit tests for this process
            for i in range(iPro, nTes, self._nPro):
                # Check if this mos file should be simulated
                if self._data[i]['mustSimulate'] or (self._include_fmu_test and self._data[i]['mustExportFMU']):
                    isLastItem = (iItem == nItem-1)
                    self._data[i]['ResultDirectory'] = self._temDir[iPro]
                    mosFilNam = os.path.join(self.getLibraryName(),
                                             "Resources", "Scripts", "Dymola",
                                             self._data[i]['ScriptDirectory'],
                                             self._data[i]['ScriptFile'])
                    absMosFilNam = os.path.join(self._temDir[iPro], mosFilNam)

                    values = {"mosWithPath": mosFilNam.replace("\\","/"),
                              "checkCommand": self._getModelCheckCommand(absMosFilNam).replace("\\","/"),
                              "checkCommandString": self._getModelCheckCommand(absMosFilNam).replace('\"', r'\\\"'),
                              "scriptDir": self._data[i]['ScriptDirectory'].replace("\\","/"),
                              "scriptFile": self._data[i]['ScriptFile'].replace("\\","/"),
                              "modelName": self._data[i]['modelName'].replace("\\","/"),
                              "modelName_underscore":  self._data[i]['modelName'].replace(".", "_"),
                              "statisticsLog": self._statistics_log.replace("\\","/"),
                              "simulatorLog": self._simulator_log_file.replace("\\","/")}

                    if self._data[i].has_key('FMUName'):
                        values["FMUName"] = self._data[i]['FMUName']


                    if self._modelicaCmd == 'dymola':
                        # Delete command log, modelName.simulation.log and dslog.txt
                        runFil.write("Modelica.Utilities.Files.remove(\"%s.translation.log\");\n" % values["modelName"])
                        runFil.write("Modelica.Utilities.Files.remove(\"dslog.txt\");\n")
                        runFil.write("clearlog();\n")

                    if self._modelicaCmd == 'omc':
                        runFil.write('getErrorString();\n')

                    ########################################################################
                    # Write line for model check
                    if self._modelicaCmd == 'dymola':
                        template = r"""
rCheck = {checkCommand};
Modelica.Utilities.Streams.print("    {{ \"file\" :  \"{mosWithPath}\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("      \"model\" : \"{modelName}\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("      \"check\" : {{", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"command\" : \"{checkCommandString};\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"result\"  : " + String(rCheck), "{statisticsLog}");
Modelica.Utilities.Streams.print("      }},", "{statisticsLog}");
"""
                        runFil.write(template.format(**values))

                    #######################################################################################
                    # Write commands for checking translation and simulation results.
                    if self._modelicaCmd == 'dymola' and self._data[i]["mustSimulate"]:
                        # Remove dslog.txt, run a simulation, rename dslog.txt, and
                        # scan this log file for errors.
                        # This is needed as RunScript returns true even if the simulation failed.
                        # We read to dslog file line by line as very long files can lead to
                        # Out of memory for strings
                        # It could due to too large matrices, infinite recursion, or uninitialized variables.
                        # You can increase the size of 'Stringbuffer' in dymola/source/matrixop.h.
                        # The stack of functions is:
                        # Modelica.Utilities.Streams.readFile
                        template = r"""
rScript=RunScript("Resources/Scripts/Dymola/{scriptDir}/{scriptFile}");
savelog("{modelName}.translation.log");
if Modelica.Utilities.Files.exist("dslog.txt") then
  Modelica.Utilities.Files.move("dslog.txt", "{modelName}.dslog.log");
end if;
iSuc=0;
if Modelica.Utilities.Files.exist("{modelName}.dslog.log") then
  iLin=1;
  endOfFile=false;
  while (not endOfFile) loop
    (line, endOfFile)=Modelica.Utilities.Streams.readLine("{modelName}.dslog.log", iLin);
    iLin=iLin+1;
    iSuc=iSuc+Modelica.Utilities.Strings.count(line, "Integration terminated successfully");
  end while;
  Modelica.Utilities.Streams.close("{modelName}.dslog.log");
else
  Modelica.Utilities.Streams.print("{modelName}.dslog.log was not generated.", "{modelName}.log");
end if;
"""
                        runFil.write(template.format(**values))

                        _write_translation_checks(runFil, values)

                        template = r"""
Modelica.Utilities.Streams.print("      \"simulate\" : {{", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"command\" : \"RunScript(\\\"Resources/Scripts/Dymola/{scriptDir}/{scriptFile}\\\");\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"result\"  : " + String(iSuc > 0) + ",", "{statisticsLog}");
"""
                        runFil.write(template.format(**values))

                        _write_translation_stats(runFil, values)

                        _print_end_of_json(isLastItem,
                                           runFil,
                                           self._statistics_log);

                    #############################################################################################
                    ## FMU export
                    if self._modelicaCmd == 'dymola' and self._data[i]["mustExportFMU"] and self._include_fmu_test:
                        template = r"""
Modelica.Utilities.Files.removeFile("{FMUName}");
RunScript("Resources/Scripts/Dymola/{scriptDir}/{scriptFile}");
savelog("{modelName}.translation.log");
if Modelica.Utilities.Files.exist("dslog.txt") then
  Modelica.Utilities.Files.move("dslog.txt", "{modelName}.dslog.log");
end if;
iSuc=0;
if Modelica.Utilities.Files.exist("{modelName}.dslog.log") then
  iLin=1;
  endOfFile=false;
  while (not endOfFile) loop
    (line, endOfFile)=Modelica.Utilities.Streams.readLine("{modelName}.dslog.log", iLin);
    iLin=iLin+1;
    iSuc=iSuc+Modelica.Utilities.Strings.count(line, "Created {FMUName}");
  end while;
  Modelica.Utilities.Streams.close("{modelName}.dslog.log");
else
  Modelica.Utilities.Streams.print("{modelName}.dslog.log was not generated.", "{modelName}.log");
end if;
"""
                        runFil.write(template.format(**values))

                        _write_translation_checks(runFil, values)

                        template = r"""
Modelica.Utilities.Streams.print("      \"FMUExport\" : {{", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"command\" :\"RunScript(\\\"Resources/Scripts/Dymola/{scriptDir}/{scriptFile}\\\");\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"result\"  : " + String(iSuc > 0)  + ",", "{statisticsLog}");
"""
                        runFil.write(template.format(**values))

                        _write_translation_stats(runFil, values)

                        _print_end_of_json(isLastItem,
                                           runFil,
                                           self._statistics_log);


                    elif self._modelicaCmd == 'omc':
                        template("""
runScript("Resources/Scripts/Dymola/{scriptDir}/{scriptFile}");
getErrorString();
""")
                        runFil.write(template.format(**values))


                    if self._modelicaCmd == 'dymola' and not (self._data[i]["mustExportFMU"] or self._data[i]["mustSimulate"]):
                        print("****** {} neither requires a simulation nor an FMU export.".format(self._data[i]['ScriptFile']))

                    self._removePlotCommands(absMosFilNam)
                    nUniTes = nUniTes + 1
                    iItem = iItem + 1
            runFil.write("Modelica.Utilities.System.exit();\n")
            runFil.close()

        # For files that do not require a simulation, we need to set the path of the result files.
        for dat in self._data:
            if not dat['mustSimulate'] and not dat['mustExportFMU']:
                matFil = dat['ResultFile']
                for allDat in self._data:
                    if allDat['mustSimulate']:
                        resFil = allDat['ResultFile']
                        if resFil == matFil:
                            dat['ResultDirectory']=allDat['ResultDirectory']
                            break

        print("Generated {} regression tests.\n".format(nUniTes))

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
            #print("Calling parallel loop for iPro={}, self._nPro={}".format(iPro, self._nPro))
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

        # Remove all data that do not require a simulation or an FMU export.
        # Otherwise, some processes may have no simulation to run and then
        # the json output file would have an invalid syntax
        for ele in self._data:
            if not (ele['mustSimulate'] or ele['mustExportFMU']):
                self._data.remove(ele)

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
                print("Error: Did not find executable '{}'".format(self._modelicaCmd))
                return 3

        # Check current working directory
        if not self.isValidLibrary(self._libHome):
            print("*** {} is not a valid Modelica library.".format(self._libHome))
            print("*** The current directory is {}".format(os.getcwd()))
            print("*** Expected directory {} ".format(os.path.abspath(os.path.join(self._libHome, "Resources", "Scripts"))))
            print("*** Exit with error. Did not do anything.")
            return 2

        # Initialize data structure to check results
        self._initialize_error_dict()

        # Print number of processors
        print("Using {} of {} processors to run unit tests.".format(self._nPro, multiprocessing.cpu_count()))
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
        self._write_runscripts()
        if not self._useExistingResults:
            libNam = self.getLibraryName()
            if self._modelicaCmd == 'dymola':
                if self._showGUI:
                    cmd = [self.getModelicaCommand(), "runAll.mos"]
                else:
                    cmd = [self.getModelicaCommand(), "runAll.mos", "/nowindow"]
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
            logFil = open(self._simulator_log_file, mode="w", encoding="utf-8")
            for d in self._temDir:
                for temLogFilNam in glob.glob( os.path.join(d, self.getLibraryName(), '*.translation.log') ):
                    if os.path.exists(temLogFilNam):
                        fil=open(temLogFilNam, mode="r", encoding="utf-8")
                        data=fil.read()
                        fil.close()
                        logFil.write(data)
                    else:
                        self._reporter.writeError("Log file '" + temLogFilNam + "' does not exist.\n")
                        retVal = 1
            logFil.close()

            # Concatenate simulator statistics into one file
            logFil = open(self._statistics_log, mode="w", encoding="utf-8")
            stat = list()
            for d in self._temDir:
                temLogFilNam = os.path.join(d, self.getLibraryName(), self._statistics_log)
                if os.path.exists(temLogFilNam):
                    temSta=open(temLogFilNam.replace('Temp\tmp','Temp\\tmp'), mode="r", encoding="utf-8")
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
            retVal = self._check_fmu_statistics(ans)
            if retVal != 0:
                retVal = 4


        if self._modelicaCmd == 'dymola':
            r = self._checkReferencePoints(ans)
            if r != 0:
                retVal = 4

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
            print("*** Warning: The following files may be excluded from the regression tests:\n")
            for fil in self._excludeMos:
                print("            {}".format(fil))

        # Print time
        elapsedTime = time.time()-startTime
        print("Execution time = {:.3f} s".format(elapsedTime))

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

        print('\n')
        print(70*'#')
        print("Tested {} models:\n  * {} compiled \
successfully (={:.1%})"\
              .format(nbr_tot,
                      nbr_cmpl, float(nbr_cmpl)/float(nbr_tot)))
        if load:
            print("  * {} loaded successfully (={:.1%})".format(nbr_load, float(nbr_load)/float(nbr_tot)))

        if simulate:
            print("  * {} simulated successfully (={:.1%})".format(nbr_sim, float(nbr_sim)/float(nbr_tot)))

        print("\nFailed compilation for the following models:")
        for p in list_failed_cmpl(self._jmstats):
            print("  * {}".format(p.split(os.sep)[-1].split('.mo')[0]))

        if load:
            print("\nFailed loading for the following models:")
            for p in list_failed_load(self._jmstats):
                print("  * {}".format(p.split(os.sep)[-1].split('.mo')[0]))

        if simulate:
            print("\nFailed simulation for the following models:")
            for p in list_failed_sim(self._jmstats):
                print("  * {}".format(p.split(os.sep)[-1].split('.mo')[0]))

        print("\nMore detailed information is stored in self._jmstats")
        print(70*'#')

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

        with open(mosfilename, mode="w", encoding="utf-8") as mosfile:
            # preamble
            mosfile.write("//Automatically generated script for testing model compliance with OpenModelica.\n")
            mosfile.write("loadModel(Modelica, {\"3.2\"});\n")
            mosfile.write("getErrorString();\n")
            mosfile.write("loadModel({});\n\n".format(self.getLibraryName()))

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
             Tested 4 models:
               * 0 compiled successfully (=0.0%)
             <BLANKLINE>
             Successfully checked models:
             Failed model checks:
               * BuildingsPy.buildingspy.tests.MyModelicaLibrary.Examples.BooleanParameters
               * BuildingsPy.buildingspy.tests.MyModelicaLibrary.Examples.Constants
               * BuildingsPy.buildingspy.tests.MyModelicaLibrary.Examples.MyStep
               * BuildingsPy.buildingspy.tests.MyModelicaLibrary.Examples.ParameterEvaluation
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
                print("Child was terminated by signal {}".format(retcode))
                return retcode

        except OSError as e:
            raise OSError("Execution of omc +d=initialization " + mosfile + " failed.\n" +
                             "Working directory is '" + worDir + "'.")
        else:
            # process the log file
            print("Logfile created: {}".format(logFilNam))
            print("Starting analysis of logfile")
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

        print('\n')
        print(70*'#')
        print("Tested {} models:\n  * {} compiled successfully (={:.1%})"\
          .format(check_ok+check_nok,
                  check_ok, float(check_ok)/float(check_ok+check_nok)))
        if simulate:
            print("  * {} simulated successfully (={:.1%})".format(sim_ok, float(sim_ok)/float(sim_ok+sim_nok)))

        print("\nSuccessfully checked models:")
        for m in models_check_ok:
            print("  * {}".format(m))
        print("Failed model checks:")
        for m in models_check_nok:
            print("  * {}".format(m))

        if simulate:
            print("\nSuccessfully simulated models:")
            for m in models_sim_ok:
                print("  * {}".format(m))
            print("Failed model simulations:")
            for m in models_sim_nok:
                print("  * {}".format(m))

        print("\nMore detailed information is stored in self._omstats")
        print(70*'#')
