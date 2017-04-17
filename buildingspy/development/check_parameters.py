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

# import from future to make Python2 behave like Python3
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import *
from io import open
#from io import open
#import logging as log

# log.basicConfig(filename='check_parameters.log', filemode='w',
#                 level=log.DEBUG, format='%(asctime)s %(message)s',
#                 datefmt='%m/%d/%Y %I:%M:%S %p')
# stderrLogger = log.StreamHandler()
# stderrLogger.setFormatter(log.Formatter(log.BASIC_FORMAT))
# log.getLogger().addHandler(stderrLogger)

import os
import re

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
    
    def _check_experiment(self, name, val, value, model_path, mos_file):
        """ 
        Check experiment annotation in mo file.
    
        :param name: Parameter name.
        :param val: Value found in mo file.
        :param value: Value found in mos file.
        :param model_path: Path to mo file.
        :param mos_file: Path to mos file.
    
         """
        
        if("*" in str(val)):
            s = ("Found mo file=" + str(model_path) + " with experiment annotation " + self._capitalize_first(name) + ".\n" 
                + self._capitalize_first(name) + "contains invalid such as x * y. Only literal expressions are allowed " 
                + "by JModelica and OpenModelica unit tests.\n")
            raise ValueError(s) 
    
        delta = abs(eval(val) - eval(value))
        
        if (delta!=0):
            s = ("Found mo file=" + str(model_path) + " with experiment annotation " + self._capitalize_first(name) + ".\n" 
                + "The value of " + self._capitalize_first(name) + "="+str(val) +" is different from the (default) value="
                + str(value)+" found in the mos file=" + str(mos_file) + ".\n")
            raise ValueError(s)            
            

            
    def _missing_parameter(self, name, value, model_path, mos_file):
        """ 
        Check experiment annotation in mo file.
    
        :param name: Parameter name.
        :param value: Value found in mos file.
        :param model_path: Path to mo file.
        :param mos_file: Path to mos file.
    
         """
        
        s = ("Found mo file=" + str(model_path) + " without parameter " 
             + self._capitalize_first(name) + " defined.\n" 
            + "The parameter name " + name + " is defined in the mos file=" 
            + str(mos_file) + " and hence must be defined in the mo file.\n")
        raise ValueError(s)
        

    def _capitalize_first(self, name):
        """ 
        Capitalize the first letter of the given word.
        Return a word with first letter capitalized.
    
        :param name: Word to be capitalized.
    
         """
        lst = [word[0].upper() + word[1:] for word in name.split()]
        return " ".join(lst)
    
    def _missing_experiment(self, mos_files):
        """ 
        Check if ``experiment`` annotation exists in mo file.
        Return number of mo files with experiment.
    
        :param mos_files: List of mos files.
    
         """
        
        n_mo_files = 0
        for mos_file in mos_files:
            mos_path=os.path.join(os.sep, 'Resources', 'Scripts', 'Dymola')
            model_path=mos_file.replace(mos_path, "")
            model_path = model_path.replace(".mos", ".mo")
            fm = open(model_path,"r", encoding="utf8")
            
            model_content = fm.readlines()
            Nlines = len(model_content)
            
            foundExp = False
            for i in range(Nlines-1, 0, -1):
                line = model_content[i]
                if "experiment(" in line.replace(" ", ""):
                    foundExp=True
                    n_mo_files+=1
            if (not foundExp):
                s = ("Found mo file=" + str(model_path) 
                    + " without experiment annotation" + ".\n")
                raise ValueError(s)
                
            # close and exit
            fm.close()
        return n_mo_files 
    
        
    def _separate_mos_files(self, mos_files):
        """ 
        Return number of files with tolerance parameter
        and two list of mos files file, one with the ``simulateModel``
        and the other one with the ``translateModelFMU`` command.
    
        :param mos_files: file path.
    
         """
        
        mos_non_fmus = []
        mos_fmus = []
        
        n_tols = 0
        n_fmus = 0
        n_sim = 0
        
        for itr in mos_files:
            found_sim = False
            found_fmu = False
            found_tol = False
            f = open(itr,"r", encoding="utf8")
            content = f.readlines()
            i=0
            while i<len(content):
                l = content[i]
                if "tolerance=1" in (l.replace(" ", "")).lower():
                    found_tol =True
                    n_tols += 1
                if "simulateModel(" in l.replace(" ", ""):
                    n_sim+=1
                    found_sim = True
                    mos_non_fmus.append(itr)
                elif ("translateModelFMU" in l):
                    n_fmus += 1
                    mos_fmus.append(itr)
                    found_fmu = True
                i += 1
            f.close()
            
            if (found_sim and not found_tol):
                s = ("Found mos file=" + str(itr) 
                    + " without tolerance defined" + ".\n"
                    + "A maximum tolerance of 1e-6 is required by JModelica.\n")
                raise ValueError(s)
                
            
            if (not found_sim and not found_fmu):
                s = ("Found mos file=" + str(itr) 
                    + " with neither simulateModel() nor translateModelFMU()" + ".\n")
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
        if ("" + name + "=" + "" == "tolerance=" and float(value) > 1e-6):
            self._wrong_parameter (mos_file, name, value)
  
    
    def _wrong_parameter (self, mos_file, name, value):
        """ 
        Stop if invalid parameter is found.
    
        :param mos_file: mos file.
        :param name: parameter name.
        :param value: parameter value.
    
         """
         
        if ("" + name + "=" + "" == "tolerance="):
            if(float(value) > 1e-6):
                s = ("Found mos file=" + str(mos_file) + " with tolerance=" + str(value) + ".\n"
                    "The tolerance found is bigger than 1e-6, the maximum required by "
                    "JModelica for unit tests.\n")
                raise ValueError(s)
            elif(float(value) == 0.0):
                s = ("Found mos file=" + str(mos_file) + " without tolerance specified.\n" + 
                    "A maximum tolerance of 1e-6 is required by JModelica for unit tests.\n")
                raise ValueError(s)
        if ("" + name + "=" + "" == "stopTime="):
            if(float(value) == 0.0):
                s = ("Found mos file=" + str(mos_file) + " without stopTime specified.\n" + 
                    "A non-null stopTime is required by OpenModelica for unit tests.\n")
                raise ValueError(s)
                
    def _wrong_literal (self, mos_file, name):
        """ 
        Stop if invalid literal is detected.
    
        :param mos_file: mos file.
        :param name: Parameter name.
    
         """
        
        s = ("Found mos file=" + str(mos_file) + " with invalid expression=" 
             + str(name+'='+name) + ".\n" 
             + "This is not allowed for cross validation with JModelica.\n")
        raise ValueError(s)
    
    
    def _validate_model_parameters (self, name, mos_files, root_dir):
        """ 
        Validate parameter settings.
    
        :param name: Parameter name.
        :param mos_files: List of mos files.
        :param root_dir: Root directory.
    
         """

        N_mos_defect=0
    
        j = 1
        for mos_file in mos_files:
            j += 1
            
            f = open(mos_file,"r", encoding="utf8")
            
            content = f.readlines()
            found = False
            i = 0
            while found == False and i<len(content):
                l = content[i]
                if "simulateModel(" in l.replace(" ", ""):
                    line = l
                    found = True
                i += 1
            
            try:
                if ""+name+"="+name+"" in line.replace(" ", ""):
                    value = ""+name+""
                    self._wrong_literal(mos_file ,name)
                   
                if ""+name+"="+"" in line.replace(" ", ""):
                    pTime    = re.compile(r"[\d\S\s.,]*("+name+"=)([\d]*[.]*[\d]*[eE]*[+|-]*[\d]*[*]*[\d]*[.]*[\d]*[eE]*[+|-]*[\d]*)")
                    mTime    = pTime.match(line)
                    value = mTime.group(2)
                    self._check_tolerance(content, name, value, mos_file)     
                else:
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
                            self._wrong_literal(mos_file, name)
                    if found == False:
                        if (name=="startTime"):
                            value = "0.0"
                        elif (name=="stopTime"):
                            value="1.0"
                        elif(name=="tolerance"):
                            value="0.0"
                            print("Should be coming here")
                            self._wrong_parameter (mos_file, name, value)
    
            except AttributeError:
                value = "NA"
                N_mos_defect += 1
                
            if value != "NA" and value != ""+name+"":   

                mos_path=os.path.join(os.sep, 'Resources', 'Scripts', 'Dymola')
                model_path=mos_file.replace(mos_path, "")
                model_path = model_path.replace(".mos", ".mo")
                fm = open(model_path,"r", encoding="utf8")
                
                model_content = fm.readlines()
                Nlines = len(model_content)
                
                found = False
                foundStopExp_mo = False
                foundStartExp_mo = False
                foundToleranceExp_mo = False
                
                for i in range(Nlines-1, 0, -1):
                    line = model_content[i]
                    if "StopTime=" in line.replace(" ", ""):
                        foundStopExp_mo=True
                    if "StartTime=" in line.replace(" ", ""):
                        foundStartExp_mo=True
                    if "Tolerance=" in line.replace(" ", ""):
                        foundToleranceExp_mo=True
                
                # Check if attributes StartTime/startTime are defined in mos and mo                    
                if (""+name+"="+"" == "startTime=" and eval(value)!=0.0 and (not foundStartExp_mo)):
                    self._missing_parameter(name, value, model_path, mos_file)
                    
                # Check if attributes StopTime/stopTime are defined in mos and mo
                if (""+name+"="+"" == "stopTime=" and eval(value)!=1.0 and (not foundStopExp_mo)):
                    self._missing_parameter(name, value, model_path, mos_file)
                    
                # Check if attributes Tolerance/tolerance are defined in mos and mo
                if (""+name+"="+"" == "tolerance=" and eval(value) >= 1e-6 and (not foundToleranceExp_mo)):
                    self._missing_parameter(name, value, model_path, mos_file)
                                        
                for i in range(Nlines-1, 0, -1):   
                    line = model_content[i]
             
                    # if the lines contains experiment stop time, replace it
                    if ""+self._capitalize_first(name)+"="+"" in line.replace(" ", "") and not found:
                        pTime    = re.compile(r"[\d\S\s.,]*("+self._capitalize_first(name)+"=)([\d]*[.]*[\d]*[eE]*[+|-]*[\d]*[*]*[\d]*[.]*[\d]*[eE]*[+|-]*[\d]*)[\S\s.,]*")
                        mTime    = pTime.match(line)
                        val = mTime.group(2)
                        self._check_experiment(name, val, value, model_path, mos_file)
                        found = True
                
                fm.close()
            elif value == ""+name+"":
                self._wrong_literal(model_path, name)
    
                
            f.close()
    
    def validateModelParameters(self, root_dir):
        
        """ 
        Validate parameter of mo and mos files.
    
        :param root_dir: Root directory.
    
         """
        
        # Make sure that the parameter root_dir points to a Modelica package.
        topPackage = os.path.join(root_dir, "package.mo")
        if not os.path.isfile(topPackage):
            s = ("Argument root_dir=" + str(root_dir) + " is not a Modelica package\n" 
                + " Expected file=" + str(topPackage)+ ".\n")
            raise ValueError(s)
                
        # Get the path to the mos files
        rootPackage = os.path.join(root_dir, 'Resources', 'Scripts', 'Dymola')
        
        # Get all mos files
        mos_files = self._recursive_glob(rootPackage, '.mos')
        
        # Split mos files which either contain simulateModel or translateModelFMU
        n_tols, mos_non_fmus, _ =  self._separate_mos_files (mos_files)
        
        # Check if all .mo files contain experiment annotation
        n_mo_files = self._missing_experiment(mos_non_fmus)
        
        # Validate model parameters
        for i in ["stopTime", "tolerance", "startTime"]:
            self._validate_model_parameters(i, mos_non_fmus, root_dir)
        
        if(n_tols!=n_mo_files):
            s = ("The number of tolerances in the mos files=" + str(n_tols) 
                + " does no match the number of mo files=" + str(n_mo_files)+ ".\n")
            raise ValueError(s)
  
#         log.info("****************DIAGNOSTICS****************")
#         log.info("Number of .mos files found without **translateModelFMU**={!s}.".format(len(mosCorrect)))
#         log.info("Number of .mos files found with **translateModelFMU**={!s}.".format(n_files_fmus))
#         log.info("Number of .mo files with **tolerance**={!s}.".format(n_files_tol_mo))
#         log.info("Number of .mos files found with **tolerance**={!s}.".format(n_files_tol_mos))
#         log.info("Number of .mo files found with **Tolerance**={!s}.".format(n_files_tol_mo))    

