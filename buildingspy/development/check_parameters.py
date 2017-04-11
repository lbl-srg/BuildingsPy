#!/usr/bin/env python
###########################################################
# Script with functions to validate consistency
# between .mos files and .mo files.

# This script checks invalid expression (x*y) in 
# the experiment annotation of a Modelica model,
# In addition it checks if an experiment annotation exists
# in all Modelica models. 
# It checks if the parameters of experiment annotation is 
# consistent with the values defined in the mos script.
# It checks if each model has a tolerance less than 1e-6.
# It checks it the mos script contains expression such as
# startTime=startTime.
# If any of the checks fail, the script returns with an error.
#
# TSNouidui@lbl.gov                            2017-01-24
###########################################################
#

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import logging as log

log.basicConfig(filename='check_parameters.log', filemode='w',
                level=log.DEBUG, format='%(asctime)s %(message)s',
                datefmt='%m/%d/%Y %I:%M:%S %p')
stderrLogger = log.StreamHandler()
stderrLogger.setFormatter(log.Formatter(log.BASIC_FORMAT))
log.getLogger().addHandler(stderrLogger)

import os
import re
import sys

class Validator(object):
    ''' Class that validates ``.mo`` files for the correct syntax.
    '''
    def __init__(self):

        # --------------------------
        # Class variables
        self._rewriteModel = False

    def _recursive_glob(self, rootdir='.', suffix=''):
        return [os.path.join(rootdir, filename) for rootdir, dirnames,
                filenames in os.walk(rootdir) for filename in filenames 
                if (filename.endswith(suffix) 
                    and ("ConvertBuildings_from" not in filename)) ]    
    
    def _check_experiment(self, name, val, value, modelPath, mos_file):
        """ 
        Check experiment annotation in mo file.
    
        :param name: Parameter name.
        :param val: Value found in mo file.
        :param value: Value found in mos file.
        :param modelPath: Path to mo file.
        :param mos_file: Path to mos file.
    
         """
        
        if("*" in str(val)):
            log.error("Found mo_file: {!s} with **experiment** annotation: {!s} which contains the invalid expression: {!s}"
                      .format(modelPath, self._capitalize_first(name), str(val)))
            sys.exit(1)
    
        delta = abs(eval(val) - eval(value))
        
        if (delta!=0):
            log.error("Found mo_file: {!s} with **experiment** annotation: {!s}".format(modelPath, self._capitalize_first(name)))
            log.error("The value of {!s} is : {!s} which is different from the (default) value: {!s} found in the .mos file: {!s}."
                      .format(val, value, name, mos_file))
            sys.exit(1)
            
    def _missing_parameter(self, name, value, modelPath, mos_file):
        """ 
        Check experiment annotation in mo file.
    
        :param name: Parameter name.
        :param value: Value found in mos file.
        :param modelPath: Path to mo file.
        :param mos_file: Path to mos file.
    
         """
        
        
        log.error("Found mo_file: {!s} without experiment annotation **"+self._capitalize_first(name)+"**.".format(modelPath))
        log.error("The parameter **"+name+"** with value : {!s} is however defined in the .mos file {!s}.".format(value, mos_file)) 
        sys.exit(1)   
        
    def _capitalize_first(self, name):
        """ 
        Capitalize the first letter of the given word.
    
        :param name: Word to be capitalized.
    
         """
        lst = [word[0].upper() + word[1:] for word in name.split()]
        return " ".join(lst)
    
    def _write_file(self, mos_file, content):
        """ 
        Write new mos file.
    
        :param mos_file: mos file name.
        :param content: mos file content.
    
         """
        
        # Delete the old file
        # print( "\tDeleting the old mos script...")
        os.system("rm "+mos_file)
    
        # Create a new one with the same name
        fm = open(mos_file,"w")
    
        for line in content:
            fm.write(line)
    
        # close and exit
        fm.close()
        
    def _number_occurences(self, filPat, ext):
        """ 
        Count number of occurences of Tolerance=1.
    
        :param filPat: file path.
        :param ext: file extension.
    
         """
        
        mosCorrect = []
        
        n_files_tol = 0
        n_files_fmus = 0
        for itr in filPat:
            f = open(itr,"r")
            content = f.readlines()
            found = False
            i=0
            while found == False and i<len(content):
                l = content[i]
                if "tolerance=1" in l.lower():
                    found = True
                    n_files_tol += 1
                    if (ext=="mos"):
                        mosCorrect.append(itr)
                    break
                if (ext=="mos"):
                    if ("translateModelFMU" in l):
                        n_files_fmus += 1
                i += 1
            f.close()
        return n_files_tol, n_files_fmus, mosCorrect
    
    def _replace_content(self, content, name, value, para, foundStop):
        """ 
        Replace content to a file.
    
        :param content: file content.
        :param name: variable name.
        :param value: variable value.
        :param para: parameter value.
        :param foundStop: Flag to stop.
    
         """
    
        i=0
        while i < len(content):
            line = content[i]
            i += 1
            # Remove white spaces
            line.replace(" ", "")
            if ""+name+"="+"" in line.replace(" ", ""):
                newLine = line.replace(""+name+"="+"" + str(value), ""+name+"="+""+str(para))
                content[i-1] = newLine
                foundStop = True
                return foundStop, content
        
    
    def _replace_stoptime(self, content, name, value, foundStop):
        """ 
        Replace stopTime in file.
    
        :param content: file content.
        :param name: variable name.
        :param value: variable value.
        :param foundStop: Flag to stop.
    
         """
        # Delete the old file
        i=0
        while i < len(content):
            line = content[i]
            i += 1
            # Remove white spaces
            line.replace(" ", "")
            if "stopTime=" in line.replace(" ", ""):
                newLine = line.replace("stopTime" , ""+name+"="+"" + str(value) + ", stopTime")
                content[i-1] = newLine
                foundStop = True
                return foundStop, content
    
    def _replace_resultfile(self, content, name, value, foundStop):
        """ 
        Replace resultFile in file.
    
        :param content: file content.
        :param name: variable name.
        :param value: variable value.
        :param foundStop: Flag to stop.
    
         """
        # Delete the old file
        i=0
        while i < len(content):
            line = content[i]
            i += 1
            # Remove white spaces
            line.replace(" ", "")
            if "resultFile=" in line.replace(" ", ""):
                newLine = line.replace("resultFile" , ""+name+"="+"" + str(value) + ", resultFile")
                content[i-1] = newLine
                foundStop = True
                return foundStop, content
    
    def _check_tolerance(self, content, name, value, mos_file):
        """ 
        Replace tolerance in file.
    
        :param content: file content.
        :param name: variable name.
        :param value: variable value.
        :param mos_file: mos file.
    
         """
        if ("" + name + "=" + "" == "tolerance=" and float(value) > 1e-6):
            self._wrong_parameter (mos_file, name, value)
    #         foundStop = False
    #         consPar = "1e-6"
    #         foundStop, content = _replace_content(content, name, value, consPar, foundStop)
    #         _write_file(mos_file, content)    
    
    def _wrong_parameter (self, mos_file, name, value):
        """ 
        Stop if invalid parameter is found.
    
        :param mos_file: mos file.
        :param name: parameter name.
        :param value: parameter value.
    
         """
         
        if ("" + name + "=" + "" == "tolerance="):
            if(float(value)> 1e-6):
                #print("\t=================================")
                log.error("Found mos_file: {!s} with a tolerance={!s}).".format(mos_file, value))
                log.error("This tolerance is bigger than the maximum allowed tolerance of 1e-6.")
                log.error("A tolerance of 1e-6 or less is required for the JModelica verification.")
                sys.exit(1)
            elif(float(value)== 0.0):
                #log.error("\t=================================")
                log.info("Found mos_file: {!s} without **tolerance** specified.".format(mos_file))
                log.error("A tolerance of 1e-6 or less is required for the JModelica verification.")
                sys.exit(1)
        if ("" + name + "=" + "" == "stopTime="):
            if(float(value)== 0.0):
                #log.error("\t=================================")
                log.info("Found mos_file: {!s} without **stopTime** specified.".format(mos_file))
                log.error("A non-null **stopTime** is required for the JModelica verification.")
                sys.exit(1)
                
    def _wrong_literal (self, mos_file, name):
        """ 
        Stop if invalid literal is detected.
    
        :param mos_file: mos file.
        :param name: Parameter name.
    
         """
         
        #log.error("\t=================================")
        log.error("Found mos_file: {!s} with expression: {!s}.".format(mos_file, name+'='+name))
        log.error("This is not allowed for the JModelica verification.")  
        sys.exit(1)
    
    
    def _validate_model_parameters (self, name, mos_files, rootDir):
        """ 
        Fix parameter settings.
    
        :param name: Parameter name.
    
         """

        N_mos_defect=0
    
        j = 1
        for mos_file in mos_files:
            j += 1
            
            f = open(mos_file,"r")
            
            content = f.readlines()
            found = False
            i = 0
            while found == False and i<len(content):
                l = content[i]
                if "simulateModel(" in l:
                    line = l
                    found = True
                i += 1
            
            # Remove white spaces
            line.replace(" ", "")
            
            try:
                pModel    = re.compile('simulateModel\("([^\(|^"]+)[\S]*"')
                mModel    = pModel.match(line)
                modelName = mModel.group(1)
                if ""+name+"="+name+"" in line.replace(" ", ""):
                    value = ""+name+""
                    #print("\t=================================")
                    self._wrong_literal(mos_file ,name)
                   
                if ""+name+"="+"" in line.replace(" ", ""):
                    # pTime    = re.compile(r"[\d\S\s.,]*(stopTime=)([\d]*[.]*[\d]*[e]*[+|-]*[\d]*)")
                    pTime    = re.compile(r"[\d\S\s.,]*("+name+"=)([\d]*[.]*[\d]*[eE]*[+|-]*[\d]*[*]*[\d]*[.]*[\d]*[eE]*[+|-]*[\d]*)")
                    mTime    = pTime.match(line)
                    value = mTime.group(2)
                    self._check_tolerance(content, name, value, mos_file)     
                else:
                    # print("\tThe name is not in the simulation command row... go ahead")
                    found = False
                    while found == False and i<len(content):
                        line = content[i]
                        i += 1
                        # Remove white spaces
                        line.replace(" ", "")
                        
                        if ""+name+"="+"" in line.replace(" ", ""):
                            found = True
                            pTime    = re.compile(r"[\d\S\s.,]*("+name+"=)([\d]*[.]*[\d]*[eE]*[+|-]*[\d]*[*]*[\d]*[.]*[\d]*[eE]*[+|-]*[\d]*)[\S\s.,]*")
                            mTime    = pTime.match(line)
                            value = mTime.group(2)
                            self._check_tolerance(content, name, value, mos_file)  
                            #startTime = startTime[:-1]
                        if ""+name+"="+name+"" in line.replace(" ", ""):
                            value = ""+name+""
                            #print("\t=================================")
                            self._wrong_literal(mos_file, name)
                    if found == False:
                        if (name=="startTime"):
                            value = "0.0"
                        elif (name=="stopTime"):
                            #print("\t"+ name + " not found, defined the default stopTime=1.0")
                            value="1.0"
                        elif(name=="tolerance"):
                            #foundToleranceExp_mos = True
                            value="0.0"
                            self._wrong_parameter (mos_file, name, value)
    
            except AttributeError:
                #print("\tThe script does not contain the simulation command! Maybe it is a plot script...")
                value = "NA"
                N_mos_defect += 1
                
            if (""+name+"="+"" != "numberOfIntervals=" ):
                if value != "NA" and value != ""+name+"":   

                    mosPath=os.path.join(os.sep, 'Resources', 'Scripts', 'Dymola')
                    modelPath=mos_file.replace(mosPath, "")
                    modelPath = modelPath.replace(".mos", ".mo")
                    fm = open(modelPath,"r")
                    
                    modelContent = fm.readlines()
                    Nlines = len(modelContent)
                    
                    found = False
                    foundExp = False
                    foundStopExp_mo = False
                    foundStartExp_mo = False
                    foundToleranceExp_mo = False
                    for i in range(Nlines-1, 0, -1):
                        line = modelContent[i]
                        if "experiment(" in line.replace(" ", ""):
                            foundExp=True
                        if "StopTime=" in line.replace(" ", ""):
                            foundStopExp_mo=True
                        if "StartTime=" in line.replace(" ", ""):
                            foundStartExp_mo=True
                        if "Tolerance=" in line.replace(" ", ""):
                            foundToleranceExp_mo=True
                    
                    # Check if experiment annotation is defined  
                    if (not foundExp):
                        log.error("Found mo_file: {!s} without **experiment** annotation.".format(modelPath))
                        log.error("An **experiment** annotation is required in the .mo example file.")
                        log.error("The parameters of the **experiment** annotation must match the parameters of the .mos script: {!s}."
                                  .format(mos_file))
                        sys.exit(1)
                    
                    # Check if attributes StartTime/startTime are defined in mos and mo                    
                    if (""+name+"="+"" == "startTime=" and eval(value)!=0.0 and (not foundStartExp_mo)):
                        self._missing_parameter(self, name, value, modelPath, mos_file)
                        
                    # Check if attributes StopTime/stopTime are defined in mos and mo
                    if (""+name+"="+"" == "stopTime=" and eval(value)!=1.0 and (not foundStopExp_mo)):
                        self._missing_parameter(self, name, value, modelPath, mos_file)
                        
                    # Check if attributes Tolerance/tolerance are defined in mos and mo
                    if (""+name+"="+"" == "tolerance=" and eval(value) >= 1e-6 and (not foundToleranceExp_mo)):
                        self._missing_parameter(self, name, value, modelPath, mos_file)
                                            
                    for i in range(Nlines-1, 0, -1):
    #                     
                        line = modelContent[i]
                 
    #                   # if the lines contains experiment stop time, replace it
                        if ""+self._capitalize_first(name)+"="+"" in line.replace(" ", "") and not found:
                            
                            # found the stopTime assignment, replace with the value in the mos file
                            pTime    = re.compile(r"[\d\S\s.,]*("+self._capitalize_first(name)+"=)([\d]*[.]*[\d]*[eE]*[+|-]*[\d]*[*]*[\d]*[.]*[\d]*[eE]*[+|-]*[\d]*)[\S\s.,]*")
                            mTime    = pTime.match(line)
                            val = mTime.group(2)
                            self._check_experiment(name, val, value, modelPath, mos_file)
                            found = True
                    
                elif value == ""+name+"":
                    self._wrong_literal(modelPath, name)
    
                
            f.close()
    
    def validateModelParameters(self, rootDir):
        
        # Make sure that the parameter rootDir points to a Modelica package.
        topPackage = os.path.join(rootDir, "package.mo")
        if not os.path.isfile(topPackage):
            raise ValueError("Argument rootDir=%s is not a Modelica package. Expected file '%s'."
                             % (rootDir, topPackage))
                
        # Get the path to the mos files
        rootPackage = os.path.join(rootDir, 'Resources', 'Scripts', 'Dymola')
        
        # Get all mos files
        mos_files = self._recursive_glob(rootPackage, '.mos')
        
        # Validate model parameters
        for i in ["stopTime", "tolerance", "startTime"]:
            self._validate_model_parameters(i, mos_files, rootDir)
      
        # Get the number of mos files with/without translateModelFMU 
        n_files_tol_mos, n_files_fmus, mosCorrect = self._number_occurences (mos_files, "mos")
        
        mo_files = []  
        for i in mosCorrect:
            mosPath=os.path.join(os.sep, 'Resources', 'Scripts', 'Dymola')
            mofile = i.replace(mosPath, "")
            mofile = mofile.replace(".mos", ".mo")
            mo_files.append(mofile)
        
        # Get the number of valid mo files
        n_files_tol_mo, _, _ = self._number_occurences (mo_files, "mo")
        
        if(n_files_tol_mos != n_files_tol_mo):
            raise ValueError("The number of .mo files with **tolerance** %s does not match the number of .mos scripts %s."
                % (str(n_files_tol_mos), str(n_files_tol_mo)))     
#         log.info("****************DIAGNOSTICS****************")
#         log.info("Number of .mos files found without **translateModelFMU**={!s}.".format(len(mosCorrect)))
#         log.info("Number of .mos files found with **translateModelFMU**={!s}.".format(n_files_fmus))
#         log.info("Number of .mo files with **tolerance**={!s}.".format(n_files_tol_mo))
#         log.info("Number of .mos files found with **tolerance**={!s}.".format(n_files_tol_mos))
#         log.info("Number of .mo files found with **Tolerance**={!s}.".format(n_files_tol_mo))    

