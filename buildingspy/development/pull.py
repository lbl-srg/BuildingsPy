#!/usr/bin/env python
#######################################################
# Script that pulls the Annex60 Modelica library
# into another Modelica library
#
# MWetter@lbl.gov                            2014-04-15
#######################################################


class Annex60:
    ''' Class that pulls the `Annex60` Modelica library into another
    Modelica library that has the same package structure.


    '''
    def __init__(self, **kwargs):
        ''' Constructor.
        '''
        import os

        # --------------------------
        # Class variables
        #fixme: This should be made as arguments
        root = "/Users/mwetter/proj/ldrd/bie/modeling/github"
        self._annex60_home=os.path.abspath(root + "/iea-annex60/modelica-annex60/Annex60")
        self._target_home=os.path.abspath(root + "/lbl-srg/modelica-buildings/Buildings")
        self._new_library_name = "Buildings"

    def _merge_package_order(self, source_file, destination_file):
        """ Merge the `package.order` file.
        
        :param source_file: The source file for the `package.order` file
        :param destination_file: The destination file for the `package.order` file
        """
        import os
        import shutil
        
        if os.path.isfile(destination_file):
            # Merge the file
            print "fixme. implement merging of package.order"
        else:
            shutil.copy2(source_file, destination_file)


    def _copy_mo_and_mos(self, source_file, destination_file):
        """ Update the library name and do other replacements that
            may be specific for an individual library.
        
        :param file_name: Name of the file
        """
        import string
        rep = {"Annex60": 
               self._new_library_name}
        # For the Buildings library, do these additional replacements.
        if self._new_library_name == "Buildings":
            rep.update({"Modelica.Thermal.HeatTransfer.Sources.PrescribedTemperature":
                        "Buildings.HeatTransfer.Sources.PrescribedTemperature",
                        "Modelica.Thermal.HeatTransfer.Sources.PrescribedHeatFlow":
                        "Buildings.HeatTransfer.Sources.PrescribedHeatFlow"})

        # fixme: We don't yet want to replace media
    #           "Buildings.Media.ConstantPropertyLiquidWater":
    #           "Buildings.Media.Water",
    #           "Buildings.Media.GasesPTDecoupled.MoistAir":
    #           "Buildings.Media.Air",
    #           "Buildings.Media.GasesPTDecoupled.MoistAirUnsaturated":
    #           "Buildings.Media.Air",
    #           "Buildings.Media.GasesPTDecoupled.SimpleAir":
    #           "Buildings.Media.Air",
    #           "Buildings.Media.GasesConstantDensity.MoistAir":
    #           "Buildings.Media.Air",
    #           "Buildings.Media.GasesConstantDensity.MoistAirUnsaturated":
    #           "Buildings.Media.Air",
    #           "Buildings.Media.GasesConstantDensity.SimpleAir":
    #           "Buildings.Media.Air",
    #           "Buildings.Media.IdealGases.SimpleAir":
    #           "Buildings.Media.Air",
    #           "Buildings.Media.PerfectGases.MoistAir":
    #           "Buildings.Media.Air",
    #           "Buildings.Media.PerfectGases.MoistAirUnsaturated":
    #           "Buildings.Media.Air"
    
        # Read source file, store the lines and update the content of the lines
        f_sou = open(source_file, 'r')
        lines = list()
        for lin in f_sou.readlines():
            for ori, new in rep.iteritems():
                lin = string.replace(lin, ori, new)
            lines.append(lin)
        f_sou.close
        # Write the lines to the new file
        f_des = open(destination_file, 'w')
        f_des.writelines(lines)
        f_des.close()
        
    def _copy_files(self):
        """ Copy all files except the license file and the top-level package.mo
        """
        import os
        import shutil

        # Location of reference results
        ref_res = os.path.join(self._target_home, "Resources", "ReferenceResults")
        
        for root, _, files in os.walk(self._annex60_home):
            for fil in files:
                srcFil=os.path.join(root, fil)
                # Loop over all 
                # - .mo files except for top-level .mo file
                # - package.order
                # - .mos files
                # - ReferenceResults
                if (not srcFil.endswith(os.path.join("Annex60", "package.mo")) \
                    or srcFil.endswith("legal.html")):
                    
                    desFil=srcFil.replace(self._annex60_home, self._target_home)
                    desPat=os.path.dirname(desFil)
                    if not os.path.exists(desPat):
                        os.makedirs(desPat)
                    # Process file.
                    # If package.order does already exist, then need to merge it
                    if desFil.endswith("package.order") and os.path.exists(desFil):
                        self._merge_package_order(srcFil, desFil)
                    # If package.order does not exist, then simply copy it
                    elif desFil.endswith("package.order"):
                        shutil.copy2(srcFil, desFil)
                    # Copy mo and mos files, and replace the library name
                    elif desFil.endswith(".mo") or desFil.endswith(".mos"):
                        shutil.copy2(srcFil, desFil)
                        self._update_mo_and_mos(desFil)
                    # Only copy reference results if no such file exists.
                    # If a reference file already exists, the don't change it. 
                    # This requires to replace
                    # the name of the library in names of the result file
                    elif desFil.startswith(ref_res):
                        dir_name = os.path.dirname(ref_res)
                        base_name = os.path.basename(ref_res)
                        new_file = os.path.join(dir_name, 
                                                base_name.replace("Annex60", 
                                                                  self._new_library_name))
                        if not os.path.isfile(new_file):
                            shutil.copy2(srcFil, new_file)
                    # Copy all other files. This may be images, C-source, libraries etc.
                    else:
                        shutil.copy2(srcFil, desFil)

