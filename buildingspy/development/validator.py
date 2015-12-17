#!/usr/bin/env python
#######################################################
# Class that validates the .mo file for correct
# html syntax
#
# MWetter@lbl.gov                            2013-05-31
#######################################################


class Validator:
    ''' Class that validates ``.mo`` files for the correct html syntax.
    '''
    def __init__(self):
        import os

        # --------------------------
        # Class variables
#        self._libHome=os.path.abspath(".")
        self._writeHTML = False

    def validateHTMLInPackage(self, rootDir):
        '''
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

        '''
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

    def _validateHTML(self, moFile):
        '''
        This function validates the file ``moFile`` for correct html syntax.

        :param moFile: The name of a Modelica source file.
        :return: (str, str) The tidied markup [0] and warning/error
                 messages[1]. Warnings and errors are returned
                 just as tidylib returns them.

        '''
        from tidylib import tidy_document
        # Open file.
        f = open(moFile, "r")
        lines = f.readlines()
        f.close()
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
        nLin = len(lines)
        isTagClosed = True
        body = ""
        for i in range(nLin):
            if isTagClosed:
                # search for opening tag
                idxO = lines[i].find("<html>")
                if idxO > -1:
                    # search for closing tag on same line as opening tag
                    idxC = lines[i].find("</html>")
                    if idxC > -1:
                        body += lines[i][idxO+6:idxC] + '\n'
                        isTagClosed = True
                    else:
                        body += lines[i][idxO+6:] + '\n'
                        isTagClosed = False
            else:
                # search for closing tag
                idxC = lines[i].find("</html>")
                if idxC == -1:
                    # closing tag not found, copy full line
                    body += lines[i] + '\n'
                else:
                    # found closing tag, copy beginning of line only
                    body += lines[i][0:idxC] + '\n'
                    isTagClosed = True
                    body += "<h4>Revisions</h4>\n"
                    # search for opening tag on same line as closing tag
                    idxO = lines[i].find("<html>")
                    if idxO > -1:
                        body += lines[i][idxO+6:] + '\n'
                        isTagClosed = False

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
            f = open(htmlName, "w")
            f.write(document)
            f.close()
        return (document, errors)
