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
        import multiprocessing
        import buildingspy.io.reporter as rep

        # --------------------------
        # Class variables
        self.__libHome=os.path.abspath(".")
        self.__nPro = multiprocessing.cpu_count()
        self.__batch = False

        # List of temporary directories that are used to validate the files
        self.__temDir = []
        self.__writeHTML = False

        # Flag to delete temporary directories.
#        self.__deleteTemporaryDirectories = True

#        self.__libraryName = os.getcwd().split(os.path.sep)[-1]
#        self.__reporter = rep.Reporter("validator.log")


    def validateHTMLInPackage(self, rootDir):
        ''' This function recursively validates all ``.mo`` files
            in a package.
            
            If there is malformed html code in the ``info`` section,
            then this function write the error message of tidy to the
            standard output.

            Note that the line number correspond to an intermediate format
            (e.g., the output format of tidy) which may be different from
            the ``.mo`` file.
            
            :param rootDir: The root directory of the package.
            
            '''
        import os
        scrPat = self.__libHome

        for root, dirs, files in os.walk(scrPat):
            for moFil in files:
                # find the .mo file
                pos=moFil.endswith('.mo')
                if pos > -1:
                    moFulNam = os.path.join(root, moFil)
                    doc, err = self.validateHTML(moFulNam)
                    if len(err) > 0:
                        # We found an error. Report it to the console.
                        # This may later be changed to use an error handler.
                        print "[-- %s ]" % moFulNam
                        print err


    def validateHTML(self, moFile):
        ''' This function validates the file ``moFile`` for correct html
            syntax
        
        :param moFile: The name of a Modelica source file.
        :return: (str, str): The tidied markup [0] and warning/error messages[1]. 
                             Warnings and errors are returned just as tidylib returns them.

        Usage: Type
           >>> import buildingspy.development.Validator as v; 
           >>> val = v.Validator(); 
           >>> doc, err = val.validateHTML('aaaa.mo'); 
           >>> print doc;
           >>> print err;
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
        firstHTML = True
        body=""
        for i in range(nLin):
            if firstHTML:
                idx = lines[i].find("<html>")
                if idx > -1:
                    body += lines[i][idx+6:]  + '\n'
                    firstHTML = False
            else:
                idx = lines[i].find("</html>")
                if idx == -1:
                    body += lines[i] + '\n'
                else:
                    body += lines[i][0:idx] + '\n'
                    firstHTML = True
                    body += "<h4>Revisions</h4>\n"
#                    break
        # Replace \" with "
        body = body.replace('\\"', '"')

       # Document footer
        footer = "<!-- +++++++++++++++++++++++++++++++++++++ -->\n \
</body>\n \
</html>"

        # Validate the string
        document, errors = tidy_document(r"%s%s%s" % (header, body, footer),
                                         options={'numeric-entities':1,
                                                  'output-html': 1,
                                                  'alt-text': '',
                                                  'wrap': 72})
        # Write html file.
        if self.__writeHTML:
            htmlName = "%s%s" % (moFile[0:-2], "html")
            f = open(htmlName, "w")
            f.write(document)
            f.close()
        return (document, errors)
