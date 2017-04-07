#!/usr/bin/env python
###########################################################
# Python script for making sure that the simulation 
# settings specified in the mos files are the same 
# as the ones used in the Experiment Annotation 
# of the corresponding Modelica model.The reason is 
# because Dymola ignores the parameters defined in 
# the Experiment Annotation when running the simulateModel() 
# command of the unit test
#
# TSNouidui@lbl.gov                            2017-01-24
###########################################################
#

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import logging as log

log.basicConfig(filename='matchParameters.log', filemode='w',
                level=log.DEBUG, format='%(asctime)s %(message)s',
                datefmt='%m/%d/%Y %I:%M:%S %p')
stderrLogger = log.StreamHandler()
stderrLogger.setFormatter(log.Formatter(log.BASIC_FORMAT))
log.getLogger().addHandler(stderrLogger)

#from __future__ import unicode_literals

import os
import re

def recursive_glob(rootdir='.', suffix=''):
    return [os.path.join(rootdir, filename) for rootdir, dirnames, 
            filenames in os.walk(rootdir) for filename in filenames 
            if ( filename.endswith(suffix) 
                 and ("ConvertBuildings_from" not in filename)) ]

# Get the path to the library
libHome = os.path.abspath(".")

print (libHome)

# Get the path to the mos files
rootPackage = os.path.join(libHome, 'Resources', 'Scripts', 'Dymola')

mos_files = recursive_glob(rootPackage, '.mos')

# number of modified models
N_modify_mos = 0
# number of modified models
N_modify_models = 0
# number of .mos scripts with problems
N_mos_defect = 0
# mos files to fix
mosToFixed=[]
# mo files to fix
moToFixed=[]
# number of times script must run
N_Runs = 2
# number of valid mos files.
mosCorrect=[]
# Known missing tolerance flag
knownMissingTolerance = False
# Number of .mos files
N_mos_files = len(mos_files)
# Defect mos files
defect_mos=[]

def defect_mo_files(foundMos):
    """ 
    Return a list of .mo files which do not have a Tolerance
    in the experiment Annotation.

    :param foundMos: List of mos files.

     """
    # known missing tolerance falg
    global knownMissingTolerance
    knownMissingTolerance = False
    
    for k in foundMos:
        newMofile = k.replace("/Resources/Scripts/Dymola", "")
        newMofile = newMofile.replace(".mos", ".mo")
        # Exclude an mo file with known missing tolerance annotation
        if 'Fluid/Movers/Validation/PumpCurveDerivatives.mo' in newMofile:
            knownMissingTolerance = True
        f = open(newMofile, "r")
        content = f.readlines()
        found = False
        i = 0
        while found == False and i < len(content):
            l = content[i]
            if "tolerance=1" in l.lower():
                found = True
                break
            i += 1
        if found == False:
            moToFixed.append(newMofile)
        f.close()
    return moToFixed

def capitalize_first(name):
    """ 
    Capitalize the first letter of the given word.

    :param name: Word to be capitalized.

     """
    lst = [word[0].upper() + word[1:] for word in name.split()]
    return " ".join(lst)

def write_file(mos_file, content):
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
    
def number_occurences(filPat, ext):
    """ 
    Count number of occurences of Tolerance=1.

    :param filPat: file path.
    :param ext: file extension.

     """
    
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
    return n_files_tol, n_files_fmus

def replace_content(content, name, value, para, foundStop):
    """ 
    Replace content to a file.

    :param content: file content.
    :param name: variable name.
    :param value: variable value.
    :param para: parameter value.
    :param foundStop: Flag to stop.

     """

    # Delete the old file
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
    

def replace_stoptime(content, name, value, foundStop):
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

def replace_resultfile(content, name, value, foundStop):
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

def replace_tolerance_intervals(content, name, value, mos_file):
    """ 
    Replace tolerance and numberOfIntervals in file.

    :param content: file content.
    :param name: variable name.
    :param value: variable value.
    :param mos_file: mos file.

     """
    if ("" + name + "=" + "" == "tolerance=" and float(value) > 1e-6):
        wrong_parameter (mos_file, name, value)
#         foundStop = False
#         consPar = "1e-6"
#         foundStop, content = replace_content(content, name, value, consPar, foundStop)
#         write_file(mos_file, content)    

def wrong_parameter (mos_file, name, value):
    """ 
    Stop if invalid parameter is found.

    :param mos_file: mos file.
    :param name: parameter name.

     """
     
    if ("" + name + "=" + "" == "tolerance="):
        if(float(value)> 1e-6):
            #print("\t=================================")
            log.error("Found mos_file: {!s} with a tolerance={!s}).".format(mos_file, value))
            log.error("This tolerance is bigger than the maximum allowed tolerance of 1e-6.")
            log.error("A tolerance of 1e-6 or less is required for the JModelica verification.")
            log.error("Please correct the .mos file  and re-run the conversion script.")
            exit(1)
        elif(float(value)== 0.0):
            #log.error("\t=================================")
            log.info("Found mos_file: {!s} without **tolerance** specified.".format(mos_file))
            log.error("A tolerance of 1e-6 or less is required for the JModelica verification.")
            log.error("Please correct the .mos file  and re-run the conversion script.")
            exit(1)
            


def wrong_literal (mos_file):
    """ 
    Stop if wrong invalid literal is detected.

    :param mos_file: mos file.

     """
     
    #log.error("\t=================================")
    log.error("Found mos_file: {!s} with expression such as startTime=startTime.".format(mos_file))
    log.error("This is not allowed for the JModelica verification.")
    log.error("Please correct the .mos file  and re-run the conversion script.")    
    exit(1)


def fixParameters (name):
    """ 
    Fix parameter settings.

    :param name: mos file.

     """

    global N_modify_models
    global N_modify_mos
    global N_mos_defect   
    global defect_mos
    global mosToFixed

    N_modify_models=0
    N_modify_mos=0
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
                wrong_literal(mos_file)
            if ""+name+"="+"" in line.replace(" ", ""):
                # pTime    = re.compile(r"[\d\S\s.,]*(stopTime=)([\d]*[.]*[\d]*[e]*[+|-]*[\d]*)")
                pTime    = re.compile(r"[\d\S\s.,]*("+name+"=)([\d]*[.]*[\d]*[eE]*[+|-]*[\d]*[*]*[\d]*[.]*[\d]*[eE]*[+|-]*[\d]*)")
                mTime    = pTime.match(line)
                value = mTime.group(2)
                replace_tolerance_intervals(content, name, value, mos_file)     
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
                        replace_tolerance_intervals(content, name, value, mos_file)  
                        #startTime = startTime[:-1]
                    if ""+name+"="+name+"" in line.replace(" ", ""):
                        value = ""+name+""
                        #print("\t=================================")
                        wrong_literal(mos_file)
                if found == False:
#                     if (name=="startTime"):
#                         #print("\t"+ name + " not found, defined the default startTime=0.0")
#                         value = "0.0"
                    if (name=="stopTime"):
                        #print("\t"+ name + " not found, defined the default stopTime=1.0")
                        value="1.0"
                    elif(name=="tolerance"):
                        value="0.0"
                    foundStop=False
                    if (name=="stopTime"):
                        foundStop, content = replace_resultfile(content, name, value, foundStop)
                    elif(name=="tolerance"):
                        # Return with an error since tolerance is not specified in mos
                        wrong_parameter (mos_file, name, value)
                        #foundStop, content = replace_stoptime(content, name, value, foundStop)
                    if foundStop == False:
                        # Break and continue with other parameters
                        break;
                    write_file(mos_file, content) 
                    
                    #print("\tNew mos script is available!")
                    N_modify_mos += 1    

        except AttributeError:
            #print("\tThe script does not contain the simulation command! Maybe it is a plot script...")
            value = "NA"
            N_mos_defect += 1
            
        if (""+name+"="+"" != "numberOfIntervals=" ):
            if value != "NA" and value != ""+name+"":        
                
                modelPath = ""
                modelPath = modelName.replace(".", "/")
                modelPath = "../"+modelPath+".mo"

                fm = open(modelPath,"r")
                
                modelContent = fm.readlines()
                Nlines = len(modelContent)
                
                found = False
                foundExp = False
                foundStopExp = False
                for i in range(Nlines-1, 0, -1):
                    line = modelContent[i]
                    if "experiment(" in line.replace(" ", ""):
                        foundExp=True
                    if "StopTime" in line.replace(" ", ""):
                        foundStopExp=True
                    
            
                if (not foundExp and not foundStopExp):
                    defect_mos.append(modelPath)
                    
                for i in range(Nlines-1, 0, -1):
#                     
                    line = modelContent[i]
#                     
#                   # if the lines contains experiment stop time, replace it
#                   # experiment(StopTime=2)
                    if ""+capitalize_first(name)+"="+"" in line.replace(" ", "") and not found:
                        # found the stopTime assignment, replace with the value in the mos file
                        pTime    = re.compile(r"[\d\S\s.,]*("+capitalize_first(name)+"=)([\d]*[.]*[\d]*[eE]*[+|-]*[\d]*[*]*[\d]*[.]*[\d]*[eE]*[+|-]*[\d]*)[\S\s.,]*")
                        mTime    = pTime.match(line)
                        val = mTime.group(2)
       
                        #newLine = line.replace(mNameStr,""+capitalize_first(name)+"="+""+str(value))
                        newLine = line.replace(""+capitalize_first(name)+"="+"" + str(val), ""+capitalize_first(name)+"="+""+str(value))
                         
                        # replace
                        modelContent[i] = newLine
                        found = True
                    
                    # check if we shouldn't remove spaces in line.replace(" ", "")s to avoid this?
                    if ("annotation(" in line.replace(" ", "")) and not found:    
                        # We reach the beginning of the annotation and we don't found the stop time
                        # Go back and look for the __DymolaCommand and replace it adding the experiment
                        # stopTime command
                        for k in range(Nlines-1, i-1, -1):
                            line = modelContent[k]
                            line.replace(" ", "")
                            if (name=="stopTime"):
                                if (not foundExp and not foundStopExp):
                                    log.error("Found mo_file: {!s} without experiment annotation.".format(modelPath))
                                    log.error("An **experiment** annotation is required in an .mo example file.")
                                    log.error("The parameters of the **experiment** annotation must match the parameters of the associated .mos script: {!s}.".format(mos_file))
                                    log.error("Please correct the .mo file  and re-run the conversion script.")
                                    exit(1)
                                    # Stop with an error if experiment annotation is missing in mo file
#                                     if "__Dymola_Commands(" in line.replace(" ", ""):
#                                         newLine = line.replace("__Dymola_Commands(", "\nexperiment(StopTime="+str(value)+"),\n__Dymola_Commands(")
#                                         # replace
#                                         modelContent[k] = newLine
#                                         # replacement done
#                                         found = True    
#                                         break       
                                elif (foundExp and not foundStopExp):
                                    if "Tolerance=" in line.replace(" ", ""):
                                        pTime    = re.compile(r"[\d\S\s.,]*("+"Tolerance"+"=)([\d]*[.]*[\d]*[eE]*[+|-]*[\d]*[*]*[\d]*[.]*[\d]*[eE]*[+|-]*[\d]*)")
                                        mTime    = pTime.match(line)
                                        val = mTime.group(2)
                                        newLine = line.replace("Tolerance="+"" + str(val), ""+capitalize_first(name)+"="+""+str(value))
                                        # replace
                                        modelContent[k] = newLine
                                        # replacement done
                                        found = True             
                                        break
                                    elif "StartTime=" in line.replace(" ", ""):
                                        pTime    = re.compile(r"[\d\S\s.,]*("+"StartTime"+"=)([\d]*[.]*[\d]*[eE]*[+|-]*[\d]*[*]*[\d]*[.]*[\d]*[eE]*[+|-]*[\d]*)")
                                        mTime    = pTime.match(line)
                                        val = mTime.group(2)
                                        newLine = line.replace("StartTime="+"" + str(val), ""+capitalize_first(name)+"="+""+str(value))
                                        # replace
                                        modelContent[k] = newLine
                                        # replacement done
                                        found = True  
                                        break
                            else:
                                if "StopTime=" in line.replace(" ", ""):
                                    newLine = line.replace("StopTime" , ""+capitalize_first(name)+"="+""+str(value)+", StopTime")
                                    
                                    # replace
                                    modelContent[k] = newLine 
                                    # replacement done
                                    found = True  
                                    break  
                write_file(modelPath, modelContent)
                N_modify_models += 1  
                
            elif value == ""+name+"":
                #print("\n\t*******************************")
                print("\tDO THAT MODIFICATION AT HAND!!!")
            
        f.close()
    
def main():
    for k in range(N_Runs):
        for i in ["stopTime", "tolerance", "startTime"]:
            fixParameters(i)
  
    log.info("****************DIAGNOSTICS****************")
    
    n_files_tol_mos, n_files_fmus = number_occurences (mos_files, "mos")
    
    log.info("Number of .mos files found without **translateModelFMU**={!s}.".format(len(mosCorrect)))
    log.info("Number of .mos files found with **translateModelFMU**={!s}.".format(n_files_fmus))
    
    log.info(".mos files with **stopTime=stopTime**={!s}.".format(mosToFixed))
    log.info("Number of .mos files with **stopTime=stopTime**={!s}.".format(len(mosToFixed)))
    
    defect_mo = defect_mo_files(mosCorrect)
    
    mo_files = []  
    for i in mosCorrect:
        mofile = i.replace("/Resources/Scripts/Dymola", "")
        mofile = mofile.replace(".mos", ".mo")
        mo_files.append(mofile)
    
    n_files_tol_mo, n_files_fmus = number_occurences (mo_files, "mo")

    log.info("Number of .mo files with **tolerance**={!s}.".format(n_files_tol_mo))
    
    log.info(".mo files without **tolerances**={!s}.".format(defect_mo))
    log.info("Number of .mo files without **tolerances**={!s}.".format(len(defect_mo)))
    
    log.info(".mo files without **experiment** annotation={!s}.".format(defect_mos))
    log.info("Number of .mo files without **experiment** annotation={!s}.".format(len(defect_mos)))
    
    log.info("Number of .mos files found with **tolerance**={!s}.".format(n_files_tol_mos))
    log.info("Number of .mo files found with **Tolerance**={!s}.".format(n_files_tol_mo))
    
    #if(knownMissingTolerance):
    #    n_files_tol_mo-=1
    
    # will be reduced to avoid the assert to trigger as this is to be expected.
    assert n_files_tol_mos - n_files_tol_mo == 0, "The number of .mo files with **tolerance** {!s} does not match the number of .mos scripts: {!s}."   
