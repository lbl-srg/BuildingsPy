#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################
# Class that validates the .mo file for correct
# html syntax and checks the consistency of
# experiment annotation in .mo with the .mos files.
#
#######################################################
import os
import re


class Validator(object):
    """ Class that validates ``.mo`` files for the correct html syntax.
    """

    def __init__(self):

        # --------------------------
        # Class variables
        # self._libHome=os.path.abspath(".")
        self._writeHTML = False

    def validateHTMLInPackage(self, rootDir):
        """
        This function recursively validates all ``.mo`` files
        in a package.

        If there is malformed html code in the ``info`` or the
        ``revision`` section,
        then this function write the error message of tidy to the
        standard output.

        Note that the line number correspond to an intermediate format
        (e.g., the output format of tidy), which may be different from
        the ``.mo`` file.

        :param rootDir: The root directory of the package.
        :return: str[] Warning/error messages from tidylib.

        Usage: Type
            >>> import os
            >>> import buildingspy.development.validator as v
            >>> val = v.Validator()
            >>> myMoLib = os.path.join(\
                    "buildingspy", "tests", "MyModelicaLibrary")
            >>> # Get a list whose elements are the error strings
            >>> errStr = val.validateHTMLInPackage(myMoLib)

        """
        import os
        errMsg = list()

        # Make sure that the parameter rootDir points to a Modelica package.
        topPackage = os.path.join(rootDir, "package.mo")
        if not os.path.isfile(topPackage):
            raise ValueError("Argument rootDir=%s is not a \
Modelica package. Expected file '%s'."
                             % (rootDir, topPackage))

        for root, _, files in os.walk(rootDir):
            for moFil in files:
                # find the .mo file
                if moFil.endswith('.mo'):
                    moFulNam = os.path.join(root, moFil)
                    err = self._validateHTML(moFulNam)[1]
                    if len(err) > 0:
                        # We found an error. Report it to the console.
                        # This may later be changed to use an error handler.
                        errMsg.append("[-- %s ]\n%s" % (moFulNam, err))
        return errMsg

    def _getInfoRevisionsHTML(self, moFile):
        """
        This function returns a list that contain the html code of the
        info and revision sections. Each element of the list
        is a string.

        :param moFile: The name of a Modelica source file.
        :return: list The list of strings of the info and revisions
                 section.
        """

        with open(moFile, mode="r", encoding="utf-8") as f:
            lines = f.readlines()

        nLin = len(lines)
        isTagClosed = True
        entries = list()

        for i in range(nLin):
            if isTagClosed:
                # search for opening tag
                idxO = lines[i].find("<html>")
                if idxO > -1:
                    # search for closing tag on same line as opening tag
                    idxC = lines[i].find("</html>")
                    if idxC > -1:
                        entries.append(lines[i][idxO + 6:idxC])
                        isTagClosed = True
                    else:
                        entries.append(lines[i][idxO + 6:])
                        isTagClosed = False
            else:
                # search for closing tag
                idxC = lines[i].find("</html>")
                if idxC == -1:
                    # closing tag not found, copy full line
                    entries.append(lines[i])
                else:
                    # found closing tag, copy beginning of line only
                    entries.append(lines[i][0:idxC])
                    isTagClosed = True
                    entries.append("<h4>Revisions</h4>\n")
                    # search for opening tag on same line as closing tag
                    idxO = lines[i].find("<html>")
                    if idxO > -1:
                        entries.append(lines[i][idxO + 6:])
                        isTagClosed = False
        return entries

    def _validateHTML(self, moFile):
        """
        This function validates the file ``moFile`` for correct html syntax.

        :param moFile: The name of a Modelica source file.
        :return: (str, str) The tidied markup [0] and warning/error
                 messages[1]. Warnings and errors are returned
                 just as tidylib returns them.

        """
        from tidylib import tidy_document

        entries = self._getInfoRevisionsHTML(moFile)

        # Document header
        header = "<?xml version='1.0' encoding='utf-8'?> \n \
        <!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\" \n \
    \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd\"> \n \
<html xmlns=\"http://www.w3.org/1999/xhtml\"> \n \
<head> \n \
<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" /> \n \
<title>xxx</title> \n \
</head> \n \
<body> \n \
<!-- +++++++++++++++++++++++++++++++++++++ -->\n"

        body = ""
        for line in entries:
            body += line + '\n'
        # Replace \" with "
        body = body.replace('\\"', '"')

        # Document footer
        footer = "<!-- +++++++++++++++++++++++++++++++++++++ -->\n \
</body>\n \
</html>"

        # Validate the string
        document, errors = tidy_document(r"%s%s%s" % (header, body, footer),
                                         options={'numeric-entities': 1,
                                                  'output-html': 1,
                                                  'alt-text': '',
                                                  'wrap': 72})
        # Write html file.
        if self._writeHTML:
            htmlName = "%s%s" % (moFile[0:-2], "html")
            with open(htmlName, mode="w", encoding="utf-8") as f:
                f.write(document)
        return (document, errors)

    def _recursive_glob(self, rootdir='.', suffix=''):
        """
        Return all files with given extension.

        :param rootdir: Root directory.
        :param suffix: File extension.
        :return: List of files with given extension.


         """

        return [os.path.join(rootdir, filename) for rootdir, dirnames,
                filenames in os.walk(rootdir) for filename in filenames
                if (filename.endswith(suffix) and
                    ("ConvertBuildings_from" not in filename))]

    def _check_experiment(self, name, val, value, model_path, mos_file):
        """
        Check experiment annotation parameters in mo file.

        :param name: Parameter name.
        :param val: Value found in mo file.
        :param value: Value found in mos file.
        :param model_path: Path to mo file.
        :param mos_file: Path to mos file.

         """

        if("*" in str(val)):
            s = (
                "Found mo file=" +
                str(model_path) +
                " with experiment annotation " +
                self._capitalize_first(name) +
                ".\n" +
                self._capitalize_first(name) +
                " contains invalid expressions such as x * y. Only literal expressions are allowed " +
                "by OPTIMICA, JModelica and OpenModelica unit tests.\n")
            raise ValueError(s)

        delta = abs(eval(val) - eval(value))

        if (delta > 0):
            s = ("Found mo file={!s} with experiment annotation {!s}.\n" +
                 "The value of {!s}={!s} is different from the (default) value={!s}" +
                 " found in the mos file={!s}.\n").format(model_path,
                                                          self._capitalize_first(name),
                                                          self._capitalize_first(name),
                                                          val, value, mos_file)
            raise ValueError(s)

    def _missing_parameter(self, name, value, model_path, mos_file):
        """
        Check missing experiment annotation parameter in mo file.

        :param name: Parameter name.
        :param value: Value found in mos file.
        :param model_path: Path to mo file.
        :param mos_file: Path to mos file.

         """

        s = (
            "Found mo file={!s} without parameter {!s} defined.\n" +
            "The parameter name {!s} is defined in the mos file={!s}" +
            " with the value {!s}. It must hence be defined in the mo file.\n").format(
            model_path,
            self._capitalize_first(name),
            name,
            mos_file,
            value)
        raise ValueError(s)

    def _capitalize_first(self, name):
        """
        Capitalize the first letter of the given word.
        Return a word with first letter capitalized.

        :param name: Word to be capitalized.
        :return: Word with first letter capitalized.

         """
        lst = [word[0].upper() + word[1:] for word in name.split()]
        return " ".join(lst)

    def _missing_experiment_stoptime(self, mos_files):
        """
        Check missing experiment and StopTime annotation in mo file.
        Return number of mo files with experiment.

        :param mos_files: List of mos files.

         """

        n_mo_files = 0
        for mos_file in mos_files:
            mos_path = os.path.join(os.sep, 'Resources', 'Scripts', 'Dymola')
            model_path = mos_file.replace(mos_path, "")
            model_path = model_path.replace(".mos", ".mo")
            fm = open(model_path, "r", encoding="utf8")

            model_content = fm.readlines()
            Nlines = len(model_content)

            foundExp = False
            foundStop = False
            for i in range(Nlines - 1, 0, -1):
                line = model_content[i]
                if "experiment(" in line.replace(" ", ""):
                    foundExp = True
                    n_mo_files += 1
                if "StopTime=" in line.replace(" ", ""):
                    foundStop = True
            if (not foundExp):
                s = ("Found mo file={!s} without experiment annotation.\n").format(model_path)
                raise ValueError(s)
            if (not foundStop):
                s = ("Found mo file={!s} without StopTime in experiment annotation.\n").format(
                    model_path)
                raise ValueError(s)

            # close and exit
            fm.close()
        return n_mo_files

    def _separate_mos_files(self, mos_files):
        """
        Return number of files with tolerance parameter
        and two lists of mos files file, one with the simulateModel
        and the other one with the translateModelFMU command.

        :param mos_files: file path.
        :return: Number of files with tolerance parameter,
                and two lists of mos files file, one with the simulateModel
                and the other one with the translateModelFMU command.

         """

        mos_non_fmus = []
        mos_fmus = []

        n_tols = 0
        n_fmus = 0
        n_sim = 0

        for itr in mos_files:
            found_sim = False
            found_tol = False
            f = open(itr, "r", encoding="utf8")
            content = f.readlines()
            i = 0
            while i < len(content):
                l = content[i]
                if "tolerance=1" in (l.replace(" ", "")).lower():
                    found_tol = True
                    n_tols += 1
                if "simulateModel(" in l.replace(" ", ""):
                    n_sim += 1
                    found_sim = True
                    mos_non_fmus.append(itr)
                elif ("translateModelFMU" in l):
                    n_fmus += 1
                    mos_fmus.append(itr)
                i += 1
            f.close()

            if (found_sim and not found_tol):
                s = (
                    "Found mos file={!s} without tolerance defined.\n" +
                    "A minimum tolerance of 1e-6 is required for OPTIMICA and JModelica.\n").format(itr)
                raise ValueError(s)

        return n_tols, mos_non_fmus, mos_fmus

    def _check_tolerance(self, content, name, value, mos_file):
        """
        Check value of tolerance in file.

        :param content: file content.
        :param name: variable name.
        :param value: variable value.
        :param mos_file: mos file.

         """

        if (name + "=" == "tolerance=" and float(value) > 1e-6):
            self._wrong_parameter(mos_file, name, value)

    def _wrong_parameter(self, mos_file, name, value):
        """
        Stop if invalid parameter is found.

        :param mos_file: mos file.
        :param name: parameter name.
        :param value: parameter value.

         """

        if (name + "=" == "tolerance="):
            if value is None:
                s = (
                    "Found mos file={!s} without tolerance specified.\n" +
                    "A minimum tolerance of 1e-6 is required for OPTIMICA and JModelica for unit tests.\n").format(mos_file)
                raise ValueError(s)
            else:
                if(float(value) > 1e-6):
                    s = ("Found mos file={!s} with tolerance={!s}.\n"
                         "The tolerance found is bigger than 1e-6, the maximum required by "
                         "OPTIMICA and JModelica for unit tests.\n").format(mos_file, value)
                    raise ValueError(s)

        if (name + "=" == "stopTime="):
            if value is None:
                s = (
                    "Found mos file={!s} without stopTime specified.\n" +
                    "A non-null stopTime is required by OpenModelica for unit tests.\n").format(mos_file)
                raise ValueError(s)

    def _getValue(self, name, line, fil_nam):
        """
        Get value of input parameter.

        :param name: Parameter name.
        :param line: Line with parameter name.
        :param fil_nam: File with parameter.

         """
        # Split the name
        value1 = line.split(name + "=")
        # Split the value with potential character
        value2 = value1[1].split(',')
        # Split the value with potential character
        value3 = value2[0].split(')')
        try:
            ev = eval(value3[0])
        except Exception as err:
            err = "{!s}. Invalid literal found in file {!s}.".format(err, fil_nam)
            raise ValueError(err)

        if name == "StartTime":
            # If it is smaller than -2147483648 and bigger than 2147483647, which are
            # the minimum and maximum 32 bit integers. These are used in
            # the CI testing of JModelica. Exceeding them will cause an integer overflow
            if isinstance(ev, int):
                if ev < -2147483648:
                    err = (
                        "Integer overflow: Integers can be -2147483648 to 2147483647, received {}.\n".format(ev) +
                        "Use floating point represenation in {!s}.".format(fil_nam))
                    raise ValueError(err)

        if name == "StopTime":
            # If it is smaller than -2147483648 and bigger than 2147483647, which are
            # the minimum and maximum 32 bit integers. These are used in
            # the CI testing of JModelica. Exceeding them will cause an integer overflow
            if isinstance(ev, int):
                if ev > 2147483647:
                    err = (
                        "Integer overflow: Integers can be -2147483648 to 2147483647, received {}.\n".format(ev) +
                        "Use floating point represenation in {!s}.".format(fil_nam))
                    raise ValueError(err)

        # Return the value found
        return value3[0]

    def _wrong_literal(self, mos_file, name):
        """
        Stop if invalid literal is found.

        :param mos_file: mos file.
        :param name: Parameter name.

         """

        s = (
            "Found mos file={!s} with invalid expression={!s}.\n" +
            "This is not allowed for cross validation with OPTIMICA and JModelica.\n").format(
            mos_file,
            name +
            '=' +
            name)
        raise ValueError(s)

    def _validate_experiment_setup(self, name, mos_files):
        """
        Validate experiment setup.

        :param name: Parameter name.
        :param mos_files: List of mos files.
        """

        N_mos_defect = 0

        j = 1
        for mos_file in mos_files:
            j += 1

            f = open(mos_file, "r", encoding="utf8")

            content = f.readlines()
            found = False
            i = 0
            while not found and i < len(content):
                l = content[i]
                if "simulateModel(" in l.replace(" ", ""):
                    line = l
                    found = True
                i += 1

            try:
                if name + "=" + name in line.replace(" ", ""):
                    value = name
                    self._wrong_literal(mos_file, name)

                if name + "=" in line.replace(" ", ""):
                    value = self._getValue(name, line.replace(" ", ""), mos_file)
                    self._check_tolerance(content, name, value, mos_file)
                else:
                    found = False
                    while not found and i < len(content):
                        line = content[i]
                        i += 1

                        if name + "=" in line.replace(" ", ""):
                            found = True
                            value = self._getValue(name, line.replace(" ", ""), mos_file)
                            self._check_tolerance(content, name, value, mos_file)
                        if name + "=" + name in line.replace(" ", ""):
                            value = name
                            self._wrong_literal(mos_file, name)
                    if not found:
                        if (name == "startTime"):
                            value = "0.0"
                        elif (name == "stopTime"):
                            value = "1.0"
                        elif(name == "tolerance"):
                            value = None
                            self._wrong_parameter(mos_file, name, value)

            except AttributeError:
                N_mos_defect += 1

            if value is not None and value != name:

                mos_path = os.path.join(os.sep, 'Resources', 'Scripts', 'Dymola')
                model_path = mos_file.replace(mos_path, "")
                model_path = model_path.replace(".mos", ".mo")
                fm = open(model_path, "r", encoding="utf8")

                model_content = fm.readlines()
                Nlines = len(model_content)

                found = False
                foundStopExp_mo = False
                foundStartExp_mo = False
                foundToleranceExp_mo = False

                for i in range(Nlines - 1, 0, -1):
                    line = model_content[i]
                    if "StopTime=" in line.replace(" ", ""):
                        foundStopExp_mo = True
                    if "StartTime=" in line.replace(" ", ""):
                        foundStartExp_mo = True
                    if "Tolerance=" in line.replace(" ", ""):
                        foundToleranceExp_mo = True

                # Check if attributes StartTime/startTime are defined in mos and mo
                if (name + "=" == "startTime=" and abs(eval(value)) > 0.0 and (not foundStartExp_mo)):
                    self._missing_parameter(name, value, model_path, mos_file)

                # Check if attributes StopTime/stopTime are defined in mos and mo
                if (name + "=" == "stopTime=" and abs(eval(value) - 1.0) >
                        0.0 and (not foundStopExp_mo)):
                    self._missing_parameter(name, value, model_path, mos_file)

                # Check if attributes Tolerance/tolerance are defined in mos and mo
                if (name + "=" == "tolerance=" and abs(eval(value)) >
                        0.0 and (not foundToleranceExp_mo)):
                    self._missing_parameter(name, value, model_path, mos_file)

                for i in range(Nlines - 1, 0, -1):
                    line = model_content[i]

                    # if the lines contains experiment stop time, replace it
                    if self._capitalize_first(name) + "=" in line.replace(" ", "") and not found:
                        val = self._getValue(self._capitalize_first(
                            name), line.replace(" ", ""), model_path)
                        self._check_experiment(name, val, value, model_path, mos_file)
                        found = True

                fm.close()
            elif value == name:
                self._wrong_literal(model_path, name)

            f.close()

    def validateExperimentSetup(self, root_dir):
        """
        Validate the experiment setup in ``.mo`` and ``.mos`` files.

        :param root_dir: Root directory.

         """

        # Make sure that the parameter root_dir points to a Modelica package.
        topPackage = os.path.join(root_dir, "package.mo")
        if not os.path.isfile(topPackage):
            s = ("Argument root_dir={!s} is not a Modelica package.\n" +
                 "Expected file={!s}.\n").format(root_dir, topPackage)
            raise ValueError(s)

        # Get the path to the mos files
        rootPackage = os.path.join(root_dir, 'Resources', 'Scripts', 'Dymola')

        # Get all mos files
        mos_files = self._recursive_glob(rootPackage, '.mos')

        # Split mos files which either contain simulateModel or translateModelFMU
        n_tols, mos_non_fmus, _ = self._separate_mos_files(mos_files)

        # Check if all .mo files contain experiment annotation
        n_mo_files = self._missing_experiment_stoptime(mos_non_fmus)

        # Validate model parameters
        for i in ["stopTime", "tolerance", "startTime"]:
            self._validate_experiment_setup(i, mos_non_fmus)

        if(n_tols != n_mo_files):
            s = ("The number of tolerances in the mos files={!s} does no match " +
                 "the number of mo files={!s}.\n").format(n_tols, n_mo_files)
            raise ValueError(s)
