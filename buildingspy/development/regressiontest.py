#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################
# Script that runs all regression tests.
#
#
# MWetter@lbl.gov                            2011-02-23
#######################################################
#
from collections import defaultdict
from contextlib import contextmanager
import difflib
import fnmatch
import functools
import glob
import io
import json
import multiprocessing
import numbers
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import webbrowser
# Third-party module or package imports.
import numpy as np
import simplejson
# Code repository sub-package imports.
import pyfunnel
from buildingspy.development import error_dictionary_openmodelica
from buildingspy.development import error_dictionary_optimica
from buildingspy.development import error_dictionary_dymola
from buildingspy.io.outputfile import Reader
from buildingspy.io.postprocess import Plotter
import buildingspy.io.outputfile as of
import buildingspy.io.reporter as rep


def runSimulation(worDir, cmd):
    """ Run the simulation.

    :param worDir: The working directory.
    :param cmd: An array which is passed to the `args` argument of
                :mod:`subprocess.Popen`

    .. note:: This method is outside the class definition to
              allow parallel computing.
    """
    # OPTIMICA requires the working directory to be part of MODELICAPATH
    env = os.environ.copy()  # will be passed to the subprocess.Popen call
    if 'MODELICAPATH' in os.environ:
        env['MODELICAPATH'] = "{}:{}".format(worDir, os.environ['MODELICAPATH'])
    else:
        env['MODELICAPATH'] = worDir

    logFilNam = os.path.join(worDir, 'stdout.log')
#
    with open(logFilNam, mode="w", encoding="utf-8") as logFil:
        # Here we add worDir to cmd[1], see https://github.com/lbl-srg/BuildingsPy/issues/303
        pro = subprocess.Popen(args=[cmd[0], worDir + "/" + cmd[1]] + cmd[2:],
                               stdout=logFil,
                               stderr=logFil,
                               shell=False,
                               env=env,
                               cwd=worDir)
        try:
            retcode = pro.wait()
            if retcode != 0:
                print("*** Execution of command '{}' failed".format(cmd))
                print("*** Working directory is {}".format(worDir))
                print("*** Files in directory {} are\n".format(worDir))
                for fil in os.listdir(worDir):
                    print("     {}".format(fil))
                print("*** The command returned the following output: \n")
                if os.path.isfile(logFilNam):
                    with open(logFilNam, 'r') as f:
                        print(f.read())
                else:
                    print("The file {} does not exist.\n".format(logFilNam))
                print("*** end of command output\n")

                print("Child was terminated by signal {}".format(retcode))
                return retcode
            else:
                return 0
        except OSError as e:
            sys.stderr.write("Execution of '" + " ".join(map(str, cmd)) + " failed.\n"
                             + "Working directory is '" + worDir + "'.")
            raise(e)
        except KeyboardInterrupt as e:
            pro.kill()
            sys.stderr.write("Users stopped simulation in %s.\n" % worDir)


def _print_dictionary(msg, dic, exit=False):
    import sys
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    print(f"*************** {msg} **************************")
    pp.pprint(dic)
    print(f"*****************************************")
    if exit:
        sys.exit(1)


@contextmanager
def _stdout_redirector(stream):
    """ Redirects sys.stdout to stream."""
    old_stdout = sys.stdout
    sys.stdout = stream
    try:
        yield
    finally:
        sys.stdout = old_stdout


class Tester(object):
    """ Class that runs regression tests of the Modelica library.

    Initiate with the following optional arguments:

    :param check_html: Boolean (default ``True``). Specify whether to load tidylib and
            perform validation of html documentation.
    :param tool: string {``'dymola'``, ``'openmodelica'``, ``'optimica'``}.
            Default is ``'dymola'``, specifies the
            tool to use for running the regression test with :func:`~buildingspy.development.Tester.run`.
    :param cleanup: Boolean (default ``True``). Specify whether to delete temporary directories.
    :param tol: float or dict (default=1E-3). Comparison tolerance
            If a float is provided, it is assigned to the absolute tolerance along x axis and to the
            absolute and relative tolerance along y axis.
            (If ``comp_tool='legacy'``, only the absolute tolerance in y is used.)
            If a dict is provided, keys must conform with ``pyfunnel.compareAndReport`` arguments.
    :param skip_verification: Boolean (default ``False``).
            If ``True``, unit test results are not verified against reference points.
    :param color: Boolean (default ``False``).
            If ``True``, command line output will be in color (ignored on Windows).

    This class can be used to run all regression tests.

    *Regression testing using Dymola*

    For Dymola, this module searches the directory
    ``CURRENT_DIRECTORY/Resources/Scripts/Dymola`` for
    all ``*.mos`` files that contain the string ``simulate``,
    where ``CURRENT_DIRECTORY`` is the name of the directory in which the Python
    script is started, as returned by the function :func:`getLibraryName`.
    All these files will be executed as part of the regression tests.
    Any variables or parameters that are plotted by these ``*.mos`` files
    will be compared to previous results that are stored in
    ``CURRENT_DIRECTORY/Resources/ReferenceResults/Dymola``.
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
       >>> rt = r.Tester(tool="dymola")
       >>> myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
       >>> rt.setLibraryRoot(myMoLib)
       >>> rt.run()                    # doctest: +SKIP
       MyModelicaLibrary.Examples.NoSolution: Excluded from simulation. Model excluded from simulation as it has no solution.
       Number of models   : 11
                 blocks   : 2
                 functions: 0
       Using ... of ... processors to run unit tests for dymola.
       Generated 7 regression tests.
       <BLANKLINE>
       Comparison files output by funnel are stored in the directory 'funnel_comp' of size ... MB.
       Run 'python -c "import buildingspy.development.regressiontest as t; t.Tester(tool=\\\"dymola\\\").report()"'
       to access a summary of the comparison results.
       <BLANKLINE>
       Script that runs unit tests had 0 warnings and 0 errors.
       <BLANKLINE>
       See 'simulator-dymola.log' for details.
       Unit tests completed successfully.
       <BLANKLINE>
       Execution time = ...

    To run regression tests only for a single package, call :func:`setSinglePackage`
    prior to :func:`run`.

    *Regression testing using OpenModelica or OPTIMICA*

    For OpenModelica and OPTIMICA, the selection of test cases is done the same
    way as for Dymola. However, the solver tolerance is obtained
    from the `.mo` file by reading the annotation
    `Tolerance="value"`.

    For OpenModelica and OPTIMICA, a JSON file stored as
    ``Resources/Scripts/BuildingsPy/conf.yml`` (or for backward compatibility, in `conf.json`) can be used
    to further configure tests. The file has the syntax below,
    where ``openmodelica`` or ``optimica`` specifies the tool.

    .. code-block:: javascript

       - model_name: Buildings.Fluid.Examples.FlowSystem.Simplified2
         optimica:
           ncp: 500,
           rtol: 1E-6,
           solver: "CVode",
           simulate: True,
           translate: True,
           time_out: 600
           comment: 'Add some comment and ideally a link to a github issue'


    For OpenModelica, replace ``optimica`` with ``openmodelica``.
    For the detailed specification of allowed fields, see ``buildingspy/templates/regressiontest_conf.py``.

    Any entries are optional, and the entries shown above
    are the default values, except for the relative tolerance `rtol`
    which is read from the `.mo` file. However, with `rtol`, this
    value can be overwritten.
    Note that this syntax is still experimental and may be changed.

    """

    def __init__(
        self,
        check_html=True,
        tool="dymola",
        cleanup=True,
        comp_tool='funnel',
        tol=1E-3,
        skip_verification=False,
        color=False
    ):
        import platform

        """ Constructor."""
        if tool == 'optimica':
            e = error_dictionary_optimica
        elif tool == 'openmodelica':
            e = error_dictionary_openmodelica
        else:
            e = error_dictionary_dymola
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

        # Set the tool
        if tool in ['dymola', 'openmodelica', 'optimica']:
            self._modelica_tool = tool
        else:
            raise ValueError(
                "Value of 'tool' of constructor 'Tester' must be 'dymola', 'openmodelica' or 'optimica'. Received '{}'.".format(tool))
        # File to which the console output of the simulator is written
        self._simulator_log_file = "simulator-{}.log".format(tool)
        #  File to which the console output of the simulator of failed simulations is written
        self._failed_simulator_log_file = "failed-simulator-{}.log".format(tool)
        # File to which statistics is written to
        self._statistics_log = "statistics.json"
        self._nPro = multiprocessing.cpu_count()
        self._batch = False
        self._pedanticModelica = False

        # Number of data points that are used
        self._OCT_VERIFICATION = True
        self._nPoi = 501 if self._OCT_VERIFICATION else 101

        # List of temporary directories that are used to run the simulations.
        self._temDir = []

        # Flag to delete temporary directories.
        self._deleteTemporaryDirectories = cleanup

        # Flag to use existing results instead of running a simulation.
        self._useExistingResults = False

        # Flag to compare results against reference points.
        self._skip_verification = skip_verification

        # Comparison tool.
        self._comp_tool = comp_tool

        # Absolute (a) or relative (r) tolerance in x and y.
        self._tol = {}  # Keys: 'ax', 'ay', 'lx', 'ly', 'rx', 'ry'. Values: defaulting to 0.
        if isinstance(tol, numbers.Real):
            self._tol['ax'] = tol
            self._tol['ay'] = tol
            self._tol['ly'] = tol
        elif isinstance(tol, dict):
            self._tol = tol
        else:
            raise TypeError('Parameter `tol` must be a number or a dict.')
        for k in ['ax', 'ay', 'lx', 'ly', 'rx', 'ry']:
            try:
                self._tol[k]
            except KeyError:
                self._tol[k] = 0

        # Data structures for storing comparison data.
        self._comp_info = []
        self._comp_log_file = "comparison-{}.log".format(tool)
        self._comp_dir = "funnel_comp"

        # (Delete and) Create directory for storing funnel data.
        # Done by run method to allow for runing report method without having to rerun simulations.

        # Path of templates for HTML report and plot.
        self._REPORT_TEMPLATE = os.path.join(
            os.path.dirname(__file__), os.path.pardir, 'templates', 'datatable.html')
        self._PLOT_TEMPLATE = os.path.join(
            os.path.dirname(__file__), os.path.pardir, 'templates', 'plot.html')

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
        self._reporter = rep.Reporter(os.path.join(os.getcwd(), "unitTests-{}.log".format(tool)))

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

        # Enable or disable colored output on non-windows
        if color and (platform.system() != "Windows"):
            self._color_BOLD = '\033[1m'
            self._color_OK = '\033[1;32m'
            self._color_GREY = '\033[90m'
            self._color_WARNING = '\033[93m'
            self._color_ERROR = '\033[91m'
            self._color_ENDC = '\033[0m'
        else:
            self._color_BOLD = ''
            self._color_OK = ''
            self._color_GREY = ''
            self._color_WARNING = ''
            self._color_ERROR = ''
            self._color_ENDC = ''

    def report(self, timeout=600, browser=None, autoraise=True, comp_file=None):
        """Builds and displays HTML report.

        Serves until timeout (s) or KeyboardInterrupt.
        """
        if self._comp_tool != 'funnel':
            raise ValueError('Report is only available with comp_tool="funnel".')

        report_file = 'report.html'
        plot_file = os.path.join(self._comp_dir, 'plot.html')

        with open(self._REPORT_TEMPLATE, 'r') as f:
            template = f.read()
        content = re.sub(r'\$SIMULATOR_LOG', self._comp_log_file, template)
        content = re.sub(r'\$COMP_DIR', self._comp_dir, content)
        server = pyfunnel.MyHTTPServer(
            ('',
             0),
            pyfunnel.CORSRequestHandler,
            str_html=content,
            url_html='funnel',
            browse_dir=os.getcwd())

        # Pre-build HTML plot file.
        with open(self._PLOT_TEMPLATE, 'r') as f:
            template = f.read()
        content = re.sub(r'\$SERVER_PORT', str(server.server_port), template)
        with open(plot_file, 'w') as f:
            f.write(content)

        server.browse(browser=browser, timeout=timeout)

    def get_unit_test_log_file(self):
        """ Return the name of the log file of the unit tests,
            such as ``unitTests-openmodelica.log``, ``unitTests-optimica.log`` or ``unitTests-dymola.log``.
        """
        return "unitTests-{}.log".format(self._modelica_tool)

    def _initialize_error_dict(self):
        """ Initialize the error dictionary.

        """
        if self._modelica_tool == 'openmodelica':
            import buildingspy.development.error_dictionary_openmodelica as e
        elif self._modelica_tool == 'optimica':
            import buildingspy.development.error_dictionary_optimica as e
        else:
            import buildingspy.development.error_dictionary_dymola as e

        self._error_dict = e.ErrorDictionary()

    def setLibraryRoot(self, rootDir):
        """ Set the root directory of the library.

        :param rootDir: The top-most directory of the library.

        The root directory is the directory that contains the ``Resources`` folder
        and the top-level ``package.mo`` file.

        Usage: Type
           >>> import os
           >>> import buildingspy.development.regressiontest as r
           >>> rt = r.Tester()
           >>> myMoLib = os.path.join("buildingspy", "tests", "MyModelicaLibrary")
           >>> rt.setLibraryRoot(myMoLib)
        """
        self._libHome = os.path.abspath(rootDir)
        self._rootPackage = os.path.join(self._libHome, 'Resources', 'Scripts', 'Dymola')
        self.isValidLibrary(self._libHome)

    def useExistingResults(self, dirs):
        """ This function allows to use existing results, as opposed to running a simulation.

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

        """
        if len(dirs) == 0:
            raise ValueError(
                "Argument 'dirs' of function 'useExistingResults(dirs)' must have at least one element.")

        self.setNumberOfThreads(len(dirs))
        self._temDir = dirs
        self.deleteTemporaryDirectories(False)
        self._useExistingResults = True

    def setNumberOfThreads(self, number):
        """ Set the number of parallel threads that are used to run the regression tests.

        :param number: The number of parallel threads that are used to run the regression tests.

        By default, the number of parallel threads are set to be equal to the number of
        processors of the computer.
        """
        self._nPro = number

    def showGUI(self, show=True):
        """ Call this function to show the GUI of the simulator.

        By default, the simulator runs without GUI
        """
        self._showGUI = show
        return

    def batchMode(self, batchMode):
        """ Set the batch mode flag.

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

        """
        self._batch = batchMode

    def pedanticModelica(self, pedanticModelica):
        """ Set the pedantic Modelica mode flag.

        :param pedanticModelica: Set to ``True`` to run the unit tests in the pedantic Modelica mode.

        By default, regression tests are run in non-pedantic Modelica mode.
        This however will be changed in the near future.

        >>> import os
        >>> import buildingspy.development.regressiontest as r
        >>> r = r.Tester()
        >>> r.pedanticModelica(True)
        >>> r.run() # doctest: +SKIP

        """
        self._pedanticModelica = pedanticModelica

    def include_fmu_tests(self, fmu_export):
        """ Sets a flag that, if ``False``, does not test the export of FMUs.

        :param fmu_export: Set to ``True`` to test the export of FMUs (default), or ``False``
                           to not test the FMU export.

        To run the unit tests but do not test the export of FMUs, type

        >>> import os
        >>> import buildingspy.development.regressiontest as r
        >>> r = r.Tester()
        >>> r.include_fmu_tests(False)
        >>> r.run() # doctest: +SKIP

        """
        self._include_fmu_test = fmu_export

    def getModelicaCommand(self):
        """ Return the name of the modelica executable.

        :return: The name of the modelica executable.

        """
        import platform

        if self._modelica_tool == 'openmodelica':
            # get the executable for omc, depending on platform
            if platform.system() == "Windows":
                try:
                    omc = os.path.join(env['OPENMODELICAHOME'], 'bin', 'omc')
                except KeyError:
                    raise OSError("Environment flag 'OPENMODELICAHOME' must be set")
            else:
                # we suppose the omc executable is known
                omc = 'omc'
            return omc
        elif self._modelica_tool != 'dymola':
            return 'jm_ipython.sh'
        else:
            return self._modelica_tool

    def isExecutable(self, program):
        """ Return ``True`` if the ``program`` is an executable
        """
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

    @staticmethod
    def isValidLibrary(library_home):
        """ Returns true if the regression tester points to a valid library
            that implements the scripts for the regression tests.

        :param library_home: top-level directory of the library, such as ``Buildings``.
        :return: ``True`` if the library implements regression tests, ``False`` otherwise.
        """
        topPackage = os.path.abspath(os.path.join(library_home, "package.mo"))
        if not os.path.isfile(topPackage):
            raise ValueError("Directory %s is not a Modelica library.\n    Expected file '%s'."
                             % (library_home, topPackage))
        srcDir = os.path.join(library_home, "Resources", "Scripts")
        if not os.path.exists(srcDir):
            raise ValueError(
                "Directory %s is not a Modelica library.\n    Expected directories '%s'." %
                (library_home, srcDir))

        return os.path.exists(os.path.join(library_home, "Resources", "Scripts"))

    def getLibraryName(self):
        """ Return the name of the library that will be run by this regression test.

        :return: The name of the library that will be run by this regression test.
        """
        return os.path.basename(self._libHome)

    def checkPythonModuleAvailability(self):
        """ Check whether all required python modules are installed.

            If some modules are missing, then an `ImportError` is raised.
        """
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
        """ Checks whether ``key`` is contained in the header of the file ``fileName``
            If the first line starts with ``within``
            and the second line starts with ``key``
            the counter is increased by one.
        """

        with open(fileName, mode="rt", encoding="utf-8-sig") as filObj:
            # filObj is an iterable object, so we can use next(filObj)
            line0 = next(filObj).strip()
            if line0.startswith("within"):
                line1 = next(filObj).strip()
                if line1.startswith(key):
                    counter += 1
        return counter

    @staticmethod
    def expand_packages(packages):
        """
        Expand the ``packages`` from the form
        ``A.{B,C}`` and return ``A.B,A.C``
        :param: packages: A list of packages
        """
        ids = packages.find('{')
        if ids < 0:
            # This has no curly bracket notation
            return packages

        ide = packages.find('}')

        # Make some simple test for checking the string format
        if ide - 1 <= ids:
            raise ValueError("String '{}' is wrong formatted".format(packages))

        # Get text before the curly brackets
        pre = packages[0:ids]
        # Get text inside the curly brackets
        in_bra = packages[ids + 1:ide]
        entries = in_bra.split(',')
        # Add the start to the entries
        pac = []
        for ele in entries:
            pac.append("{}{}".format(pre, ele))
        ret = ",".join(pac)
        return ret.replace(' ', '')

    def _remove_duplicate_packages(self, packages):
        """ Remove duplicate packages in the list of packages.

            For example, if packages = [A.B.C, A.B, A.F], or packages = [A.B, A.B.C, A.F],
            then this function returns [A.B, A.F] because A.B.C is already contained in A.B
        """
        sor = sorted(packages)  # This sets sor = [A.B, A.B.C, A.F]
        ret = list()
        for i in range(len(sor)):
            add = True
            for j in range(len(ret)):
                if sor[i].startswith(ret[j]):
                    # The parent package is already in the list
                    add = False
                    self._reporter.writeWarning(
                        "Found package that is contained in other package in test configuration '{}' and '{}'".format(
                            sor[i], ret[j]))
            if add:
                ret.append(sor[i])
        return ret

    def setSinglePackage(self, packageName):
        """
        Set the name of one or multiple Modelica package(s) to be tested.

        :param packageName: The name of the package(s) to be tested.

        Calling this method will cause the regression tests to run
        only for the examples in the package ``packageName``, and in
        all its sub-packages.

        For example:

        * If ``packageName = IBPSA.Controls.Continuous.Examples``,
          then a test of the ``IBPSA`` library will run all examples in
          ``IBPSA.Controls.Continuous.Examples``.
        * If ``packageName = IBPSA.Controls.Continuous.Examples,IBPSA.Controls.Continuous.Validation``,
          then a test of the ``IBPSA`` library will run all examples in
          ``IBPSA.Controls.Continuous.Examples`` and in ``IBPSA.Controls.Continuous.Validation``.

        """

        # Create a list of packages, unless packageName is already a list
        packages = list()
        if ',' in packageName:
            # First, split packages in case they are of the form Building.{Examples, Fluid}
            expanded_packages = self.expand_packages(packageName)
            packages = expanded_packages.split(',')
        else:
            packages.append(packageName)
        packages = self._remove_duplicate_packages(packages)
        # Inform the user that not all tests are run, but don't add to warnings
        # as this would flag the test to have failed
        self._reporter.writeOutput(
            """Regression tests are only run for the following package{}:""".format(
                '' if len(packages) == 1 else 's'))
        for pac in packages:
            self._reporter.writeOutput("""  {}""".format(pac))
        # Remove the top-level package name as the unit test directory does not
        # contain the name of the library.

        # Set data dictionary as it may have been generated earlier for the whole library.
        self._data = []

        for pac in packages:
            pacSep = pac.find('.')
            pacPat = pac[pacSep + 1:]
            pacPat = pacPat.replace('.', os.sep)
            rooPat = os.path.join(self._libHome, 'Resources', 'Scripts', 'Dymola', pacPat)
            # Verify that the directory indeed exists
            if not os.path.isdir(rooPat):
                msg = """Requested to test only package '%s', but directory
'%s' does not exist.""" % (pac, rooPat)
                raise ValueError(msg)
            self.setDataDictionary(rooPat)

    def writeOpenModelicaResultDictionary(self):
        """ Write in ``Resources/Scripts/OpenModelica/compareVars`` files whose
        name are the name of the example model, and whose content is::

            compareVars :=
              {
                "controler.y",
                "sensor.T",
                "heater.Q_flow"
              };

        These files are then used in the regression testing that is done by the
        OpenModelica development team.

        """
        import glob
        # Create the data dictionary.
        if len(self._data) == 0:
            self.setDataDictionary(self._rootPackage)

        # Directory where files will be stored
        desDir = os.path.join(self._libHome, "Resources", "Scripts", "OpenModelica", "compareVars")
        if not os.path.exists(desDir):
            os.makedirs(desDir)

        # Loop over all experiments and write the files.
        for experiment in self._data:
            if 'model_name' in experiment:
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
                    filNam = os.path.join(desDir, experiment['model_name'] + ".mos")
                    # Write the file
                    with open(filNam, mode="w", encoding="utf-8") as fil:
                        fil.write(filCon)

    @staticmethod
    def get_plot_variables(line):
        """ For a string of the form `*y={aa,bb,cc}*`, optionally with whitespace characters,
        return the list `[aa, bb, cc]`.
        If the string does not contain `y = ...`, return `None`.

        A usage may be as follows. Note that the second call returns `None` as
        it has a different format.

          >>> import buildingspy.development.regressiontest as r
          >>> r.Tester.get_plot_variables('y = {"a", "b", "c"}')
          ['a', 'b', 'c']
          >>> r.Tester.get_plot_variables('... x}, y = {"a", "b", "c"}, z = {...')
          ['a', 'b', 'c']
          >>> r.Tester.get_plot_variables("y=abc") is None
          True

        """
        import re
        import shlex

        # Make sure line has no "y = {..." that is not closed, e.g., it spans multiple lines
        incomplete = re.search(r"y\s*=\s*{.*\n", line)
        # This evaluates for example
        #   re.search("y.*=.*{.*}", "aay = {aa, bb, cc}aa").group()
        #   'y = {aa, bb, cc}'
        var = re.search(r"y\s*=\s*{.*}", line)
        if var is None and incomplete is None:
            return None
        if var is None and incomplete is not None:
            msg = "Malformed line '{}'".format(line)
            raise ValueError(msg)

        s = var.group()
        s = re.search('{.*?}', s).group()
        s = s.strip('{}')
        # Use the lexer module as simply splitting by "," won't work because arrays have
        # commas in the form "a[1, 1]", "a[1, 2]"
        lexer = shlex.shlex(s)
        lexer.quotes = '"'
        lexer.whitespace = ", \t"  # Skip commas, otherwise they are also returned as a token
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
            y[i] = re.sub(r',\W*', ', ', y[i])
        return y

    @staticmethod
    def get_tolerance(library_home, model_name):
        """ Return the tolerance as read from the `.mo` file.

            :param library_home: Home directory of the library.
            :param model_name: Name of the model.
        """
        import os
        import re
        import io

        file_name = os.path.join(library_home, '..', model_name.replace('.', os.path.sep) + ".mo")
        if not os.path.exists(file_name):
            raise IOError("Failed to find file '{}' for model '{}'".format(file_name, model_name))

        p_number = re.compile(r'Tolerance\s*=\s*(-?\ *[0-9]+\.?[0-9]*(?:[Ee]\ *-?\ *[0-9]+)?)')
        tols = list()
        with open(file_name, 'r') as fil:
            for lin in fil:
                tol = re.findall(p_number, lin)
                if len(tol) > 0:
                    tols.append(tol)

        # Make sure we found exactly one entry
        if len(tols) == 0:
            raise RuntimeError("Failed to find Tolerance in '{}'.".format(file_name))

        if len(tols) > 1:
            raise RuntimeError(
                "Found multiple entries for Tolerance in '{}', but require exactly one entry.".format(file_name))
        return tols[0][0]

    def setDataDictionary(self, root_package=None):
        """ Build the data structures that are needed to parse the output files.

           :param: root_package The name of the top-level package for which the files need to be parsed.
                                Separate package names with a period.

        """
        def _set_attribute_value(line, keyword, dat):
            """ Set the value of an attribute from the `.mos` file.

                This function will remove leading and ending quotes.

                :param line: The line that contains the keyword and the value.
                :param keyword: The keyword
                :param dat: The data dictionary to which dat[keyword] = value will be written.

            """
            line = re.sub(' ', '', line)
            pos = line.find(keyword)
            if pos > -1:
                posEq = line.find('=', pos)
                posComma = line.find(',', pos)
                posBracket = line.find(')', pos)
                posEnd = min(posComma, posBracket)
                if posEnd < 0:
                    posEnd = max(posComma, posBracket)
                # Ensure that keyword is directly located before the next = sign
                if posEq == pos + len(keyword):
                    entry = line[posEq + 1:posEnd]
                    dat[keyword] = re.sub(r'^"|"$', '', entry)
            return

        # Check if the data dictionary has already been set, in
        # which case we return doing nothing.
        # This is needed because methods append to the dictionary, which
        # can lead to double entries.
        roo_pac = root_package if root_package is not None else os.path.join(
            self._libHome, 'Resources', 'Scripts', 'Dymola')
        for root, _, files in os.walk(roo_pac):
            for mosFil in files:
                # Exclude the conversion scripts and also backup copies
                # which have the extensions .mos~ if they are generated from emacs
                if mosFil.endswith('.mos') and (
                    not mosFil.startswith(
                        "Convert" + self.getLibraryName())):
                    dat = {'ScriptFile': os.path.join(
                        root[len(os.path.join(self._libHome, 'Resources', 'Scripts', 'Dymola')) + 1:], mosFil)}
                    # ScriptFile is something like Controls/Continuous/Examples/LimPIDWithReset.mos
                    # JModelica CI testing needs files below 140 characters, which includes Buildings.
                    # Hence, write warning if a file is equal or longer than 140-9=131 characters.
                    if len(dat['ScriptFile']) >= 131:
                        self._reporter.writeError(
                            """File {} is {}-character long. Reduce it to maximum of 130 characters.""".format(
                                dat['ScriptFile'], len(
                                    dat['ScriptFile'])))
                    # _check_reference_result_file_name(dat['ScriptFile'])
                    # open the mos file and read its content.
                    # Path and name of mos file without 'Resources/Scripts/Dymola'
                    with open(os.path.join(root, mosFil), mode="r", encoding="utf-8-sig") as fMOS:
                        Lines = fMOS.readlines()

                    # Remove white spaces
                    for i in range(len(Lines)):
                        Lines[i] = Lines[i].replace(' ', '')

                    # Set some attributes in the Data object
                    dat['dymola'] = {
                        'exportFMU': False,
                        'translate': False,
                        'simulate': False
                    }  # May be switched to True below

                    for lin in Lines:
                        # Add the model name to the dictionary.
                        # This is needed to export the model as an FMU.
                        # Also, set the flag mustSimulate to True.
                        simCom = re.search(r'simulateModel\(\s*".*"', lin)
                        if simCom is not None:
                            dat['dymola']['translate'] = True
                            dat['dymola']['simulate'] = True
                            modNam = re.sub(r'simulateModel\(\s*"', '', simCom.string)
                            modNam = modNam[0:modNam.index('"')]
                            dat['model_name'] = modNam
                            dat['dymola']['TranslationLogFile'] = modNam + ".translation.log"
                            # Not all .mos files list startTime and stopTime.
                            # Hence, set the default values, which may be overridden just below.
                            dat["startTime"] = 0
                            dat["stopTime"] = 1
                        # parse startTime and stopTime, if any
                        for attr in ["startTime", "stopTime"]:
                            _set_attribute_value(lin, attr, dat)
                        # Check if this model need to be translated as an FMU.
                        if (not dat['dymola']['exportFMU']) and ("translateModelFMU" in lin):
                            dat['dymola']['exportFMU'] = True
                            dat['dymola']['translate'] = False
                            dat['dymola']['simulate'] = False
                        if dat['dymola']['exportFMU']:
                            for attr in ["modelToOpen", "modelName"]:
                                _set_attribute_value(lin, attr, dat['dymola'])

                    # We are finished iterating over all lines of the .mos

                    # Dymola uses in translateModelFMU the syntax
                    # modelName=... but our dictionary uses model_name
                    if dat['dymola']['exportFMU']:
                        if 'modelToOpen' in dat['dymola'] and len(dat['dymola']['modelToOpen']) > 0:
                            dat['model_name'] = dat['dymola']['modelToOpen']
                        if 'model_name' not in dat and dat['dymola']['modelName'] in dat:
                            dat["model_name"] = dat['dymola']['modelName']
                        if dat['dymola']['modelName'] in dat:
                            # This is not needed anymore
                            del dat['dymola']['modelName']

                    # Some files like plotFan.mos has neither a simulateModel
                    # nor a translateModelFMU command.
                    # These must not be added to the data array. Hence we skip further processing.
                    if dat['dymola']['translate'] == False and dat['dymola']['exportFMU'] == False:
                        continue

                    # The .mos script allows modelName="", hence
                    # we set the model name to be the entry of modelToOpen
#                    elif "model_name" not in dat['dymola'] and "modelToOpen" in dat['dymola']:
#                        dat['model_name'] = dat['dymola']['modelToOpen']

#                        # Make sure model_name is set
#                        if 'model_name' not in dat or dat['model_name'] == '':
#                            msg = f"Failed to set model_name for {os.path.join(root, mosFil)}"
#                            raise ValueError(msg)
                    dat['dymola']['TranslationLogFile'] = dat['model_name'] + ".translation.log"
                    # Get tolerance from mo file. This is used to set the tolerance
                    # for OpenModelica and OPTIMICA.
                    # Only get the tolerance for the models that need to be simulated,
                    # because those that are only exported as FMU don't need this setting.
                    if not dat['dymola']['exportFMU']:
                        try:
                            dat['tolerance'] = self.get_tolerance(
                                self._libHome, dat['model_name'])
                        except Exception as e:
                            self._reporter.writeError(str(e))
                            dat['tolerance'] = None
                    # For FMU export, if model_name="", then Dymola uses the
                    # Modelica class name, with "." replaced by "_".
                    # If the Modelica class name consists of "_", then they
                    # are replaced by "_0".
                    # Hence, we update dat['model_name'] if needed.
                    if dat['dymola']['exportFMU']:
                        # Strip quotes from model_name and modelToOpen
                        dat['dymola']['FMUName'] = dat['model_name'].strip('"')
                        dat['dymola']['modelToOpen'] = dat['dymola']['modelToOpen'].strip('"')
                        # Update the name of the FMU if model_name is "" in .mos file.
                        if len(dat['dymola']['FMUName']) == 0:
                            dat['dymola']['FMUName'] = dat['dymola']['modelToOpen']
                        # Update the FMU name, for example to change
                        # Buildings.Fluid.FMI.Examples.FMUs.IdealSource_m_flow to
                        # Buildings_Fluid_FMI_Examples_FMUs_IdealSource_0m_0flow
                        dat['dymola']['FMUName'] = dat['dymola']['FMUName'].replace(
                            "_", "_0").replace(".", "_")
                        dat['dymola']['FMUName'] = dat['dymola']['FMUName'] + ".fmu"
                    # Plot variables are only used for those models that need to be simulated.
                    if not dat['dymola']['exportFMU']:
                        plotVars = []
                        iLin = 0
                        for lin in Lines:
                            iLin = iLin + 1
                            try:
                                y = self.get_plot_variables(lin)
                                if y is not None:
                                    plotVars.append(y)
                            except (AttributeError, ValueError) as e:
                                s = "%s, line %s, could not be parsed.\n" % (mosFil, iLin)
                                s += "The problem occurred at the line below:\n"
                                s += "%s\n" % lin
                                s += "Make sure that each assignment of the plot command is on one line.\n"
                                self._reporter.writeError(s)
                                # Store the error, but keep going to check other lines and files
                                pass
                        if len(plotVars) == 0:
                            s = "%s does not contain any plot command.\n" % mosFil
                            s += "You need to add a plot command to include its\n"
                            s += "results in the regression tests.\n"
                            self._reporter.writeError(s)
                        # Store grouped plot variables without duplicates.
                        # (Duplicates happen when the same y variables are plotted against
                        # different x variables.)
                        dat['ResultVariables'] = []
                        for v_i in plotVars:
                            if v_i not in dat['ResultVariables']:
                                dat['ResultVariables'].append(v_i)
                        # Create the result file name.
                        if self._modelica_tool == 'dymola':
                            # For Dymola, this is not the name in the .mos file (as these may not be unique).
                            # Rather, we set the result file name to be the mos file name with
                            # .mat extension
                            matFil = f"{dat['model_name']}.mat"
                        elif self._modelica_tool == 'openmodelica':
                            matFil = f"{dat['model_name']}_res.mat"
                        else:
                            matFil = '{}_result.mat'.format(
                                re.sub(r'\.', '_', dat['model_name']))
                        # Some *.mos file only contain plot commands, but no simulation.
                        # Hence, if 'resultFile=' could not be found, try to get the file that
                        # is used for plotting.
                        # cf. BUG
                        if len(matFil) == 0:
                            for lin in Lines:
                                if 'filename=\"' in lin:
                                    # Note that the filename entry already has the .mat
                                    # extension.
                                    matFil = re.search(
                                        r'(?<=filename=\")[a-zA-Z0-9_\.]+', lin).group()
                                    break
                        if len(matFil) == 0:
                            raise ValueError('Did not find *.mat file in ' + mosFil)
                        dat['ResultFile'] = matFil
                    self._data.append(dat)

        # Make sure we found at least one unit test.
        if self.get_number_of_tests() == 0:
            msg = """Did not find any regression tests in '%s'.""" % root_package
            self._reporter.writeError(msg)

        # Make sure there are no duplicate data
        self._checkDataDictionary()
        # Raise an error if there was any error reported.
        if self._reporter.getNumberOfErrors() > 0:
            raise ValueError("Error when setting up unit tests.")

        # Add the experiment specifications from conf.json to the data.
        self._add_experiment_specifications()
        # For those records for which Dymola needs to simply export the FMU,
        # no simulation should be done with any tool (as these models generally
        # require input signals)
        for dat in self._data:
            if dat['dymola']['exportFMU']:
                dat[self._modelica_tool]['simulate'] = False

        return

    def _sort_yml_file(self, conf_data, conf_file_name):
        """ Sort the content of the yml file and write it back to disk with the extension sorted.
        """
        import yaml as y
        import sys
        # Sort the list of dictionary items
        sor = sorted(conf_data, key=lambda i: i['model_name'])
        if not sor == conf_data:
            fname = f"{conf_file_name}.sorted"
            self._reporter.writeWarning(
                f"Configuration file was not sorted. Wrote sorted configuration data to {fname}.")
            with open(fname, 'w') as f:
                y.safe_dump(sor, f, sort_keys=False, width=4096)

    def _validate_experiment_specifications(self, conf_data, conf_file_name):
        from cerberus import Validator
        # Read schema
        with open(os.path.join(
                os.path.dirname(__file__), os.path.pardir, 'templates', 'regressiontest_conf.py'), 'r') as f:
            schema = json.load(f)
        v = Validator(schema)
        # Validate
        found_error = False
        for dat in conf_data:
            if not v.validate(dat, schema):
                for k in v.errors.keys():
                    self._reporter.writeError(
                        f"{conf_file_name}:  {k} {v.errors[k]} error in '{str(dat)}'")
                found_error = True
        if found_error:
            raise ValueError(f"Failed to validate configuration file {conf_file_name}.")

    def _validate_experiment_specifications_model_names(self, conf_data, conf_file_name):
        """ Make sure each model_name is unique
        """
        names = []
        for dat in conf_data:
            names.append(dat['model_name'])
        found_error = False
        for name in names:
            if names.count(name) > 1:
                found_error = True
                self._reporter.writeError(f"{conf_file_name}: 'model_name: {name}' is duplicate.")
        if found_error:
            raise ValueError(f"Failed to validate configuration file {conf_file_name}.")

    def _add_experiment_specifications(self):
        """ Add the experiment specification to the data structure.

            This method reads the `Resources/Scripts/BuildingsPy/conf.yml` file
            and adds it to the data structure.
        """
        import copy
        import json
        import yaml

        def _verify_model_exists(model_name):
            """ Verify that `model_name` exists. If it does not exist, log an error.
            """
            mo_name = os.path.abspath(
                f"{os.path.join(self._libHome, '..', model_name.replace('.', os.path.sep))}.mo")
            if not os.path.isfile(mo_name):
                self._reporter.writeError(
                    f"{conf_file_name} specifies {con_dat['model_name']}, but there is no model file {mo_name}.")

        if self._modelica_tool == 'dymola':
            for ent in self._data:
                ent['dymola']['time_out'] = 300
        else:  # Non-dymola
            def_dic = {}
            def_dic[self._modelica_tool] = {
                'translate': True,
                'simulate': True,
                'solver': 'CVode' if self._modelica_tool != 'openmodelica' else 'dassl',
                'ncp': 500,
                'time_out': 300
            }

            for all_dat in self._data:
                # Add default data
                for key in def_dic[self._modelica_tool].keys():
                    # all_dat only exists for Dymola, not for the other tools
                    if self._modelica_tool not in all_dat:
                        all_dat[self._modelica_tool] = {}
                    all_dat[self._modelica_tool][key] = copy.deepcopy(
                        def_dic[self._modelica_tool][key])

        # Get configuration data from file, if present
        conf_dir = os.path.join(self._libHome, 'Resources', 'Scripts', 'BuildingsPy')
        conf_json = os.path.join(conf_dir, 'conf.json')
        conf_yml = os.path.join(conf_dir, 'conf.yml')

        if os.path.exists(conf_json) and os.path.exists(conf_yml):
            raise ValueError(
                f"Found {conf_yml} and {conf_json}. Only one must exist. Future versions will only support the .yml file.")

        if os.path.exists(conf_json) or os.path.exists(conf_yml):
            if os.path.exists(conf_yml):
                conf_file_name = conf_yml
                with open(conf_yml, 'r') as f:
                    conf_data = yaml.safe_load(f)
                self._sort_yml_file(conf_data, conf_file_name)
            else:
                conf_file_name = conf_json
                with open(conf_json, 'r') as f:
                    conf_data = json.load(f)
            # Validate the configuration file
            self._validate_experiment_specifications(conf_data, conf_file_name)
            self._validate_experiment_specifications_model_names(conf_data, conf_file_name)

            # Validate entries for model_name
            for con_dat in conf_data:
                _verify_model_exists(con_dat['model_name'])
            if self._reporter.getNumberOfErrors() > 0:
                raise ValueError(f"Wrong specification in {conf_file_name}.")

            # Add model specific data
            for con_dat in conf_data:
                for all_dat in self._data:
                    if con_dat['model_name'] == all_dat['model_name']:
                        # Add all elements of the configuration data
                        for key in con_dat.keys():
                            # Have dictionary in dictionary
                            if key == self._modelica_tool:
                                for k in con_dat[self._modelica_tool]:
                                    val = con_dat[self._modelica_tool][k]
                                    all_dat[self._modelica_tool][k] = val
                            else:
                                if key != 'dymola':
                                    all_dat[key] = con_dat[key]
                                else:
                                    # Don't override the already set data for dymola
                                    for con_key in con_dat.keys():
                                        # if con_dat[con_key] is a dictionary, then it is the specification for openmodelica or optimica.
                                        # Hence, don't add it to dymola
                                        if not type(con_dat[con_key]) is dict:
                                            all_dat['dymola'][con_key] = con_dat[con_key]
                        # Write warning if this model should not be translated or simulated.
                        msg = None
                        if all_dat[self._modelica_tool]['translate'] is False:
                            msg = f"{all_dat['model_name']}: Excluded from translation."
                        elif all_dat[self._modelica_tool]['simulate'] is False:
                            msg = f"{all_dat['model_name']}: Excluded from simulation."
                        if msg is not None:
                            if 'comment' in all_dat[self._modelica_tool]:
                                msg = f"{msg} {self._color_GREY}{all_dat[self._modelica_tool]['comment']}{self._color_ENDC}"
                            self._reporter.writeOutput(msg)
            for all_dat in self._data:
                # Set simulate to false as well as it can't be simulated
                # if not translated
                if 'translate' in all_dat[self._modelica_tool] and all_dat[self._modelica_tool]['translate'] == False:
                    all_dat[self._modelica_tool]['simulate'] = False
            # Stop if there were any errors
            if self._reporter.getNumberOfErrors() > 0:
                raise ValueError(f"Wrong specification in {conf_file_name}.")

    def _checkDataDictionary(self):
        """ Check if the data used to run the regression tests do not have duplicate ``*.fmu`` files
            and ``*.mat`` names.

            Since Dymola writes all ``*.fmu`` and ``*.mat`` files to the current working directory,
            duplicate file names would cause a translation or simulation to overwrite the files
            of a previous test. This would make it impossible to check the FMU export
            and to compare the results to previously obtained results.

            If there are duplicate ``.fmu`` and ``*.mat`` file names used, then this method raises
            a ``ValueError`` exception.

        """
        s_fmu = set()
        s_mat = set()
        errMes = ""
        for data in self._data:
            if 'ResultFile' in data:
                resFil = data['ResultFile']
                if "stopTime" in data:
                    if resFil in s_mat:
                        errMes += "*** Error: Result file %s is generated by more than one script.\n" \
                            "           You need to make sure that all scripts use unique result file names.\n" % resFil
                    else:
                        s_mat.add(resFil)
        if self._modelica_tool == 'dymola':
            for data in self._data:
                if 'FMUName' in data['dymola']:
                    fmuFil = data['dymola']['FMUName']
                    if fmuFil in s_fmu:
                        errMes += "*** Error: FMU file {} is generated by more than one script.\n" \
                            "           You need to make sure that all scripts use unique result file names.\n".format(
                                fmuFil)
                    else:
                        s_fmu.add(fmuFil)
        if len(errMes) > 0:
            raise ValueError(errMes)

    def _getTimeGrid(self, tMin, tMax, nPoi):
        """
        Return the time grid for the output result interpolation

        :param tMin: Minimum time of the results.
        :param tMax: Maximum time of the results.
        :param nPoi: Number of result points.
        """
        return [tMin + float(i) / (nPoi - 1) * (tMax - tMin) for i in range(nPoi)]

    def _getSimulationResults(self, data, warnings, errors):
        """Get the simulation results for a single unit test.

        :param data: The class that contains the data structure for the simulation results.
        :param warning: A list to which all warnings will be appended.
        :param errors: A list to which all errors will be appended.

        Extracts and returns the simulation results from the `*.mat` file as
        a list of dictionaries. Each element of the list contains a dictionary
        of results that need to be printed together.
        """
        def extractData(y, step):
            # Replace the last element with the last element in time,
            # [::step] may not extract the last time stamp, in which case
            # the final time changes when the number of event changes.
            r = y[::step]
            r[len(r) - 1] = y[len(y) - 1]
            return r

        def _getTimeGridFromSimulationResults(pairs):
            nCt=0
            timeGrid=[]
            # Loop over all variables to find maximum length of time grid
            for pai in pairs: # pairs of variables that are plotted together
                for var in pai:
                    time = []
                    (time, val) = r.values(var)
                    if(len(time==2) and nCt < 1):
                        timeGrid=time
                        nCt=nCt+1
                    elif(len(time) > 2):
                        timeGrid=time
                        nCt=nCt+1
            return timeGrid


        # Get the working directory that contains the ".mat" file
        fulFilNam = os.path.join(data['ResultDirectory'], self.getLibraryName(), data['ResultFile'])
        if self._modelica_tool != 'dymola':
            fulFilNam = os.path.join(data['ResultDirectory'], data['ResultFile'])
        ret = []
        try:
            r = Reader(fulFilNam, self._modelica_tool)
        except IOError as e:
            errors.append("IOError while reading %s generated by %s.\n%s\n" %
                          (fulFilNam, data['ScriptFile'], e))
            return ret
        except ValueError as e:  # BUG #9
            errors.append("ValueError while reading %s generated by %s.\n%s\n" %
                          (fulFilNam, data['ScriptFile'], e))
            return ret
        except MemoryError as e:
            errors.append("MemoryError while reading %s generated by %s.\n%s\n" %
                          (fulFilNam, data['ScriptFile'], e))
            return ret
        except Exception as e:
            errors.append("Exception while reading %s generated by %s.\n%s\n" %
                          (fulFilNam, data['ScriptFile'], e))
            return ret

        timeGrid = _getTimeGridFromSimulationResults(data['ResultVariables'])


        for pai in data['ResultVariables']:  # pairs of variables that are plotted together
            dat = dict()
            for var in pai:
                time = []
                val = []
                try:
                    var_mat = var
                    # Matrix variables in OpenModelica and OPTIMICA are stored in mat file with
                    # no space e.g. [1,1].
                    if self._modelica_tool != 'dymola':
                        var_mat = re.sub(' ', '', var_mat)
                    (time, val) = r.values(var_mat)
                    # Make time grid to which simulation results
                    # will be interpolated.
                    # This reduces the data that need to be stored.
                    # It also makes it easier to compare accuracy
                    # in case that a slight change in the location of
                    # state events triggered a different output interval grid.
                    tMin = float(min(time))
                    tMax = float(max(time))
                    nPoi = min(self._nPoi, len(val))
                    ti = self._getTimeGrid(tMin, tMax, nPoi)
                except ZeroDivisionError as e:
                    s = "When processing " + fulFilNam + " generated by " + \
                        data['ScriptFile'] + ", caught division by zero.\n"
                    s += "   len(val)  = " + str(len(val)) + "\n"
                    s += "   tMax-tMin = " + str(tMax - tMin) + "\n"
                    errors.append(s)
                    break
                except ValueError as e:
                    s = "When processing " + fulFilNam + " generated by " + \
                        data['ScriptFile'] + ", caught ValueError.\n"
                    s += "   type(time) = " + str(type(time)) + "\n"
                    break
                except KeyError:
                    # This must be an error, otherwise the user would be asked
                    # to accept a reference result file with a variable that does not exist.
                    errors.append("%s uses %s which does not exist in %s.\n" %
                                  (data['ScriptFile'], var, data['ResultFile']))
                else:
                    # Store time grid.
                    if self._OCT_VERIFICATION:
                        dat['time']=timeGrid
                        if (self._isParameter(val)):
                            import numpy as np
                            dat[var]=np.ones(len(timeGrid))*val[0]
                        else:
                            dat[var] = val
                    else:
                        if ('time' not in dat):
                            dat['time'] = [tMin, tMax]
                        if self._isParameter(val):
                            dat[var] = val
                        else:
                            try:
                                dat[var] = Plotter.interpolate(ti, time, val)
                            except ValueError as e:
                                msg = "Failed to process {} generated by {}.\n{}\n".format(
                                    fulFilNam, data['ScriptFile'], e)
                                errors.append(msg)
                                return ret

            if len(dat) > 0:
                ret.append(dat)
        return ret

    def _getDymolaTranslationStatistics(self, data, warnings, errors):
        """
        Get the translation statistics for a single unit test.

        :param data: The class that contains the data structure for the simulation results.
        :param warning: A list to which all warnings will be appended.
        :param errors: A list to which all errors will be appended.
        :return: The translation log from the `*.translation.log` file as
        a list of dictionaries, or `None` if `*.translation.log` does not exist.

        Extracts and returns the translation log from the `*.translation.log` file as
        a list of dictionaries.
        In case of an error, this method returns `None`.
        """
        # Get the working directory that contains the ".log" file
        fulFilNam = os.path.join(data['ResultDirectory'],
                                 self.getLibraryName(), data['dymola']['TranslationLogFile'])
        if os.path.exists(fulFilNam):
            return of.get_model_statistics(fulFilNam, self._modelica_tool)
        else:
            return None

    def _legacy_comp(self, tOld, yOld, tNew, yNew, tGriOld, tGriNew, varNam, filNam, tol):
        # Interpolate the new variables to the old time stamps
        #
        if len(yNew) > 2:
            try:
                yInt = Plotter.interpolate(tGriOld, tGriNew, yNew)
            except (IndexError, ValueError):
                em = (
                    "Data series have different length:\n"
                    "File=%s\n"
                    "variable=%s\n"
                    "len(tGriOld) = %d\n"
                    "len(tGriNew) = %d\n"
                    "len(yNew)    = %d\n") % (filNam,
                                              varNam,
                                              len(tGriOld),
                                              len(tGriNew),
                                              len(yNew))
                self._reporter.writeError(em)
                raise ValueError(em)
        else:
            yInt = [yNew[0], yNew[0]]

        # If the variable is heatPort.T or heatPort.Q_flow, with length=2, then
        # it has been evaluated as a parameter in the Buildings library. In the IBPSA
        # library, this may be a variable as the Buildings library uses a more efficient
        # implementation of the heatPort. Hence, we test for this special case, and
        # store the parameter as if it were a variable so that the reference result are not
        # going to be changed.
        # (Not needed for funnel: can deal with len(yNew) != len(yOld))
        if (varNam.endswith("heatPort.T") or varNam.endswith("heatPort.Q_flow")) and (
                len(yInt) == 2) and len(yOld) != len(yInt):
            yInt = np.ones(len(yOld)) * yInt[0]

        # Compute error for the variable with name varNam
        if len(yOld) != len(yInt):
            # If yOld has two points, but yInt has more points, then
            # extrapolate yOld to nPoi
            t = self._getTimeGrid(tOld[0], tOld[-1], self._nPoi)
            if len(yOld) == 2 and len(yInt) == self._nPoi:
                t = self._getTimeGrid(t[0], t[-1], self._nPoi)
                yOld = Plotter.interpolate(t, tOld, yOld)
            # If yInt has only two data points, but yOld has more, then interpolate yInt
            elif len(yInt) == 2 and len(yOld) == self._nPoi:
                yInt = Plotter.interpolate(t, [tOld[0], tOld[-1]], yInt)
            else:
                raise ValueError((
                    "Program error, yOld and yInt have different lengths.\n"
                    "Result file : %s\n"
                    "Variable    : %s\n"
                    "len(yOld)=%d\n"
                    "len(yInt)=%d\n"
                    "Stop processing.\n") % (filNam, varNam, len(yOld), len(yInt))
                )

        errAbs = np.zeros(len(yInt))
        errRel = np.zeros(len(yInt))
        errFun = np.zeros(len(yInt))

        for i in range(len(yInt)):
            errAbs[i] = abs(yOld[i] - yInt[i])
            if np.isnan(errAbs[i]):
                raise ValueError('NaN in errAbs ' + varNam + " " + str(yOld[i])
                                 + "  " + str(yInt[i]) + " i, N " + str(i) +
                                 " --:" + str(yInt[i - 1])
                                 + " ++:", str(yInt[i + 1]))
            if (abs(yOld[i]) > 10 * tol):
                errRel[i] = errAbs[i] / abs(yOld[i])
            else:
                errRel[i] = 0
            errFun[i] = errAbs[i] + errRel[i]

        t_err_max, warning = 0, None

        if max(errFun) > tol:
            iMax = 0
            eMax = 0
            for i in range(len(errFun)):
                if errFun[i] > eMax:
                    eMax = errFun[i]
                    iMax = i
            tGri = self._getTimeGrid(tOld[0], tOld[-1], self._nPoi)
            t_err_max = tGri[iMax]
            warning = filNam + ": " + varNam + " has absolute and relative error = " + \
                ("%0.3e" % max(errAbs)) + ", " + ("%0.3e" % max(errRel)) + ".\n"
            if self._isParameter(yInt):
                warning += "             %s is a parameter.\n" % varNam
            else:
                warning += "             Maximum error is at t = %s\n" % str(t_err_max)

        return (t_err_max, warning)

    def _funnel_comp(
            self,
            tOld,
            yOld,
            tNew,
            yNew,
            varNam,
            filNam,
            model_name,
            tol,
            data_idx,
            keep_dir=True):
        """Method calling funnel comparison tool."""

        t_err_max, warning = 0, None
        tmp_dir = tempfile.mkdtemp()
        log_stdout = io.StringIO()
        with _stdout_redirector(log_stdout):
            exitcode = pyfunnel.compareAndReport(
                xReference=tOld,
                yReference=yOld,
                xTest=tNew,
                yTest=yNew,
                outputDirectory=tmp_dir,
                atolx=tol['ax'],
                atoly=tol['ay'],
                ltolx=tol['lx'],
                ltoly=tol['ly'],
                rtolx=tol['rx'],
                rtoly=tol['ry'],
            )
        log_content = log_stdout.getvalue()
        log_content = re.sub(r'(^.*Warning:\s+)|(Error:\s+)', '', log_content)
        log_stdout.close()

        if exitcode != 0:
            warning = "While processing file {} for variable {}: {}".format(
                filNam, varNam, log_content)
            test_passed = False
            funnel_success = False
        else:
            err_path = os.path.join(tmp_dir, 'errors.csv')
            err_arr = np.genfromtxt(err_path, delimiter=',', skip_header=1).transpose()
            err_max = np.max(err_arr[1])  # difference between y test value and funnel bounds
            idx_err_max = np.where(err_arr[1] == err_max)[0][0]
            t_err_max = err_arr[0][idx_err_max]
            test_passed = (err_max == 0)
            if err_max > 0:
                if self._isParameter(yOld):
                    warning = "Absolute error = {:.3e} for {}".format(err_max, varNam)
                else:
                    warning = "Absolute error = {:.3e} at t = {} for {}".format(
                        err_max, t_err_max, varNam)
            funnel_success = True

        if keep_dir and funnel_success:
            target_path = os.path.join(self._comp_dir, '{}_{}'.format(filNam, varNam))
            shutil.move(tmp_dir, target_path)
        else:
            target_path = None
            shutil.rmtree(tmp_dir)

        idx = self._init_comp_info(model_name, filNam)
        self._update_comp_info(idx, varNam, target_path, test_passed, t_err_max, warning, data_idx)

        return (t_err_max, warning)

    def _init_comp_info(self, model_name, file_name):
        """Update self._comp_info with dict to store comparison results for model_name.

        Returns: index of dict storing results for model_name.
        """
        try:
            idx = next(i for i, el in enumerate(self._comp_info) if el['model'] == model_name)
        except StopIteration:  # no model_name found in self._comp_info (case dymola): create
            self._comp_info.append({
                "model": model_name,
            })
            idx = len(self._comp_info) - 1
        try:
            self._comp_info[idx]["comparison"]
        except KeyError:  # no comparison data stored for model_name: create
            self._comp_info[idx]["comparison"] = {
                "variables": [],
                "funnel_dirs": [],
                "test_passed": [],
                "file_name": file_name,
                "success_rate": 0,
                "var_groups": [],  # index of the group of variables belonging to the same subplot
                "warnings": [],
                "t_err_max": [],
            }

        return idx

    def _update_comp_info(
            self,
            idx,
            var_name,
            funnel_dir,
            test_passed,
            t_err_max,
            warning,
            data_idx,
            var_group=None):
        """Store comparison info for var_name in self._comp_info."""

        # NOTE: data_idx can differ from idx if simulation failed or variable not available.

        should_update = True

        if var_group is None:
            try:
                var_group = next(
                    iv for iv, vl in enumerate(
                        self._data[data_idx]["ResultVariables"]) if var_name in vl)
            except StopIteration:
                if warning == 'skip':
                    should_update = False
                else:
                    warning = ("Variable {} not found in ResultVariables for model {}. "
                               "However it was found in reference results file.\n").format(
                        var_name, self._comp_info[idx]['model'])
                    self._reporter.writeWarning(warning)

        if should_update:
            self._comp_info[idx]["comparison"]["variables"].append(var_name)
            self._comp_info[idx]["comparison"]["funnel_dirs"].append(funnel_dir)
            self._comp_info[idx]["comparison"]["test_passed"].append(
                int(test_passed))  # Boolean not JSON serializable
            self._comp_info[idx]["comparison"]["t_err_max"].append(t_err_max)
            self._comp_info[idx]["comparison"]["warnings"].append(warning)
            self._comp_info[idx]["comparison"]["var_groups"].append(var_group)
            self._comp_info[idx]["comparison"]["success_rate"] = sum(
                self._comp_info[idx]["comparison"]["test_passed"]) / len(self._comp_info[idx]["comparison"]["variables"])

        return None

    def areResultsEqual(self, tOld, yOld, tNew, yNew, varNam, data_idx):
        """ Return `True` if the data series are equal within a tolerance.

        :param tOld: List of old time values.
        :param yOld: Old simulation results.
        :param tNew: Time stamps of new results.
        :param yNew: New simulation results.
        :param varNam: Variable name, used for reporting.
        :param filNam: File name, used for reporting.
        :param model_name: Model name, used for reporting.
        :return: A list with ``False`` if the results are not equal, and the time
                 of the maximum error, and an error message or `None`.
                 In case of errors, the time of the maximum error may by `None`.
        """
        try:
            filNam = self._data[data_idx]['ResultFile']
            model_name = self._data[data_idx]['model_name']
        except BaseException:
            filNam = 'Undefined file name'
            model_name = 'Undefined model name'

        def getTimeGrid(t, nPoi=self._nPoi):
            if len(t) == 2:
                return self._getTimeGrid(t[0], t[-1], nPoi)
            elif len(t) == nPoi:
                return t
            else:
                s = ("While processing file {} for variable {}: The new time grid has {} points "
                     "but it must have 2 or {} points.\n"
                     "Stop processing.\n").format(
                    filNam,
                    varNam,
                    len(tNew),
                    nPoi)
                raise ValueError(s)

        # Check if the first and last time stamp are equal
        def test_equal_time(t1, t2, tol=1E-3):
            """Test if time values are equal within a given tolerance.

            t1, t2 and tol are floats.

            Returns Boolean value equal to test result.
            If t1 is close to 0, the tolerance is considered as absolute.
            Otherwise, the tolerance is considered as relative to abs(t1).
            """
            if abs(t1) <= tol:
                res = abs(t1 - t2) <= tol
            else:
                res = abs(t1 - t2) <= tol * abs(t1)
            return res

        if not test_equal_time(tOld[0], tNew[0]):
            error = (
                "While processing file {} for variable {}: Different start time between "
                "reference and test data.\n"
                "Old reference points are for {} <= t <= {}\n"
                "New reference points are for {} <= t <= {}\n").format(
                    filNam, varNam, tOld[0], tOld[len(tOld) - 1], tNew[0], tNew[len(tNew) - 1])
            test_passed = False
            t_err_max = min(tOld[0], tNew[0])
        else:  # Overwrite tOld with tNew to prevent any exception raised by the comparison tool.
            tOld[0] = tNew[0]

        if not test_equal_time(tOld[-1], tNew[-1]):
            error = (
                "While processing file {} for variable {}: Different end time between "
                "reference and test data.\n"
                "           tNew = [{}, {}]\n"
                "           tOld = [{}, {}]").format(filNam, varNam, tNew[0], tNew[-1], tOld[0], tOld[-1])
            test_passed = False
            t_err_max = min(tOld[-1], tNew[-1])
        else:  # Overwrite tOld with tNew to prevent any exception raised by the comparison tool.
            tOld[-1] = tNew[-1]

        # The next test may be true if a simulation stopped with an error prior to
        # producing sufficient data points
        if len(yNew) < len(yOld) and len(yNew) > 2:
            error = (
                "While processing file {} for variable {}: Fewer data points than reference results.\n"
                "len(yOld) = {}\n"
                "len(yNew) = {}\n"
                "Skipping error checking for this variable.\n").format(
                filNam, varNam, len(yOld), len(yNew))
            test_passed = False
            t_err_max = None

        if self._comp_tool == 'legacy':
            if len(yNew) > 2:
                # Some reference results contain already a time grid,
                # whereas others only contain the first and last time stamp.
                # Hence, we make sure to have the right time grid before we
                # call the interpolation.
                tGriOld = getTimeGrid(tOld, len(yNew))
                tGriNew = getTimeGrid(tNew, min(len(yNew), self._nPoi))
            else:
                tGriOld = tOld
                tGriNew = tNew
        elif self._comp_tool == 'funnel':
            # funnel_comp only needs len(t) = len(y) for Old and New time series
            if len(yNew) > 2:
                tNew = getTimeGrid(tNew, len(yNew))
            if len(yOld) > 2:
                tOld = getTimeGrid(tOld, len(yOld))

        if self._comp_tool == 'legacy':
            try:  # In case an error has been raised before: no comparison performed.
                error
            except NameError:
                t_err_max, error = self._legacy_comp(
                    tOld, yOld, tNew, yNew, tGriOld, tGriNew, varNam, filNam, self._tol['ay'])
        else:
            idx = self._init_comp_info(model_name, filNam)
            comp_tmp = self._comp_info[idx]['comparison']
            try:
                # Check if the variable has already been tested.
                # (This might happen if the variable is used in different plots.)
                # In this case we do not want to perform the comparison again but we still want the variable to be
                # plotted several times as it was originally intended: update _comp_info
                # with stored data.
                var_idx = comp_tmp['variables'].index(varNam)
                fun_dir = comp_tmp['funnel_dirs'][var_idx]
                test_passed = comp_tmp['test_passed'][var_idx]
                # variable group already stored for this variable
                var_group_str = comp_tmp['var_groups'][var_idx]
                # Now looking for the new variable group to be stored.
                var_group = var_group_str + 1 + next(iv for iv, vl in enumerate(
                    self._data[data_idx]["ResultVariables"][(var_group_str + 1):]) if varNam in vl)
                error = comp_tmp['warnings'][var_idx]
                t_err_max = comp_tmp['t_err_max'][var_idx]
                self._update_comp_info(
                    idx,
                    varNam,
                    fun_dir,
                    test_passed,
                    t_err_max,
                    error,
                    data_idx,
                    var_group)
            except (ValueError, StopIteration):
                try:  # In case an error has been raised before: no comparison performed.
                    self._update_comp_info(
                        idx, varNam, None, test_passed, t_err_max, error, data_idx)
                except NameError:
                    t_err_max, error = self._funnel_comp(
                        tOld, yOld, tNew, yNew, varNam, filNam, model_name, self._tol, data_idx)

        test_passed = True
        if error is not None:
            test_passed = False

        return (test_passed, t_err_max, error)

    def _isParameter(self, dataSeries):
        """ Return `True` if `dataSeries` is from a parameter.
        """
        import numpy as np
        if not (isinstance(dataSeries, np.ndarray) or isinstance(dataSeries, list)):
            raise TypeError("Program error: dataSeries must be a numpy.ndarr or a list. Received type "
                            + str(type(dataSeries)) + ".\n")
        return (len(dataSeries) == 2)

    def format_float(self, value):
        """ Return the argument in exponential notation, with
            non-significant zeros removed.
        """
        import re
        return re.sub(re.compile(r'\.e'), 'e',
                      re.sub(re.compile('0*e'), 'e', "{0:.15e}".format(value)))

    def _writeReferenceResults(self, refFilNam, y_sim, y_tra):
        """ Write the reference results.

        :param refFilNam: The name of the reference file.
        :param y_sim: The data points to be written to the file.
        :param y_tra: The dictionary with the translation log.

        This method writes the results in the form ``key=value``, with one line per entry.
        """
        from datetime import date
        import json

        with open(refFilNam, mode="w", encoding="utf-8") as f:
#            f.write('last-generated=' + str(date.today()) + '\n')
            for stage in ['initialization', 'simulation', 'fmu-dependencies']:
                if stage in y_tra:
                    # f.write('statistics-%s=\n%s\n' % (stage, _pretty_print(y_tra[stage])))
                    f.write('statistics-%s=\n%s\n' % (stage, json.dumps(y_tra[stage],
                                                                        indent=2,
                                                                        separators=(',', ': '),
                                                                        sort_keys=True)))
            # FMU exports do not have simulation results.
            # Hence, we preclude them if y_sim == None
            if y_sim is not None:
                # Set, used to avoid that data series that are plotted in two plots are
                # written twice to the reference data file.
                s = set()
                for pai in y_sim:
                    for k, v in list(pai.items()):
                        if k not in s:
                            s.add(k)
                            f.write(k + '=')
                            # Use many digits, otherwise truncation errors occur that can be higher
                            # than the required accuracy.
                            formatted = [str(self.format_float(e)) for e in v]
                            f.write(str(formatted).replace("'", ""))
                            f.write('\n')

    def _readReferenceResults(self, refFilNam):
        """ Read the reference results.

        :param refFilNam: The name of the reference file.
        :return: A dictionary with the reference results.

        If the simulation statistics was found in the reference results,
        then the return value also has an entry
        `statistics-simulation={'numerical Jacobians': '0', 'nonlinear': ' ', 'linear': ' '}`,
        where the value is a dictionary. Otherwise, this key is not present.

        """
        import numpy
        import ast

        d = dict()
        with open(refFilNam, mode="r", encoding="utf-8-sig") as f:
            lines = f.readlines()

        # Compute the number of the first line that contains the results
        iSta = 0
        for iLin in range(min(2, len(lines))):
            if "svn-id" in lines[iLin]:
                iSta = iSta + 1
            if "last-generated" in lines[iLin]:
                iSta = iSta + 1

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
                    while (iLin < len(lines) - 1 and lines[iLin + 1].find('=') == -1):
                        value = value + lines[iLin + 1].strip('\n').strip()
                        iLin += 1
                    d[key] = ast.literal_eval(value)
                else:
                    s = (value[value.find('[') + 1: value.rfind(']')]).strip()
                    numAsStr = s.split(',')
                    val = []
                    for num in numAsStr:
                        # We need to use numpy.float64 here for the comparison to work
                        val.append(numpy.float64(num))
                    r[key] = val
            except ValueError as detail:
                s = "%s could not be parsed.\n" % refFilNam
                self._reporter.writeError(s)
                raise TypeError(detail)
            iLin += 1
        d['results'] = r

        return d

    def _askNoReferenceResultsFound(self, yS, refFilNam, ans):
        """ Ask user what to do if no reference data were found
           :param yS: A list where each element is a dictionary of variable names and simulation
                      results that are to be plotted together.
           :param refFilNam: Name of reference file (used for reporting only).
           :param ans: A previously entered answer, either ``y``, ``Y``, ``n`` or ``N``.
           :return: A triple ``(updateReferenceData, foundError, ans)`` where ``updateReferenceData``
                    and ``foundError`` are booleans, and ``ans`` is ``y``, ``Y``, ``n`` or ``N``.

        """
        updateReferenceData = False
        foundError = False

        # For OCT verification, always write new reference results

        if self._OCT_VERIFICATION:
            return (True, foundError, True)

        if len(yS) > 0:
            sys.stdout.write(
                "*** Warning: The old reference data had no results, but the new simulation produced results\n")
            sys.stdout.write("             for %s\n" % refFilNam)
            sys.stdout.write("             Accept new results?\n")
            while not (ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                ans = input("             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")
            if ans == "y" or ans == "Y":
                # update the flag
                updateReferenceData = True
        return (updateReferenceData, foundError, ans)

    def _check_statistics(self, old_res, y_tra, stage, foundError, newStatistics, model_name):
        """ Checks the simulation or translation statistics and return
            `True` if there is a new statistics, or a statistics is no longer present, or if `newStatistics == True`.
        """
        import os

        def _compare_statistics(stage, key, model_name):
            """ Function that returns true if model should be compared.
                This is a fix for Dymola 2022 because for some models, the initialization statistics
                changes from one translation to another due to a linear system switching from one to two.
                """
            if stage != 'initialization' or key != 'nonlinear':
                return True
            # If BUILDINGSPY_SKIP_STATISTICS_VERIFICATION is present, skip verification of the models
            # that are listed in this environment variable
            if 'BUILDINGSPY_SKIP_STATISTICS_VERIFICATION' in os.environ:
                if model_name in os.environ['BUILDINGSPY_SKIP_STATISTICS_VERIFICATION']:
                    print(
                        f"Excluding {model_name} from comparison of initialization statistics and result comparison on Travis CI.")
                    return False
            return True

        r = newStatistics
        if 'statistics-%s' % stage in old_res:
            # Found old statistics.
            # Check whether the new results have also such a statistics.
            if stage in y_tra:
                # Check whether it changed.
                for key in old_res['statistics-%s' % stage]:
                    if key in y_tra[stage]:
                        if _compare_statistics(stage, key, model_name) and not self.are_statistics_equal(
                                old_res['statistics-%s' % stage][key], y_tra[stage][key]):
                            if foundError:
                                self._reporter.writeWarning("%s: Translation statistics for %s and results changed for %s.\n Old = %s\n New = %s"
                                                            % (model_name, stage, key, old_res['statistics-%s' % stage][key], y_tra[stage][key]))
                            else:
                                self._reporter.writeWarning("%s: Translation statistics for %s changed for %s, but results are unchanged.\n Old = %s\n New = %s"
                                                            % (model_name, stage, key, old_res['statistics-%s' % stage][key], y_tra[stage][key]))

                            r = True
                    else:
                        self._reporter.writeWarning("%s: Found translation statistics for %s for %s in old but not in new results.\n Old = %s"
                                                    % (model_name, stage, key, old_res['statistics-%s' % stage][key]))
                        r = True
                for key in y_tra[stage]:
                    if key not in old_res['statistics-%s' % stage]:
                        self._reporter.writeWarning(
                            "%s: Found translation statistics for key %s in %s in new but not in old results." %
                            (model_name, key, stage))
                        r = True
            else:
                # The new results have no such statistics.
                self._reporter.writeWarning(
                    "%s: Found translation statistics for %s in old but not in new results." %
                    (model_name, stage))
                r = True
        else:
            # The old results have no such statistics.
            if stage in y_tra:
                # The new results have such statistics, hence the statistics changed.
                self._reporter.writeWarning(
                    "%s: Found translation statistics for %s in new but not in old results." %
                    (model_name, stage))
                r = True
        return r

    def _compareResults(self, data_idx, oldRefFulFilNam, y_sim, y_tra, refFilNam, ans):
        """ Compares the new and the old results.

            :param matFilNam: Matlab file name.
            :param oldRefFilFilNam: File name including path of old reference files.
            :param y_sim: A list where each element is a dictionary of variable names and simulation
                           results that are to be plotted together.
            :param y_tra: A dictionary with the translation statistics.
            :param refFilNam: Name of the file with reference results (used for reporting only).
            :param ans: A previously entered answer, either ``y``, ``Y``, ``n`` or ``N``.
            :param model_name: Model name, used for reporting.
            :return: A triple ``(updateReferenceData, foundError, ans)`` where ``updateReferenceData``
                     and ``foundError`` are booleans, and ``ans`` is ``y``, ``Y``, ``n`` or ``N``.

        """
        matFilNam = self._data[data_idx]['ResultFile']
        model_name = self._data[data_idx]['model_name']

        # Reset answer, unless it is set to Y or N
        if not (ans == "Y" or ans == "N"):
            ans = "-"
        updateReferenceData = False
        # If previously the user chose to update all reference data, then
        # we set updateReferenceData = True
        if ans == "Y":
            updateReferenceData = True
        newTrajectories = False

        # Load the old data (in dictionary format)
        old_results = self._readReferenceResults(oldRefFulFilNam)
        # Numerical results of the simulation
        y_ref = old_results['results']

        if len(y_ref) == 0:
            return self._askNoReferenceResultsFound(y_sim, refFilNam, ans)

        # The old data contains results
        t_ref = y_ref.get('time')

        # If a simulation was requested, compare the results.
        if self._data[data_idx][self._modelica_tool]['simulate']:
            # Iterate over the pairs of data that are to be plotted together
            timOfMaxErr = dict()
            noOldResults = []  # List of variables for which no old results have been found

            list_var_ref = [el for el in y_ref.keys() if not re.search('time', el, re.I)]
            list_var_sim = [
                el for gr in y_sim for el in gr.keys() if not re.search(
                    'time', el, re.I)]
            for var in list_var_ref:  # reference variables not available in simulation results
                if var not in list_var_sim:
                    idx = self._init_comp_info(model_name, matFilNam)
                    # We skip warning considering it is only the case for x variables against which y variables
                    # are plotted.
                    self._update_comp_info(idx, var, None, False, 0, 'skip', data_idx)

            # List that collects errors for this case. This allows to report only one error if multiple trajectories
            # are not matching from a single simulation.
            errors = []
            for pai in y_sim:
                t_sim = pai['time']

                # The time interval is the same for the stored and the current data.
                # Check the accuracy of the simulation.
                for varNam in list(pai.keys()):
                    # Iterate over the variable names that are to be plotted together
                    if varNam != 'time':
                        if varNam in y_ref:
                            # Check results
                            if self._isParameter(pai[varNam]):
                                t = [min(t_sim), max(t_sim)]
                            else:
                                t = t_sim

                            # Compare times series.
                            (res, timMaxErr, error) = self.areResultsEqual(
                                t_ref, y_ref[varNam], t, pai[varNam], varNam, data_idx
                            )

                            if error:
                                errors.append(error)
                            if not res:
                                newTrajectories = True
                                timOfMaxErr[varNam] = timMaxErr
                        else:
                            # There is no old data series for this variable name
                            errors.append(f"Did not find variable {varNam} in old results.")
                            newTrajectories = True
                            noOldResults.append(varNam)
            if len(errors) > 0:
                self._reporter.writeError(
                    "{}: Errors during result verification.\n           {}".format(
                        refFilNam, '\n           '.join(errors)))
        # Compare the simulation statistics
        # There are these cases:
        # 1. The old reference results have no statistics, in which case new results may be written.
        # 2. The old reference results have statistics, and they are the same or different.
        # Statistics of the simulation model
        newStatistics = False
        if self._modelica_tool == 'dymola':
            for stage in ['initialization', 'simulation']:
                # Updated newStatistics if there is a new statistic. The other
                # arguments remain unchanged.
                newStatistics = self._check_statistics(
                    old_results, y_tra, stage, newTrajectories, newStatistics, model_name)

        # If the users selected "Y" or "N" (to not accept or reject any new results) in previous tests,
        # or if the script is run in batch mode, then don't plot the results.
        # If we found an error, plot the results, and ask the user to accept or
        # reject the new values.
        if (newTrajectories or newStatistics) and (not self._batch) and (
                not ans == "N") and (not ans == "Y"):
            if newTrajectories and newStatistics:
                print(f"{self._color_ERROR}             For {refFilNam},")
                print(
                    f"             update reference files with new {self._color_BOLD}statistics and trajectories{self._color_ERROR}?{self._color_ENDC}")
            elif newStatistics:
                print(f"{self._color_WARNING}             For {refFilNam},")
                print(
                    f"             update reference files with new {self._color_BOLD}statistics{self._color_WARNING}?{self._color_ENDC}")
            else:
                print(f"{self._color_ERROR}             For {refFilNam},")
                print(
                    f"             update reference files with new {self._color_BOLD}trajectories{self._color_ERROR}?{self._color_ENDC}")

            if newTrajectories:
                if self._comp_tool == 'legacy':
                    print("(Close plot window to continue.)")
                    self._legacy_plot(y_sim, t_ref, y_ref, noOldResults, timOfMaxErr, matFilNam)
                else:
                    self._funnel_plot(model_name)

            while not (ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                ans = input("             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")

            if ans == "y" or ans == "Y":
                # update the flag
                updateReferenceData = True

        return (updateReferenceData, (newTrajectories or newStatistics), ans)

    def _funnel_plot(self, model_name, browser=None):
        """Plot comparison results generated by pyfunnel."""

        idx = next(i for i, el in enumerate(self._comp_info) if el['model'] == model_name)
        comp_data = self._comp_info[idx]['comparison']
        dict_var_info = defaultdict(list)
        for iv, v in enumerate(comp_data['variables']):
            dict_var_info[v].append({'group': comp_data['var_groups'][iv],
                                     'dir': comp_data['funnel_dirs'][iv]})
        # Build a list of files to use for testing server request in pyfunnel.
        # We check whether these files are available in the file system.
        list_files = []
        for d in dict_var_info.values():
            if d[0]['dir'] is not None:
                for el in ['reference.csv', 'test.csv', 'errors.csv']:
                    file_path = os.path.join(d[0]['dir'], el)
                    if os.path.isfile(file_path):
                        list_files.append(file_path)
        # If no comparison results available in the file system, no plot.
        if len(list_files) == 0:
            return
        # Customize the plot.
        plot_title = comp_data['file_name']
        max_plot_per100 = 4
        height = 100 * \
            (1 + max(0, max(comp_data['var_groups']) - max_plot_per100) / max_plot_per100)
        err_plot_height = 0.18 * 100 / height
        # Populate the plot template.
        with open(self._PLOT_TEMPLATE, 'r') as f:
            template = f.read()
        content = re.sub(r'\$PAGE_TITLE', plot_title, template)
        content = re.sub(r'\$TITLE', plot_title, content)
        content = re.sub(r'\$DICT_VAR_INFO', json.dumps(dict_var_info), content)
        content = re.sub(r'\$HEIGHT', '{}%'.format(height), content)
        content = re.sub(r'\$ERR_PLOT_HEIGHT', str(err_plot_height), content)
        # Launch the local server.
        server = pyfunnel.MyHTTPServer(('', 0), pyfunnel.CORSRequestHandler,
                                       str_html=content, url_html='funnel')
        # Start the browser instance.
        server.browse(list_files, browser=browser)

    def _legacy_plot(self, y_sim, t_ref, y_ref, noOldResults, timOfMaxErr, model_name):
        """Plot comparison results generated by legacy comparison algorithm."""

        import matplotlib.pyplot as plt
        nPlo = len(y_sim)
        iPlo = 0
        plt.clf()
        for pai in y_sim:
            iPlo += 1
            plt.subplot(nPlo, 1, iPlo)
            # Iterate over the variable names that are to be plotted together
            color = ['k', 'r', 'b', 'g', 'c', 'm']
            iPai = -1
            t_sim = pai['time']
            for varNam in list(pai.keys()):
                iPai += 1
                if iPai > len(color) - 1:
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
                    if varNam in y_ref:
                        if self._isParameter(y_ref[varNam]):
                            # for parameters, don't just draw a dot, as these are hard to see as
                            # they are on the box
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
            leg.get_frame().set_alpha(0.5)  # transparent legend
            plt.xlabel('time')
            plt.grid(True)
            if iPlo == 1:
                plt.title(model_name)

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
        self._figSize = gcf.get_size_inches()

    def are_statistics_equal(self, s1, s2):
        """ Compare the simulation statistics `s1` and `s2` and
            return `True` if they are equal, or `False` otherwise.

        """
        x = s1.strip()
        y = s2.strip()
        if x == y:
            return True
        # If they have a comma, such as from 1, 20, 1, 14, then split it,
        # sort it, and compare the entries for equality

        def g(s): return s.replace(" ", "").split(",")
        # Sort and remove 0, as we are not interested in these equations because
        # they are solved explicitely
        sp1 = [x for x in sorted(g(x)) if x != '0']
        sp2 = [x for x in sorted(g(y)) if x != '0']
        # If the list have different lengths, they are not equal
        if len(sp1) != len(sp2):
            return False
        # They are of equal lengths, compare each element
        for i in range(len(sp1)):
            if sp1[i] != sp2[i]:
                return False

        return True

    def _compare_and_rewrite_fmu_dependencies(
            self,
            new_dependencies,
            reference_file_path,
            reference_file_name,
            ans):
        """ Compares whether the ``.fmu`` dependencies have been changed.
            If they are the same, this function does nothing.
            If they do not exist in the reference results, it askes to generate them.
            If they differ from the reference results, it askes whether to accept the new ones.

            :param new_dependencies: A dictionary with the new dependencies.
            :param reference_file_path: Path to the file with reference results.
            :param reference_file_name: Name of the file with reference results.
            :param ans: A previously entered answer, either ``y``, ``Y``, ``n`` or ``N``.
            :return: A tuple consisting of a boolean ``updated_reference_data`` and the value of ``ans``.

        """
        # Absolute path to the reference file
        abs_ref_fil_nam = os.path.join(reference_file_path, reference_file_name)
        # Put dependencies in data format needed to write to the reference result file
        y_tra = dict()
        y_tra['fmu-dependencies'] = new_dependencies

        # Check whether the reference results exist.
        if not os.path.exists(abs_ref_fil_nam):
            if not self._OCT_VERIFICATION:
                print("Warning ***: Reference file {} does not yet exist.".format(reference_file_name))
                while not (ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                    print("             Create new file?")
                    ans = input("             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")
            else:
                ans = "Y"

            if ans == "y" or ans == "Y":
                self._writeReferenceResults(abs_ref_fil_nam, None, y_tra)
                if not self._OCT_VERIFICATION:
                    # Avoid verbose output during OCT_VERIFICATION
                    self._reporter.writeOutput("Wrote new reference file %s." %
                                               reference_file_name)
            else:
                self._reporter.writeError("Did not write new reference file %s." %
                                          reference_file_name)
            return [True, ans]

        # The file that may contain the reference results exist.
        old_dep = self._readReferenceResults(abs_ref_fil_nam)
        # Check whether it contains a key 'statistics-fmu-dependencies'
        if 'statistics-fmu-dependencies' in old_dep:
            # Compare the statistics for each section
            found_differences = False
            for typ in ['InitialUnknowns', 'Outputs', 'Derivatives']:
                if old_dep['statistics-fmu-dependencies'][typ] != new_dependencies[typ]:
                    print(
                        "*** Warning: Reference file {} has different FMU statistics for '{}'.".format(reference_file_name, typ))
                    found_differences = True
            if found_differences:
                while not (ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                    print("             Rewrite file?")
                    ans = input("             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")
                if ans == "y" or ans == "Y":
                    self._writeReferenceResults(abs_ref_fil_nam, None, y_tra)
                    self._reporter.writeWarning(
                        "*** Warning: Rewrote reference file %s due to new FMU statistics." %
                        reference_file_name)
            return [found_differences, ans]

        else:
            # The old file has no statistics. Ask to rewrite it.
            print("*** Warning: Reference file {} has no FMU statistics.".format(reference_file_name))
            while not (ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                print("             Rewrite file?")
                ans = input("             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")
            if ans == "y" or ans == "Y":
                self._writeReferenceResults(abs_ref_fil_nam, None, y_tra)
                self._reporter.writeWarning(
                    "*** Warning: Rewrote reference file %s as the old one had no FMU statistics." %
                    reference_file_name)
            return [True, ans]

    def _check_fmu_statistics(self, ans):
        """ Check the fmu statistics from each regression test and compare it with the previously
            saved statistics stored in the library home folder.
            If the statistics differs,
            show a warning message containing the file name and path.
            If there is no statistics stored in the reference results in the library home folder,
            ask the user whether it should be generated.

            This function returns 1 if the statistics differ, or if the ``.fmu`` file
            is not found. The function returns 0 if there were no problems.
        """
        import buildingspy.fmi as fmi

        retVal = 0
        # Check if the directory
        # "self._libHome\\Resources\\ReferenceResults\\Dymola" exists, if not
        # create it.
        refDir = os.path.join(self._libHome, 'Resources', 'ReferenceResults', 'Dymola')
        if not os.path.exists(refDir):
            os.makedirs(refDir)

        for data in self._data:
            # Name of the reference file, which is the same as that matlab file name but with another extension.
            # Only check data for FMU exort.
            if data['dymola']['exportFMU']:
                # Convert 'aa/bb.mos' to 'aa_bb.txt'
                mosFulFilNam = os.path.join(self.getLibraryName(), data['ScriptFile'])
                mosFulFilNam = mosFulFilNam.replace(os.sep, '_')
                refFilNam = os.path.splitext(mosFulFilNam)[0] + ".txt"
                fmu_fil = os.path.join(data['ResultDirectory'],
                                       self.getLibraryName(), data['dymola']['FMUName'])
                try:
                    # Get the new dependency
                    dep_new = fmi.get_dependencies(fmu_fil)
                    # Compare it with the stored results, and update the stored results if
                    # needed and requested by the user.
                    [updated_reference_data, ans] = self._compare_and_rewrite_fmu_dependencies(
                        dep_new, refDir, refFilNam, ans)
                    # Reset answer, unless it is set to Y or N
                    if not (ans == "Y" or ans == "N"):
                        ans = "-"
                    if updated_reference_data:
                        retVal = 1

                except UnicodeDecodeError as e:
                    em = "UnicodeDecodeError: {}.\n".format(e)
                    em += "Output file of " + data['ScriptFile'] + " is excluded from unit tests.\n"
                    em += "The model appears to contain a non-asci character\n"
                    em += "in the comment of a variable, parameter or constant.\n"
                    em += "Check " + data['ScriptFile'] + " and the classes it instantiates.\n"
                    self._reporter.writeError(em)
                except IOError as e:
                    em = "IOError({0}): {1}.\n".format(e.errno, e)
                    em += "Output file of " + data['ScriptFile'] + \
                        " is excluded from unit tests because\n"
                    em += "the file " + fmu_fil + " does not exist\n."
                    self._reporter.writeError(em)
        return retVal

    def _get_optimica_warnings(self, error_text, model):
        """ Return a list with all OPTIMICA warnings
        """
        import re

        def _search_in_string(lin, lis, k, v):
            # JModelica/ThirdParty/MSL/Modelica/Media/package.mo has errorneous each
            # which we skip in our testing
            if ("Ignoring erroneous 'each' for the modification ' = reference_X'" in lin) or \
                    ("Ignoring erroneous 'each' for the modification ' = fill(0,0)'" in lin) or \
                    ("""Ignoring erroneous 'each' for the modification ' = {","}'""" in lin):
                return
            # Ignore warnings of the form Iteration variable "der(xxx)" is missing start value!
#            if re.search(r"""Iteration variable "der\(\S|.\)" is missing start value!""", lin):
#                break
            if v['tool_message'] in lin:
                # Found a warning. Report it to the reporter, and add it to the list that will be written to
                # the json file.
                #                  self._reporter.writeWarning(v["model_message"].format(model))
                msg = lin.strip(' \n')
                self._reporter.writeWarning("{}: {}".format(model, msg))
                lis.append(msg)
                self._error_dict.increment_counter(k)
            return

        lis = list()
        # Search for all warnings
        for k, v in list(self._error_dict.get_dictionary().items()):
            # Search in each line of the error file
            if self._modelica_tool == 'openmodelica':
                for lin in error_text.split('\n'):
                    _search_in_string(lin, lis, k, v)
            else:
                for lin in error_text:
                    _search_in_string(lin, lis, k, v)
        # Return a dictionary with all warnings
        return lis

    def _get_openmodelica_simulation_record(self, simulation_text):
        """ Return total number of Jacobian evaluations, state events, and elapsed cpu time
            when unit tests are run with OpenModelica
        """
        struct = [
            {"key": 'jacobians',
             'pattern': r"(\d+) evaluations of jacobian",
             'val': 0},
            {"key": 'state_events',
             'pattern': r"(\d+) state events",
             'val': 0},
            {"key": 'elapsed_time',
             'pattern': r"(\S+)s \[100.0%\] total",
             'val': 0}
        ]
        for ele in struct:
            r = re.search(ele['pattern'], simulation_text)
            if r is not None:
                ele['val'] = float(r.group(1)) if ele['key'] == 'elapsed_time' else r.group(1)
        res = {}
        for ele in struct:
            res[ele['key']] = ele['val']

        return res

    def _get_optimica_simulation_record(self, simulation_text):
        """ Return total number of Jacobian evaluations, state events, and elapsed cpu time
            when unit tests are run with OPTIMICA.
        """
        jacobianNumber = 0
        stateEvents = 0
        elapsedTime = 0
        for lin in simulation_text:
            if ("Number of Jacobian evaluations" in lin):
                temp = lin.split(":")
                jacobianNumber = int(temp[1].strip())
            if ("Number of state events" in lin):
                temp = lin.split(":")
                stateEvents = int(temp[1].strip())
            if ("Elapsed simulation time" in lin):
                temp = lin.split(":")
                temp1 = temp[1].split()
                elapsedTime = float(temp1[0])
        res = {'jacobians': jacobianNumber,
               'state_events': stateEvents,
               'elapsed_time': elapsedTime}
        return res

    def _verify_non_dymola_runs(self):
        """ Check the results of the OPTIMICA tests.

            This function returns 0 if no errors occurred,
            or a positive non-zero number otherwise.
        """
        iTra = 0
        iSim = 0
        iOmiSim = 0
        # Iterate over directories
        all_res = []
        for d in self._temDir:
            # Iterate over json files
            # The python file have names such as class_class_class.py
            for fil in glob.glob("{}{}*_*.py".format(d, os.path.sep)):
                # Check if there is a corresponding json file
                json_name = fil.replace(".py", "_buildingspy.json")
                if not os.path.exists(json_name):
                    em = "Did not find {}. Is the program properly installed?".format(json_name)
                    stdOutFil = os.path.abspath('stdout')
                    if os.path.exists(stdOutFil):
                        with open(stdOutFil, 'r', encoding="utf-8-sig") as tem:
                            for lin in tem:
                                em = em + "**** stdout file: {}\n".format(lin)
                            em = em + "**** end of stdout file\n"
                    self._reporter.writeError(em)
                    iTra = iTra + 1
                else:
                    with open(json_name, 'r', encoding="utf-8-sig") as json_file:
                        res = json.load(json_file)
                        # Get warnings from stdout that was captured from the compilation
                        if 'stdout' in res['translation']:
                            warnings = self._get_optimica_warnings(
                                error_text=res['translation']['stdout'],
                                model=res['model'])
                            res['translation']['warnings'] = warnings
                            # We don't need the stdout anymore, which can be long.
                            del res['translation']['stdout']

                        # Get number of Jacobian evaluations from stdout that was captured from
                        # the simulation
                        if 'stdout' in res['simulation']:
                            if self._modelica_tool == 'openmodelica':
                                jmRecord = self._get_openmodelica_simulation_record(
                                    simulation_text=res['simulation']['stdout'])
                            else:
                                jmRecord = self._get_optimica_simulation_record(
                                    simulation_text=res['simulation']['stdout'])
                            res['simulation']['jacobians'] = jmRecord['jacobians']
                            res['simulation']['state_events'] = jmRecord['state_events']
                            res['simulation']['elapsed_time'] = jmRecord['elapsed_time']
                            # We don't need the stdout anymore, which can be long.
                            del res['simulation']['stdout']
                        # Set the working_directory in the dictionary, which is used for error
                        # reporting
                        res['working_directory'] = d

                        all_res.append(res)
                        if not res['translation']['success']:
                            em = f"Translation of {res['model']} failed: '{res['translation']['exception']}'. Directory is '{res['working_directory']}'."
                            self._reporter.writeError(em)
                            iTra = iTra + 1
                        elif not res['simulation']['success']:
                            # Check if simulation was omitted based configuration.
                            if 'message' in res['simulation'] and \
                               res['simulation']['message'] == 'No simulation requested.':
                                # Write a message, except if this model is for FMU export only
                                # Get the info from the data structure that has the experiment
                                # specification.
                                mustExportFMU = False
                                model_name = res['model']
                                for ele in self._data:
                                    if ele['model_name'] == model_name:
                                        if ele['dymola']['exportFMU']:
                                            mustExportFMU = True
                                            break
#                               The models that are not simulated are already reported.
#                                if not mustExportFMU:
#                                    # This is a model that usually should be simulated,
#                                    # and not only a model that need to be exported as an FMU
#                                    print("*** Did not simulate {}".format(res['model']))
#                                    iOmiSim = iOmiSim + 1
                            else:
                                em = f"Simulation of {res['model']} failed: '{res['simulation']['exception']}'. Directory is '{res['working_directory']}'."
                                self._reporter.writeError(em)
                                iSim = iSim + 1

        # Merge all_res, which has the messages from the translation and simulation, with self._data
        # This allows to check when processing self._data whether the simulation was successful
        for res in all_res:
            model_name = res['model']
            for dat in self._data:
                if dat['model_name'] == model_name:
                    dat[self._modelica_tool]['translation'] = res['translation']
                    dat[self._modelica_tool]['simulation'] = res['simulation']
                    break

        # Write all results to simulator log file
        with open(self._simulator_log_file, 'w', encoding="utf-8-sig") as sim_log:
            sim_log.write("{}\n".format(json.dumps(all_res, indent=2, sort_keys=True)))

        retVal = self._writeSummaryMessages()

        if iTra > 0:
            print("\nNumber of models that failed translation                     : {}".format(iTra))
        if iSim > 0:
            print("\nNumber of models that translated but failed simulation       : {}".format(iSim))
        if iOmiSim > 0:
            print("\nNumber of models that configuration excluded from simulation : {}".format(iOmiSim))

        return retVal

    def _get_size_dir(self, start_path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size

    def _checkReferencePoints(self, ans):
        """ Check reference points from each regression test and compare it with the previously
            saved reference points of the same test stored in the library home folder.
            If all the reference points are not within a certain tolerance with the previous results,
            show a warning message containing the file name and path.
            If there is no ``.mat`` file of the reference points in the library home folder,
            ask the user whether it should be generated.

            This function returns ``1`` if reading reference results or reading the translation
            statistics failed. In this case, the calling method should not attempt to do
            further processing. The function returns ``0`` if there were no problems. In
            case of wrong simulation results, this function also returns ``0``, as this is
            not considered an error in executing this function.
        """
        # Check if the directory
        # "self._libHome\\Resources\\ReferenceResults\\Dymola" exists, if not
        # create it.
        refDir = os.path.join(self._libHome, 'Resources', 'ReferenceResults', 'Dymola')
        if not os.path.exists(refDir):
            os.makedirs(refDir)

        updateReferenceData = False
        ret_val = 0
        for data_idx, data in enumerate(self._data):
            # Index to self._comp_info
            # Models that only export an FMU have no field data['ResultFile']
            if 'ResultFile' in data:
                idx = self._init_comp_info(data['model_name'], data['ResultFile'])
            else:
                idx = self._init_comp_info(data['model_name'], None)
            # Only check data that need to be translated, simulated or exported as an FMU
            check_condition = \
                (self._isPresentAndTrue('translate', data[self._modelica_tool]) or
                    self._isPresentAndTrue('simulate', data[self._modelica_tool]) or
                    self._isPresentAndTrue('exportFMU', data[self._modelica_tool]))
            # Only if the simulation was successful are we reading the results.
            # (Simulation errors are reported earlier already.)

            if 'simulation' in data[self._modelica_tool]:
                check_condition = check_condition and data[self._modelica_tool]['simulation']['success']

            if check_condition:
                get_user_prompt = True
                # Convert 'aa/bb.mos' to 'aa_bb.txt'
                mosFulFilNam = os.path.join(self.getLibraryName(), data['ScriptFile'])
                mosFulFilNam = mosFulFilNam.replace(os.sep, '_')
                refFilNam = os.path.splitext(mosFulFilNam)[0] + ".txt"
                try:
                    # extract simulation results from the ".mat" file corresponding to "filNam"
                    warnings = []
                    errors = []
                    # Get the simulation results if a simulation was requested
                    y_sim = self._getSimulationResults(
                        data, warnings, errors) if data[self._modelica_tool]['simulate'] else None
                    # Get the translation statistics
                    if self._modelica_tool == 'dymola':
                        y_tra = self._getDymolaTranslationStatistics(data, warnings, errors)
                    else:
                        y_tra = None
                    for entry in warnings:
                        self._reporter.writeWarning(entry)
                    for entry in errors:
                        self._reporter.writeError(entry)
                    if len(errors) > 0:
                        # If there were errors when getting the results or translation statistics
                        # update self._comp_info to log errors and turn flags to return
                        list_var_ref = [el for gr in data['ResultVariables'] for el in gr]
                        for iv, var_ref in enumerate(list_var_ref):
                            if iv == 0:
                                self._update_comp_info(
                                    idx,
                                    var_ref,
                                    None,
                                    False,
                                    0,
                                    'Translation, simulation or extracting simulation results failed. {}'.format(
                                        '\n'.join(errors)),
                                    data_idx)
                            else:
                                self._update_comp_info(idx, var_ref, None, False, 0, '', data_idx)
                        # flags to return
                        ret_val = 1
                        get_user_prompt = False

                except UnicodeDecodeError as e:
                    em = "UnicodeDecodeError: {0}".format(e)
                    em += "Output file of " + data['ScriptFile'] + " is excluded from unit tests.\n"
                    em += "The model appears to contain a non-asci character\n"
                    em += "in the comment of a variable, parameter or constant.\n"
                    em += "Check " + data['ScriptFile'] + " and the classes it instantiates.\n"
                    self._reporter.writeError(em)
                else:
                    # if there was no error for this test case, check user feedback for result
                    if (get_user_prompt or self._OCT_VERIFICATION) and data[self._modelica_tool]['simulate']:
                        # Reset answer, unless it is set to Y or N, or
                        # unless the tests run in batch mode
                        if not (self._batch or ans == "Y" or ans == "N"):
                            ans = "-"
                            updateReferenceData = False
                        # check if reference results already exist in library
                        oldRefFulFilNam = os.path.join(refDir, refFilNam)
                        # If the reference file exists, and if the reference file contains
                        # results, compare the results.
                        if os.path.exists(oldRefFulFilNam):
                            # print('Found results for ' + oldRefFulFilNam)
                            # Note that y_sim is None if a model was requested to be not simulated.
                            [updateReferenceData, _, ans] = self._compareResults(
                                data_idx, oldRefFulFilNam, y_sim, y_tra, refFilNam, ans,
                            )
                        else:
                            # Reference file does not exist
                            if data[self._modelica_tool]['simulate']:
                                noOldResults = []
                                # add all names since we do not have any reference results yet
                                for pai in y_sim:
                                    t_ref = pai["time"]
                                    noOldResults = noOldResults + list(pai.keys())

                                if not (self._batch or ans == "Y" or ans == "N" or self._OCT_VERIFICATION):
                                    if t_ref is None:
                                        self._reporter.writeError(
                                            f"Test case {refFilNam} has no simulation output to compare. You need to add at least one variable to compare.")
                                    else:
                                        self._legacy_plot(y_sim, t_ref, {}, noOldResults, dict(),
                                                          "New results: " + data['ScriptFile'])
                                        # Reference file does not exist
                                        print(
                                            "*** Warning: Reference file {} does not yet exist.".format(refFilNam))
                                        while not (
                                                ans == "n" or ans == "y" or ans == "Y" or ans == "N"):
                                            print("             Create new file?")
                                            ans = input(
                                                "             Enter: y(yes), n(no), Y(yes for all), N(no for all): ")
                                        if ans == "y" or ans == "Y":
                                            updateReferenceData = True
                                        else:
                                            self._reporter.writeError(
                                                "Did not write new reference file %s." % oldRefFulFilNam)

                        if updateReferenceData or self._OCT_VERIFICATION and (y_tra is not None):
                            # If the reference data of any variable was updated.
                            # If run with self._OCT_VERIFICATION, if a simulation fails, y_tra is None
                            # but updateReferenceData is always true. Hence the check on y_tra.
                            # Make dictionary to save the results
                            self._writeReferenceResults(oldRefFulFilNam, y_sim, y_tra)
                            if not self._OCT_VERIFICATION:
                                # Avoid verbose output during OCT_VERIFICATION
                                self._reporter.writeOutput("Wrote new reference file %s." %
                                                           oldRefFulFilNam)

            else:
                # Tests that export FMUs do not have an output file. Hence, we do not warn
                # about these cases. Also, if the simulation failed, there is no need to report,
                # because simulation failures were already reported as an error earlier.
                if (self._modelica_tool == 'dymola' and not data['dymola']['exportFMU']):
                    # data['dymola']['simulation'] is not present for tests that are on the
                    # exclude list.
                    if 'simulation' in data['dymola']:
                        if self._isPresentAndTrue('success', data['dymola']['simulation']):
                            self._reporter.writeWarning(
                                "Output file of " +
                                data['ScriptFile'] +
                                " is excluded from result test.")

        # Write all results to comparison log file and inform user.
        with open(self._comp_log_file, 'w', encoding="utf-8-sig") as comp_log:
            comp_log.write("{}\n".format(json.dumps(self._comp_info, indent=2, sort_keys=True)))

        if self._comp_tool == 'funnel':
            s = """Comparison files output by funnel are stored in the directory '{}' of size {:.1f} MB.
Run 'python -c "import buildingspy.development.regressiontest as t; t.Tester(tool=\\\"{}\\\").report()"'
to access a summary of the comparison results.\n""".format(
                self._comp_dir, self._get_size_dir(self._comp_dir) * 1e-6, self._modelica_tool)
            self._reporter.writeOutput(s)

        return ret_val

    def _performTranslationErrorChecks(self, logFil, stat):
        with open(logFil, mode="rt", encoding="utf-8-sig") as fil:
            lines = fil.readlines()

        for k, v in list(self._error_dict.get_dictionary().items()):
            stat[k] = 0
            for line in lines:
                # use regex to extract first group and sum them in stat
                if 'is_regex' in v and v['is_regex']:
                    import re
                    m = re.search(v["tool_message"], line)
                    if m is not None:
                        stat[k] = stat[k] + int(m.group(1))
                # otherwise, default: count the number of line occurrences
                else:
                    if v["tool_message"] in line:
                        stat[k] = stat[k] + 1

        return stat

    def _checkSimulationError(self, errorFile):
        """ Check whether the simulation had any errors, and
            write the error messages to ``self._reporter``.
        """
        import json

        # Read the json file with the statistics
        if not os.path.isfile(self._statistics_log):
            raise IOError(
                "Statistics file {} does not exist.".format(
                    os.path.abspath(
                        self._statistics_log)))

        with open(self._statistics_log, mode="rt", encoding="utf-8-sig") as fil:
            try:
                stat = json.load(fil)['testCase']
            except ValueError as e:
                raise ValueError("Failed to parse {}.\n{}".format(self._statistics_log, str(e)))

        # Error counters
        iChe = 0
        iCom = 0
        iSim = 0
        iFMU = 0

        # Header for dump file
        with open(self._failed_simulator_log_file, "w") as f:
            f.write("Automatically generated BuildingsPy dump file for failed translations.\n\n")

        # Check for errors
        hasTranslationErrors = False
        for ele in stat:
            hasTranslationError = False
            if 'check' in ele and ele['check']['result'] is False:
                hasTranslationError = True
                iChe = iChe + 1
                self._reporter.writeError("Model check failed for '%s'." % ele["model"])
            if 'simulate' in ele and ele['simulate']['result'] is False:
                hasTranslationError = True
                iSim = iSim + 1
                self._reporter.writeError("Simulation failed for '%s'." %
                                          ele["simulate"]["command"])
            elif 'FMUExport' in ele and ele['FMUExport']['result'] is False:
                iFMU = iFMU + 1
                self._reporter.writeError("FMU export failed for '%s'." %
                                          ele["FMUExport"]["command"])

            # Check for problems.
            # First, determine whether we had a simulation or an FMU export
            if 'simulate' in ele:
                key = 'simulate'
            else:
                key = 'FMUExport'

            logFil = None
            if key in ele:
                if "translationLog" in ele[key]:
                    logFil = ele[key]["translationLog"]
                    ele[key] = self._performTranslationErrorChecks(logFil, ele[key])
                    for k, v in list(self._error_dict.get_dictionary().items()):
                        # For OPTIMICA, we neither have simulate nor FMUExport
                        if ele[key][k] > 0:
                            self._reporter.writeWarning(
                                v["model_message"].format(ele[key]["command"]))
                            self._error_dict.increment_counter(k)

            if hasTranslationError and logFil is not None:
                with open(self._failed_simulator_log_file, "a") as f:
                    f.write("===============================\n")
                    f.write("=====START OF NEW LOG FILE=====\n")
                    f.write("===============================\n")
                    if os.path.exists(logFil):
                        with open(logFil, "r") as f2:
                            f.write(f2.read())
                    else:
                        # Logfile does not exists, which may be because simulation was terminated
                        # due to time out
                        f.write(
                            f"Log file {logFil} does not exist, this can happen if the process was terminated due to time out.")
                    f.write("\n\n\n")

        if iChe > 0:
            print("Number of models that failed check                           : {}".format(iChe))
        if iSim > 0:
            print("Number of models that failed to simulate                     : {}".format(iSim))
        if iFMU > 0:
            print("Number of models that failed to export as an FMU             : {}".format(iFMU))
        if hasTranslationErrors:
            print(
                "Check or simulation failed, see {} for more details about the failed models.".format(
                    self._failed_simulator_log_file))
        return self._writeSummaryMessages()

    def _writeSummaryMessages(self, silent=True):
        """Write summary messages"""

        for _, v in list(self._error_dict.get_dictionary().items()):
            counter = v['counter']
            if counter > 0 and not silent:
                print(v['summary_message'].format(counter))

        if not silent:
            # Change console to color output
            nWar = self._reporter.getNumberOfWarnings()
            nErr = self._reporter.getNumberOfErrors()
            if nWar > 0 or nErr > 0:
                print(self._color_ERROR, end='')
            self._reporter.writeOutput(
                f"Script that runs unit tests had {nWar} warnings and {nErr} errors.\n")
            if nWar > 0 or nErr > 0:
                print(self._color_ENDC, end='')
            sys.stdout.write("See '{}' for details.\n".format(self._simulator_log_file))

        if self._reporter.getNumberOfErrors() > 0:
            retval = 1
        elif self._reporter.getNumberOfWarnings() > 0:
            retval = 2
        else:
            retval = 0
            if not silent:
                # Change console to color output
                print(self._color_OK, end='')
                self._reporter.writeOutput("Unit tests completed successfully.\n")
                print(self._color_ENDC, end='')
        sys.stdout.flush()

        return retval

    def get_number_of_tests(self):
        """ Returns the number of regression tests that will be run for the current library and configuration.

            Note: Needs to be run within the run method (where elements of self._data requiring no simulation
            are first removed).
        """
        return len(self._data)

    def printNumberOfClasses(self):
        """ Print the number of models, blocks and functions to the
            standard output stream
        """

        iMod = 0
        iBlo = 0
        iFun = 0
        for root, _, files in os.walk(self._libHome):
            pos = root.find('.svn' or '.git')
            # skip .svn folders
            if pos == -1:
                for filNam in files:
                    # find .mo files
                    pos = filNam.find('.mo')
                    if pos > -1 and (root.find('Examples') == -1 or root.find('Validation') == -1):
                        # find classes that are not partial
                        filFulNam = os.path.join(root, filNam)
                        iMod = self._checkKey("model", filFulNam, iMod)
                        iBlo = self._checkKey("block", filFulNam, iBlo)
                        iFun = self._checkKey("function", filFulNam, iFun)
        print("Number of models   : {!s}".format(iMod))
        print("          blocks   : {!s}".format(iBlo))
        print("          functions: {!s}".format(iFun))

    def _getModelCheckCommand(self, mosFilNam):
        """ Return lines that conduct a model check in pedantic mode.

        :param mosFilNam: The name of the ``*.mos`` file

        This function return a command of the form
        ``checkModel("Buildings.Controls.Continuous.Examples.LimPID")``
        """

        def get_model_name(mosFil, line):
            try:
                iSta = line.index('\"') + 1
                iEnd = line.index('\"', iSta)
                return line[iSta:iEnd]
            except ValueError as e:
                em = str(e) + "\n"
                em += "Did not find model name in '%s'\n" % mosFil
                self._reporter.writeError(em)
                raise ValueError(em)

        retVal = None
        with open(mosFilNam, mode="r+", encoding="utf-8-sig") as fil:
            for lin in fil:
                if "simulateModel" in lin or "modelToOpen" in lin:
                    if self._modelica_tool == 'dymola':
                        retVal = 'checkModel("{}")'.format(get_model_name(mosFilNam, lin))
                    elif self._modelica_tool == 'openmodelica':
                        retVal = "checkModel({})".format(get_model_name(mosFilNam, lin))
                    break
        return retVal

    def _removePlotCommands(self, mosFilNam):
        """Remove all plot commands from the mos file.

        :param mosFilNam: The name of the ``*.mos`` file

        This function removes all plot commands from the file ``mosFilNam``.
        This allows to work around a bug in Dymola 2012 which can cause an exception
        from the Windows operating system, or which can cause Dymola to hang on Linux.
        """
        with open(mosFilNam, mode="r+", encoding="utf-8-sig") as fil:
            lines = fil.readlines()
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
        with open(mosFilNam, mode="w", encoding="utf-8") as filWri:
            for i in range(len(linWri)):
                filWri.write(lines[linWri[i]])

    def _updateResultFile(self, mosFilNam, modelName):
        """
        Update the mos script to use ``matFilNam`` as the name of the result file.

        :param mosFilNam: The name of the ``*.mos`` file
        :param modelName: The name of the model

        This function updates in the ``mosFilNam`` the simulate command
        to use `modelName.mat` as the result file name.
        This ensures that each result file name is unique.
        """
        import re
        with open(mosFilNam, mode="r+", encoding="utf-8-sig") as fil:
            con = fil.read()
        count = 0
        (conNew, count) = re.subn(r"resultFile\s*=\s*\"(.+)\"",
                                  f"resultFile=\"{modelName}\"", con, count=count, flags=re.M)
        # Models with translateModelFMU have no result file. So these files are not written to disk
        if count > 0:
            with open(mosFilNam, mode="w", encoding="utf-8-sig") as fil:
                fil.write(conNew)

    @staticmethod
    def _isPresentAndTrue(key, dic):
        return key in dic and dic[key]

    def _write_runscript_dymola(self, iPro, tra_data_pro):
        """Create the run_modelName.mos scripts for the current processor iPro and for Dymola,
           and return the number of generated regression tests.

           :param iPro: The number of the processor.
           :param tra_data_pro: A list with the data for the experiments that require translation, for processor number iPro only.
        """
        import platform

        for tra_data in tra_data_pro:
            self._write_dymola_script(iPro, tra_data)

    def _write_dymola_script(self, iPro, tra_data):
        """Create the run_modelName.mos script for the current model and for Dymola,
           and return the number of generated regression tests.

           :param iPro: The number of the processor.
           :param tra_data: Data for the experiment that requires translation, for processor number iPro only.
        """
        import platform

        ##################################################################
        # Internal functions
        def _write_translation_stats(runFil, values):

            # Close the bracket for the JSON object
            runFil.write("""Modelica.Utilities.Streams.print("      }", """
                         + '"' + values['statisticsLog'] + '"' + ");\n")

        def _print_end_of_json(isLastItem, fileHandle, logFileName):
            if isLastItem:
                fileHandle.write(
                    "Modelica.Utilities.Streams.print(\"    }\", \"%s\")\n" % logFileName)
                fileHandle.write(
                    "Modelica.Utilities.Streams.print(\"  ]\", \"%s\")\n" % logFileName)
                fileHandle.write("Modelica.Utilities.Streams.print(\"}\", \"%s\")\n" % logFileName)
            else:
                fileHandle.write(
                    "Modelica.Utilities.Streams.print(\"  },\", \"%s\")\n" % logFileName)

        ##################################################################
        # Count the number of experiments that need to be simulated or exported as an FMU.
        # This is needed to properly close the json brackets.
#        nItem = 0
        # Count how many tests need to be simulated.
#        nTes = len(tra_data_pro)
        # Number of generated unit tests
#        nUniTes = 0

        statistics_log = f"{tra_data['model_name']}.statistics.log"
        runFil = open(os.path.join(self._temDir[iPro], self.getLibraryName(),
                                   f"run_{tra_data['model_name']}.mos"), mode="w", encoding="utf-8")
        runFil.write(
            f"""// File autogenerated for process {iPro + 1} of {self._nPro}
// File created for execution by {self._modelica_tool}. Do not edit.
// Disable parallel computing as this can give slightly different results.
Advanced.ParallelizeCode = false;
// Default values for options that can give slightly different results.
Evaluate=false;
Advanced.CompileWith64=2;
Advanced.EfficientMinorEvents=false;
// Set the pedantic Modelica mode
Advanced.PedanticModelica = {str(self._pedanticModelica).lower()};
orig_Advanced_GenerateVariableDependencies = Advanced.GenerateVariableDependencies;
Advanced.GenerateVariableDependencies = false;
""")
        # Deactivate DDE
        if platform.system() == "Windows":
            posDDE = "9"  # At position 9 DDE settings should be stored.
            runFil.write(f"""
// Deactivate DDE
(comp, sett) = GetDymolaCompiler();
DDE_orig = sett[{posDDE}];
sett[{posDDE}] = \"DDE=0\"; // Disable DDE
SetDymolaCompiler(comp, sett);
""")
        runFil.write('cd(\"{}/{}\");\n'.format(
            (self._temDir[iPro]).replace("\\", "/"),
            self.getLibraryName()))
        runFil.write(f"""
openModel("package.mo")
// Add a flag so that translation info appears in console output.
// This allows checking for numerical derivatives.
// Dymola will write this output to a file when savelog(filename) is called.
// However, the runtime log will be in dslog.txt.
Advanced.TranslationInCommandLog := true;
// Set flag to support string parameters, which is required for the weather
// data file.
//Modelica.Utilities.Files.remove(\"{self._simulator_log_file}\");
Modelica.Utilities.Files.remove(\"{statistics_log}\");
""")
        runFil.write(r"""
Modelica.Utilities.Streams.print("{\"testCase\" : [", "%s");
""" % statistics_log)

        # if self._isPresentAndTrue(
        #        'translate',
        #        tra_data['dymola']) or self._isPresentAndTrue(
        #        'exportFMU',
        #        tra_data['dymola']):
        #nItem = nItem + 1

#        iItem = 0
# Write unit tests for this process
# Check if this mos file should be simulated
        if self._isPresentAndTrue(
                'translate',
                tra_data['dymola']) or self._isPresentAndTrue(
                'exportFMU',
                tra_data['dymola']):
            isLastItem = True  # (iItem == nItem - 1)
            mosFilNam = os.path.join(self.getLibraryName(),
                                     "Resources", "Scripts", "Dymola",
                                     tra_data['ScriptFile'])
            absMosFilNam = os.path.join(self._temDir[iPro], mosFilNam)
            values = {
                "libraryName": self.getLibraryName(),
                "mosWithPath": mosFilNam.replace(
                    "\\",
                    "/"),
                "checkCommand": self._getModelCheckCommand(absMosFilNam).replace(
                    "\\",
                    "/"),
                "checkCommandString": self._getModelCheckCommand(absMosFilNam).replace(
                    '\"',
                    r'\\\"'),
                "scriptFile": tra_data['ScriptFile'].replace(
                    "\\",
                    "/"),
                "model_name": tra_data['model_name'].replace(
                    "\\",
                    "/"),
                "model_name_underscore": tra_data['model_name'].replace(
                    ".",
                    "_"),
                "start_time": tra_data['startTime'] if 'startTime' in tra_data else 0,
                "final_time": tra_data['stopTime'] if 'stopTime' in tra_data else 0,
                "statisticsLog": statistics_log,
                "translationLog": os.path.join(
                    self._temDir[iPro],
                    self.getLibraryName(),
                    tra_data['model_name'] +
                    ".translation.log").replace(
                    "\\",
                    "/"),
                "simulatorLog": self._simulator_log_file.replace(
                    "\\",
                    "/")}
            if 'FMUName' in tra_data['dymola']:
                values["FMUName"] = tra_data['dymola']['FMUName']
         # Delete command log, model_name.simulation.log and dslog.txt
            runFil.write(f"""
Modelica.Utilities.Files.remove(\"{values["model_name"]}.translation.log\");
Modelica.Utilities.Files.remove(\"dslog.txt\");
clearlog();
""")
        ########################################################################
        # Write line for model check
        model_name = values["model_name"]
        if model_name.startswith("Obsolete.", model_name.find(".") + 1):
            # This model is in IBPSA.Obsolete, or Buildings.Obsolete etc.
            values["set_non_pedantic"] = "Advanced.PedanticModelica = false;\n"
            values["set_pedantic"] = "Advanced.PedanticModelica = true;\n"
        else:  # Set to empty string as for non-obsolete models, we don't switch to non-pedantic mode
            values["set_non_pedantic"] = ""
            values["set_pedantic"] = ""
        template = r"""
{set_non_pedantic}
rCheck = {checkCommand};
{set_pedantic}
Modelica.Utilities.Streams.print("    {{ \"file\" :  \"{mosWithPath}\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("      \"model\" : \"{model_name}\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("      \"check\" : {{", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"command\" : \"{checkCommandString};\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"result\"  : " + String(rCheck), "{statisticsLog}");
Modelica.Utilities.Streams.print("      }},", "{statisticsLog}");
"""
        runFil.write(template.format(**values))
        ##########################################################################
        # Write commands for checking translation and simulation results.
        # Only translation requested, but no simulation.
        ##########################################################################
        if self._isPresentAndTrue(
                'translate',
                tra_data['dymola']) and not self._isPresentAndTrue(
                'simulate',
                tra_data['dymola']):
            template = r"""
{set_non_pedantic}
retVal = translateModel("{model_name}");
Modelica.Utilities.Streams.print("Translated {model_name} successfully: " + String(retVal));
{set_pedantic}
savelog("{model_name}.translation.log");
if Modelica.Utilities.Files.exist("dslog.txt") then
  Modelica.Utilities.Files.move("dslog.txt", "{model_name}.dslog.log");
end if;
iSuc=0;
if Modelica.Utilities.Files.exist("{model_name}.dslog.log") then
  iLin=1;
  endOfFile=false;
  while (not endOfFile) loop
    (_line, endOfFile)=Modelica.Utilities.Streams.readLine("{model_name}.dslog.log", iLin);
    iLin=iLin+1;
    iSuc=iSuc+Modelica.Utilities.Strings.count(_line, "Translated {model_name} successfully: true.");
  end while;
  Modelica.Utilities.Streams.close("{model_name}.dslog.log");
else
  Modelica.Utilities.Streams.print("{model_name}.dslog.log was not generated.", "{model_name}.log");
end if;
"""
            runFil.write(template.format(**values))
            template = r"""
Modelica.Utilities.Streams.print("      \"translate\" : {{", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"command\" :\"translateModel(\\\"{model_name}\\\");\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"translationLog\"  : \"{translationLog}\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"result\"  : " + String(iSuc > 0), "{statisticsLog}");
"""
            runFil.write(template.format(**values))
            _write_translation_stats(runFil, values)
            _print_end_of_json(isLastItem,
                               runFil,
                               statistics_log)
        # Simulation requested
        if self._isPresentAndTrue('simulate', tra_data['dymola']):
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
{set_non_pedantic}
rScript=RunScript("modelica://{libraryName}/Resources/Scripts/Dymola/{scriptFile}");
{set_pedantic}
savelog("{model_name}.translation.log");
if Modelica.Utilities.Files.exist("dslog.txt") then
  Modelica.Utilities.Files.move("dslog.txt", "{model_name}.dslog.log");
end if;
iSuc=0;
intTimRec="temp";
timRecCol=0;
timRecSpa=0;
intTim="0";
jacRec="temp";
jacRecCol=0;
jacRecLen=0;
numJac="0";
staRec="temp";
staRecCol=0;
staRecLen=0;
numSta="0";
if Modelica.Utilities.Files.exist("{model_name}.dslog.log") then
  iLin=1;
  endOfFile=false;
  while (not endOfFile) loop
    (_line, endOfFile)=Modelica.Utilities.Streams.readLine("{model_name}.dslog.log", iLin);
    iLin=iLin+1;
    iSuc=iSuc+Modelica.Utilities.Strings.count(_line, "Integration terminated successfully");
    if (Modelica.Utilities.Strings.find(_line, "CPU-time for integration") > 0) then
        intTimRec = _line;
    end if;
    if (Modelica.Utilities.Strings.find(_line, "Number of Jacobian-evaluations") > 0) then
        jacRec = _line;
    end if;
    if (Modelica.Utilities.Strings.find(_line, "Number of state events") > 0) then
        staRec = _line;
        break;
    end if;
  end while;
  if iSuc > 0 then
    if not Modelica.Utilities.Strings.isEqual(intTimRec,"temp") then
        timRecCol = Modelica.Utilities.Strings.find(intTimRec, ":");
        timRecSpa = Modelica.Utilities.Strings.findLast(intTimRec, " ");
        intTim = Modelica.Utilities.Strings.substring(intTimRec, timRecCol+1, timRecSpa-1);
    end if;
    if not Modelica.Utilities.Strings.isEqual(jacRec,"temp") then
        jacRecCol = Modelica.Utilities.Strings.find(jacRec, ":");
        jacRecLen = Modelica.Utilities.Strings.length(jacRec);
        numJac = Modelica.Utilities.Strings.substring(jacRec, jacRecCol+1, jacRecLen);
    end if;
    if not Modelica.Utilities.Strings.isEqual(staRec,"temp") then
        staRecCol = Modelica.Utilities.Strings.find(staRec, ":");
        staRecLen = Modelica.Utilities.Strings.length(staRec);
        numSta = Modelica.Utilities.Strings.substring(staRec, staRecCol+1, staRecLen);
    end if;
  end if;
  Modelica.Utilities.Streams.close("{model_name}.dslog.log");
else
  Modelica.Utilities.Streams.print("{model_name}.dslog.log was not generated.", "{model_name}.log");
end if;
"""
            runFil.write(template.format(**values))
            template = r"""
Modelica.Utilities.Streams.print("      \"simulate\" : {{", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"command\" : \"RunScript(\\\"modelica://{libraryName}/Resources/Scripts/Dymola/{scriptFile}\\\");\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"translationLog\"  : \"{translationLog}\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"elapsed_time\"  :" + intTim + ",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"jacobians\"  :" + numJac + ",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"state_events\"  :" + numSta + ",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"start_time\"  :" + String({start_time}) + ",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"final_time\"  :" + String({final_time}) + ",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"result\"  : " + String(iSuc > 0), "{statisticsLog}");
"""
            runFil.write(template.format(**values))
            _write_translation_stats(runFil, values)
            _print_end_of_json(isLastItem,
                               runFil,
                               statistics_log)
            ##########################################################################
            # FMU export
        if tra_data['dymola']['exportFMU']:
            template = r"""
Modelica.Utilities.Files.removeFile("{FMUName}");
RunScript("modelica://{libraryName}/Resources/Scripts/Dymola/{scriptFile}");
savelog("{model_name}.translation.log");
if Modelica.Utilities.Files.exist("dslog.txt") then
  Modelica.Utilities.Files.move("dslog.txt", "{model_name}.dslog.log");
end if;
iSuc=0;
if Modelica.Utilities.Files.exist("{model_name}.dslog.log") then
  iLin=1;
  endOfFile=false;
  while (not endOfFile) loop
    (_line, endOfFile)=Modelica.Utilities.Streams.readLine("{model_name}.dslog.log", iLin);
    iLin=iLin+1;
    iSuc=iSuc+Modelica.Utilities.Strings.count(_line, "Created {FMUName}");
  end while;
  Modelica.Utilities.Streams.close("{model_name}.dslog.log");
else
  Modelica.Utilities.Streams.print("{model_name}.dslog.log was not generated.", "{model_name}.log");
end if;
"""
            runFil.write(template.format(**values))
            template = r"""
Modelica.Utilities.Streams.print("      \"FMUExport\" : {{", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"command\" :\"RunScript(\\\"modelica://{libraryName}/Resources/Scripts/Dymola/{scriptFile}\\\");\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"translationLog\"  : \"{translationLog}\",", "{statisticsLog}");
Modelica.Utilities.Streams.print("        \"result\"  : " + String(iSuc > 0), "{statisticsLog}");
"""
            runFil.write(template.format(**values))
            _write_translation_stats(runFil, values)
            _print_end_of_json(isLastItem,
                               runFil,
                               statistics_log)

        if not (tra_data['dymola']['exportFMU']
                or tra_data['dymola']['translate']):
            print(
                "****** {} neither requires a simulation nor an FMU export.".format(tra_data['ScriptFile']))
        self._removePlotCommands(absMosFilNam)
        self._updateResultFile(absMosFilNam, tra_data['model_name'])
#        nUniTes = nUniTes + 1
#        iItem = iItem + 1

        if platform.system() == 'Windows':
            # Reset DDE to original settings
            runFil.write(f"""
// Reset DDE settings like before
    sett[{posDDE}] = DDE_orig;
    SetDymolaCompiler(comp, sett)
""")
        # Reset Advanced flag
        runFil.write("""
Advanced.GenerateVariableDependencies = orig_Advanced_GenerateVariableDependencies;
exit();
""")
        runFil.close()
        return

    def _write_runscripts(self):
        """Create the run_modelName.mos scripts, one per model.

        The commands in the script depend on the tool: 'openmodelica', 'dymola' or 'optimica'
        """
        nUniTes = 0

        # Build array of models that need to be translated, simulated, or exported as an FMU
        tra_data = []
        if self._modelica_tool == 'dymola':
            for dat in self._data:
                if self._isPresentAndTrue('translate', dat[self._modelica_tool]) or self._isPresentAndTrue(
                        'exportFMU', dat[self._modelica_tool]):
                    tra_data.append(dat)
        elif self._modelica_tool != 'dymola':
            for dat in self._data:
                if self._isPresentAndTrue('translate', dat[self._modelica_tool]):
                    tra_data.append(dat)
        else:
            raise RuntimeError("Tool is not supported.")

        # Count how many tests need to be translated.
        nTes = len(tra_data)
        # Reduced the number of processors if there are fewer examples than processors
        if nTes < self._nPro:
            self.setNumberOfThreads(nTes)

        # Print number of processors
        print(
            f"Using {self._nPro} of {multiprocessing.cpu_count()} processors to run unit tests for {self._modelica_tool}.")

        # Create temporary directories. This must be called after setNumberOfThreads.
        if not self._useExistingResults:
            self._setTemporaryDirectories()

        for iPro in range(self._nPro):
            for i in range(iPro, nTes, self._nPro):
                # Store ResultDirectory into data dict.
                tra_data[i]['ResultDirectory'] = self._temDir[iPro]
                # This directory must also be copied into the original data structure.
                found = False
                for k in range(len(self._data)):
                    if self._data[k]['ScriptFile'] == tra_data[i]['ScriptFile']:
                        self._data[k]['ResultDirectory'] = tra_data[i]['ResultDirectory']
                        found = True
                        break
                if not found:
                    raise RuntimeError(
                        f"Failed to find the original data for {tra_data[i]['ScriptFile']}")

        for iPro in range(self._nPro):

            tra_data_pro = []
            for i in range(iPro, nTes, self._nPro):
                # Copy data used for this process only.
                tra_data_pro.append(tra_data[i])

            if self._modelica_tool == 'dymola':
                # Case for dymola
                self._write_runscript_dymola(iPro, tra_data_pro)

            nUniTes = nUniTes + self._write_python_runscripts(iPro, tra_data_pro)
            self._write_run_all_script(iPro, tra_data_pro)

        if nUniTes == 0:
            raise RuntimeError(f"Wrong invocation, generated {nUniTes} unit tests.")

        print("Generated {} regression tests.\n".format(nUniTes))

    @staticmethod
    def _get_set_of_result_variables(list_of_result_variables):
        s = set()
        for ent in list_of_result_variables:
            for ele in ent:
                s.add(ele)
        return s

    def _write_run_all_script(self, iPro, tra_data_pro):
        """ Write the OpenModelica or OPTIMICA top-level runfile for all experiments in tra_data_pro.

        :param iPro: The number of the processor.
        :param tra_data_pro: A list with the data for the experiments that require translation, for this processor only.
        """
        import inspect
        import buildingspy.development.regressiontest as r
        import jinja2

        directory = self._temDir[iPro]

        path_to_template = os.path.dirname(inspect.getfile(r))
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(path_to_template))
        with open(os.path.join(directory, "run.py"), mode="w", encoding="utf-8") as fil:
            models_underscore = []
            for dat in tra_data_pro:
                models_underscore.append(dat['model_name'].replace(".", "_"))
            template = env.get_template("run_all.template")
            txt = template.render(models_underscore=sorted(models_underscore))
            # for the special case that no models need to be translated (for this process)
            # we need to add a python command. Otherwise the python file is not valid.
            if (len(tra_data_pro) == 0):
                txt += "   import os;\n"
            fil.write(txt)

    def _write_python_runscripts(self, iPro, tra_data_pro):
        """ Write the Python runfiles for all experiments in tra_data_pro.

        :param iPro: The number of the processor.
        :param tra_data_pro: A list with the data for the experiments that require translation, for this processor only.
        """
        import inspect
        import buildingspy.development.regressiontest as r
        import jinja2

        directory = self._temDir[iPro]

        path_to_template = os.path.dirname(inspect.getfile(r))
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(path_to_template))

        tem_mod = env.get_template("{}_run.template".format(self._modelica_tool))

        for dat in tra_data_pro:
            model = dat['model_name']
            # Filter the result variables
            if 'ResultVariables' in dat:
                result_variables = list(self._get_set_of_result_variables(dat['ResultVariables']))
            else:
                result_variables = list()
            # Set relative tolerance
            if 'rtol' not in dat[self._modelica_tool]:
                # User did not set tolerance, use the one from the .mo file
                if 'tolerance' in dat:
                    dat[self._modelica_tool]['rtol'] = dat['tolerance']
                else:
                    dat[self._modelica_tool]['rtol'] = 1E-6
            # Note that if dat[self._modelica_tool]['simulate'] == false, then only the FMU export is tested, but no
            # simulation should be done.
            # filter argument must respect glob syntax ([ is escaped with []]) + OPTIMICA mat file
            # stores matrix variables with no space e.g. [1,1].
            if self._modelica_tool == 'openmodelica':
                filter = '(' + '|'.join([re.sub(r'\[|\]',
                                                lambda m: '[{}]'.format(m.group()),
                                                re.sub(' ', '', x)) for x in result_variables]) + ')'
                txt = tem_mod.render(
                    library_name=self.getLibraryName(),
                    model=model,
                    working_directory=directory,
                    ncp=dat[self._modelica_tool]['ncp'],
                    rtol=dat[self._modelica_tool]['rtol'],
                    solver=dat[self._modelica_tool]['solver'],
                    simulate=dat[self._modelica_tool]['simulate'],
                    time_out=dat[self._modelica_tool]['time_out'],
                    filter=filter
                )
            elif self._modelica_tool == 'optimica':
                txt = tem_mod.render(
                    model=model,
                    ncp=dat[self._modelica_tool]['ncp'],
                    rtol=dat[self._modelica_tool]['rtol'],
                    solver=dat[self._modelica_tool]['solver'],
                    start_time='mod.get_default_experiment_start_time()',
                    final_time='mod.get_default_experiment_stop_time()',
                    simulate=dat[self._modelica_tool]['simulate'],
                    time_out=dat[self._modelica_tool]['time_out'],
                    generate_html_diagnostics=False,
                    debug_solver=False,
                    debug_solver_interactive_mode=False,
                    filter=[re.sub(r'\[|\]',
                                   lambda m: '[{}]'.format(m.group()),
                                   re.sub(' ', '', x)) for x in result_variables]
                )
            else:  # dymola
                # assemble command
                cmd = list()
                cmd.append(f"{self.getModelicaCommand()}")
                cmd.append(f"run_{model}.mos")
                if not self._showGUI:
                    cmd.append("/nowindow")

                txt = tem_mod.render(
                    model=model,
                    working_directory=os.path.join(directory, self.getLibraryName()),
                    library_name=self.getLibraryName(),
                    # ncp=dat[self._modelica_tool]['ncp'],
                    # rtol=dat[self._modelica_tool]['rtol'],
                    # solver=dat[self._modelica_tool]['solver'],
                    # start_time='mod.get_default_experiment_start_time()',
                    # final_time='mod.get_default_experiment_stop_time()',
                    # simulate=dat[self._modelica_tool]['simulate'],
                    time_out=dat[self._modelica_tool]['time_out'],
                    cmd=cmd
                )

            file_name = os.path.join(directory, "{}.py".format(model.replace(".", "_")))
            with open(file_name, mode="w", encoding="utf-8") as fil:
                fil.write(txt)

        # Copy python file that grabs the console output
        if self._modelica_tool == 'optimica':
            shutil.copyfile(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "simulate",
                    "OutputGrabber.py"),
                os.path.join(
                    directory,
                    "OutputGrabber.py"))

        return len(tra_data_pro)

    def deleteTemporaryDirectories(self, delete):
        """ Flag, if set to ``False``, then the temporary directories will not be deleted
        after the regression tests are run.

        :param delete: Flag, set to ``False`` to avoid the temporary directories to be deleted.

        Unless this method is called prior to running the regression tests with ``delete=False``,
        all temporary directories will be deleted after the regression tests.
        """
        self._deleteTemporaryDirectories = delete

    # Create the list of temporary directories that will be used to run the unit tests
    def _setTemporaryDirectories(self):
        self._temDir = []

        # Make temporary directory, copy library into the directory and
        # write run scripts to directory
        for iPro in range(self._nPro):
            # print("Calling parallel loop for iPro={}, self._nPro={}".format(iPro, self._nPro))
            dirNam = tempfile.mkdtemp(
                prefix='tmp-' + self.getLibraryName() + '-' + str(iPro) + "-")
            self._temDir.append(dirNam)
            # Directory that contains the library as a sub directory
            libDir = self._libHome

            shutil.copytree(
                libDir,
                os.path.join(
                    dirNam,
                    self.getLibraryName()),
                symlinks=True,
                ignore=shutil.ignore_patterns(
                    '.svn',
                    '.git',
                    '*.mat',
                    '*.log',
                    'request.',
                    'status.',
                    'dsmodel.c',
                    'dymosim',
                    'tmp-*',
                    'funnel-comp',
                    'fmi-library',  # Not all of src is excluded as some .mo models link to files from src
                    'Documentation',
                    'ReferenceResults',
                    'help',
                    'compareVars',
                    '__pychache__'))
        return

    def _run_simulation_info(self):
        """ Extract simulation data from statistics.json when run unit test with dymola
        """

        def _get(model, key, data):
            for ent in data:
                if ent['model_name'] == model:
                    return ent[key]
            return 0

        with open(self._statistics_log, 'r') as f:
            staVal = simplejson.loads(f.read())
        data = []
        for case in staVal['testCase']:
            if 'translate' in case:
                temp = {}
                temp['model'] = case['model']
                temp['translation'] = {}
                temp['translation']['success'] = case['translate']['result']
                data.append(temp)
            if 'simulate' in case:
                temp = {}
                temp['model'] = case['model']
                temp['simulation'] = {}
                temp['simulation']['elapsed_time'] = case['simulate']['elapsed_time'] if 'elapsed_time' in case['simulate'] else 0
                temp['simulation']['start_time'] = case['simulate']['start_time'] if 'start_time' in case['simulate'] else _get(
                    case['model'], 'startTime', self._data)
                temp['simulation']['final_time'] = case['simulate']['final_time'] if 'final_time' in case['simulate'] else _get(
                    case['model'], 'stopTime', self._data)
                temp['simulation']['jacobians'] = case['simulate']['jacobians'] if 'jacobians' in case['simulate'] else 0
                temp['simulation']['state_events'] = case['simulate']['state_events'] if 'state_events' in case['simulate'] else 0
                temp['simulation']['success'] = case['simulate']['result']
                data.append(temp)
        dataJson = simplejson.dumps(data)
        return dataJson

    def run(self):
        """ Run all regression tests and checks the results.

        :return: 0 if no errors and no warnings occurred during the regression tests,
                 otherwise a non-zero value.

        This method

        - creates temporary directories for each processors,
        - copies the directory ``CURRENT_DIRECTORY`` into these
          temporary directories,
        - creates run scripts that run all regression tests,
        - runs these regression tests,
        - collects the dymola log files from each process,
        - writes the combined log file ``unitTests-x.log``
          to the current directory, where `x` is the name of the
          Modelica tool,
        - for Dymola, compares the results of the new simulations with
          reference results that are stored in ``Resources/ReferenceResults``,
        - writes the message `Regression tests completed successfully.`
          if no error occurred,
        - returns 0 if no errors and no warnings occurred, or non-zero otherwise.

        """
        from sys import platform

        self.checkPythonModuleAvailability()

        if self.get_number_of_tests() == 0:
            self.setDataDictionary(self._rootPackage)

        # (Delete and) Create directory for storing funnel data.
        if self._comp_tool == 'funnel':
            shutil.rmtree(self._comp_dir, ignore_errors=True)
            os.makedirs(self._comp_dir)

        # Print number of classes
        self.printNumberOfClasses()

        # Reset the number of processors to use no more processors than there are
        # examples to be run
        self.setNumberOfThreads(min(multiprocessing.cpu_count(),
                                    self.get_number_of_tests(), self._nPro))

        retVal = 0
        # Start timer
        startTime = time.time()
        # Process command line arguments

        # Check if executable is on the path
        if not self._useExistingResults:
            exe_com = self.getModelicaCommand()
            if not self.isExecutable(exe_com):
                print("Error: Did not find executable '{}'".format(exe_com))
                return 3

        # Check current working directory
        if not self.isValidLibrary(self._libHome):
            print("*** {} is not a valid Modelica library.".format(self._libHome))
            print("*** The current directory is {}".format(os.getcwd()))
            print(
                "*** Expected directory {} ".format(
                    os.path.abspath(
                        os.path.join(
                            self._libHome,
                            "Resources",
                            "Scripts"))))
            print("*** Exit with error. Did not do anything.")
            return 2

        # Initialize data structure to check results
        self._initialize_error_dict()

        # Inform the user if regression tests are skipped
        if self._skip_verification:
            self._reporter.writeOutput(
                "Time series of simulation results will not be verified.")

        # Write the run scripts
        self._write_runscripts()

        # Run simulations
        tem_dir = []
        libNam = self.getLibraryName()
        for di in self._temDir:
            # if self._modelica_tool == 'dymola':
            #    tem_dir.append(os.path.join(di, libNam))
            # else:
            #    tem_dir.append(di)
            tem_dir.append(di)

        if not self._useExistingResults:
            if self._modelica_tool == 'dymola' or self._modelica_tool == 'openmodelica':
                # OS X invokes python 2.7 if the command below is python, despite of having
                # alias python=python3 in .bashrc.
                # Hence, we invoke python3 for OS X.
                # (The unit tests would fail with
                # invalid syntax for f"'{' '.join(cmd)}' caused '{msg}'.")
                if platform == "darwin":
                    cmd = ["python3", "./run.py"]
                else:
                    cmd = ["python", "./run.py"]
            else:
                cmd = [self.getModelicaCommand(), "run.py"]

            if self._nPro > 1:
                po = multiprocessing.Pool(self._nPro)
                po.map(functools.partial(runSimulation,
                                         cmd=cmd),
                       [x for x in tem_dir])
                po.close()
                po.join()
            else:
                if len(self._data) > 0:
                    runSimulation(tem_dir[0], cmd)

        # Concatenate simulator output files into one file
        with open(self._simulator_log_file, mode="w", encoding="utf-8") as logFil:
            for d in self._temDir:
                for temLogFilNam in glob.glob(
                    os.path.join(
                        d,
                        self.getLibraryName(),
                        '*.translation.log')):
                    if os.path.exists(temLogFilNam):
                        with open(temLogFilNam, mode="r", encoding="utf-8-sig") as fil:
                            data = fil.read()
                        logFil.write(data)
                    else:
                        self._reporter.writeError(
                            "Log file '" + temLogFilNam + "' does not exist.\n")
                        retVal = 1

        # Concatenate simulator statistics into one file
        if self._modelica_tool == 'dymola':
            with open(self._statistics_log, mode="w", encoding="utf-8") as logFil:
                stat = list()
                for d in self._temDir:
                    for temLogFilNam in glob.glob(
                            os.path.join(d, self.getLibraryName(), '*.statistics.log')):
                        if os.path.exists(temLogFilNam):
                            with open(temLogFilNam.replace('Temp\tmp', 'Temp\\tmp'), mode="r", encoding="utf-8-sig") as temSta:
                                try:
                                    jsonLog = json.load(temSta)
                                    cas = jsonLog["testCase"]
                                    # Iterate over all test cases of this output file
                                    for ele in cas:
                                        stat.append(ele)
                                except json.decoder.JSONDecodeError as e:
                                    # If a run timed out, then temLogFilNam is not a valid json file
                                    # because the file is written on the fly, and dymola did not finish
                                    # writing all of it, which results in an invalid file.
                                    # Check if /tmp/tmp-Buildings-1-o_m7nj7p/Buildings_Examples_VAVReheat_ASHRAE2006_buildingspy.json
                                    # exists
                                    modelName = os.path.split(temLogFilNam)[
                                        1].replace('.statistics.log', '')
                                    buiLogNam = os.path.join(
                                        d,
                                        f"{modelName.replace('.', '_')}_buildingspy.json")
                                    if os.path.exists(buiLogNam):
                                        # Read the log file of the python script that invoked dymola
                                        with open(buiLogNam, mode="r", encoding="utf-8-sig") as buiLog:
                                            jsonBui = json.load(buiLog)
                                            # Build up the entry for reporting the case
                                            if "simulation" in jsonBui and "exception" in jsonBui["simulation"]:
                                                exception = ''.join(
                                                    jsonBui['simulation']['exception'])
                                            else:
                                                exception = f"JSONDecodeError in {temLogFilNam}: {str(e)}"
                                            ele = {
                                                "model": modelName,
                                                "simulate": {
                                                    "command": ''.join(
                                                        jsonBui['simulation']['cmd']),
                                                    "result": False,
                                                    "exception": exception}}
                                            self._reporter.writeError(
                                                f"Model '{modelName}' failed: {exception}")
                                            stat.append(ele)
                                            # Add the failure also to self._data so that
                                            # _checkReferencePoints is not trying to read the
                                            # output.
                                            for ele in self._data:
                                                if ele['model_name'] == modelName:
                                                    if "simulation" in ele[self._modelica_tool]:
                                                        ele[self._modelica_tool]['simulation']['success'] = False
                                                    else:
                                                        ele[self._modelica_tool]['simulation'] = {
                                                            'success': False}
                                    else:
                                        self._reporter.writeError(
                                            f"Decoding '{temLogFilNam}' failed and '{buiLogNam}' does not exist: {e}")
                                        raise
                                except ValueError as e:
                                    self._reporter.writeError(
                                        "Loading '%s' failed: %s" % (temLogFilNam, e))
                                    raise
                        else:
                            self._reporter.writeError(
                                "Log file '" + temLogFilNam + "' does not exist.\n")
                            retVal = 1
                # Dump an array of testCase objects
                # dump to a string first using json.dumps instead of json.dump
                json_string = json.dumps({"testCase": stat},
                                         ensure_ascii=False,
                                         indent=4,
                                         separators=(',', ': '),
                                         sort_keys=True)
                logFil.write(json_string)

        # Check reference results
        if self._batch:
            ans = "N"
        elif self._OCT_VERIFICATION:
            ans = "Y"
        else:
            ans = "-"

        if self._modelica_tool == 'dymola':
            retVal = self._check_fmu_statistics(ans) if not self._OCT_VERIFICATION else 0
            if retVal != 0:
                retVal = 4

            if retVal == 0:
                retVal = self._checkSimulationError(self._simulator_log_file)
            else:
                self._checkSimulationError(self._simulator_log_file)

            if not self._skip_verification:
                # For Dymola: store available simulation info into
                # self._comp_info used for reporting.
                val = self._run_simulation_info()
                self._comp_info = simplejson.loads(val)

                r = self._checkReferencePoints(ans)
                if r != 0:  # In case of comparison error. Comparison warnings are handled
                    if retVal != 0:  # We keep the translation or simulation error code.
                        pass
                    else:
                        retVal = 4

        if self._modelica_tool != 'dymola':
            temp = self._verify_non_dymola_runs()

            if retVal == 0:
                retVal = temp

            if not self._skip_verification:
                # For OpenModelica and OPTIMICA: store available translation and simulation info
                # into self._comp_info used for reporting.
                with open(self._simulator_log_file, 'r') as f:
                    self._comp_info = simplejson.loads(f.read())

                r = self._checkReferencePoints(ans='N')
                if r != 0:
                    if retVal != 0:  # We keep the translation or simulation error code.
                        pass
                    else:
                        retVal = 4

        # Update exit code after comparing with reference points
        # and print summary messages.
        if retVal == 0:
            retVal = self._writeSummaryMessages(silent=False)
        else:  # We keep the translation or simulation error code.
            self._writeSummaryMessages(silent=False)

        # Delete temporary directories, or write message that they are not deleted
        for d in self._temDir:
            if self._deleteTemporaryDirectories:
                shutil.rmtree(d)
            else:
                print("Did not delete temporary directory {}".format(d))

        # Print time
        elapsedTime = time.time() - startTime
        print("Execution time = {:.3f} s".format(elapsedTime))

        # Delete statistics file
        if self._modelica_tool == 'dymola':
            os.remove(self._statistics_log)

        return retVal

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
