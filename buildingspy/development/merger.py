#!/usr/bin/env python
#######################################################
# Script that merges a Modelica library with
# the Annex60 Modelica library.
#
# MWetter@lbl.gov                            2014-04-15
#######################################################
class Annex60:
    ''' Class that merges a Modelica library with the `Annex60` library.

        Both libraries need to have the same package structure.

        By default, the top-level packages `Media`, `Experimental`,
        and `Obsolete` are not included in the merge.
        This can be overwritten with the function
        :meth:`~set_excluded_packages`.

    '''
    def __init__(self, annex60_dir, dest_dir):
        ''' Constructor.

        :param annex60_dir: Directory where the `Annex60` library is located.
        :param dest_dir: Directory where the library to be updated is located.
        '''
        import os

        # Check arguments
        def isValidLibrary(lib_home):
            import buildingspy.development.regressiontest as t

            if not t.Tester().isValidLibrary(lib_home):
                s = "*** %s is not a valid Modelica library." % lib_home
                s += "\n    Did not do anything."
                raise ValueError(s)

        isValidLibrary(annex60_dir)
        isValidLibrary(dest_dir)

        # --------------------------
        # Class variables
        self._annex60_home=annex60_dir
        self._target_home=dest_dir
        # Library name, such as Buildings
        self._new_library_name = os.path.basename(dest_dir)

        # This is a hack to exclude top-level packages
        self.set_excluded_packages(["Media", "Experimental", "Obsolete"])

    def set_excluded_packages(self, packages):
        ''' Set the packages that are excluded from the merge.
        
        :param packages: A list of packages to be excluded.
        
        '''
        if not isinstance(packages, list):
            raise ValueError("Argument must be a list.")
        self._excluded_packages = packages


    def get_merged_package_order(self, directory, src, des):
        """ Return a set where each entry is a line for the merged
            `package.order` file.

            :param directory: Directory of the `package.order` file.
            :param src: Lines of the source file for `package.order`.
            :param des: Lines of the destination file for `package.order`.

        """
        def moveItemToFront(item, lis):
            if item in lis:
                lis.remove(item)
                lis.insert(0, item)
            return lis

        def moveItemToEnd(item, lis):
            if item in lis:
                lis.remove(item)
                lis.append(item)
            return lis

        def isPackage(directory, item):
            import os
            if os.path.isdir(os.path.join(directory, item)):
                return True
            if os.path.isfile(item + ".mo"):
                fil = open(item + ".mo", 'r')
                for i, line in enumerate(fil):
                    # Search the first 3 lines
                    if i < 3:
                        if line.lstrip().startswith('package '):
                            return True
            return False

        # Remove all line endings, and trim white spaces.
        li = list()
        for ele in src:
            e = ele.strip(' \t\n\r')
            if e is not "":
                li.append(e)

        # Remove excluded top-level packages
        for pac in self._excluded_packages:
            if pac in li and not isPackage(directory, pac):
                li.remove(pac)

        # Add the destination packages
        for ele in des:
            e = ele.strip(' \t\n\r')
            if e is not "":
                li.append(e)

        # Sort the list
        s = list(sorted(set(li)))

        # Uppercase entries could be packages or models.
        # List packages first, followed by models
        m = list()
        p = list()
        for ele in s:
            if ele[0].isupper():
                if isPackage(directory, ele):
                    p.append(ele)
                else:
                    m.append(ele)
            else:
                m.append(ele)

        s = p
        for ele in m:
            s.append(ele)

        s = moveItemToFront("UsersGuide", s)
        s = moveItemToEnd("Data", s)
        s = moveItemToEnd("Types", s)
        s = moveItemToEnd("Examples", s)
        s = moveItemToEnd("Experimental", s)
        s = moveItemToEnd("BaseClasses", s)
        s = moveItemToEnd("Interfaces", s)
        s = moveItemToEnd("Internal", s)        
        s = moveItemToEnd("Obsolete", s)

        return s


    def _merge_package_order(self, source_file, destination_file):
        """ Merge the `package.order` file.

        :param source_file: The source file for the `package.order` file
        :param destination_file: The destination file for the `package.order` file
        """
        import os
        import shutil

        if os.path.isfile(destination_file):
            # Read the content of the package.order files
            f_sou = open(source_file, 'r')
            src = f_sou.readlines()
            f_sou.close()
            f_des = open(destination_file, 'r')
            des = f_des.readlines()
            f_des.close()
            # Merge the content
            merged = self.get_merged_package_order(os.path.dirname(destination_file), src, des)
            # Write the new file
            f_des = open(destination_file, 'w')
            for lin in merged:
                f_des.write(lin + "\n")
            f_des.close()
        else:
            shutil.copy2(source_file, destination_file)


    def _copy_mo_and_mos(self, source_file, destination_file):
        """ Update the library name and do other replacements that
            may be specific for an individual library.

        :param source_file: Name of the file to be copied.
        :param destination_file: Name of the new file.
        """
        import os
        import re
        import string

        rep = {"Annex60":
               self._new_library_name}
        # For the Buildings library, do these additional replacements.
        if self._new_library_name == "Buildings":
            # Replace some strings
            rep.update({"Annex60.Experimental.Media.AirPTDecoupled":
                        "Buildings.Media.GasesPTDecoupled.MoistAirUnsaturated",
                         "Annex60.Media.Air.saturationPressure":
                        "Buildings.Media.PerfectGases.MoistAirUnsaturated.saturationPressure",
                        "Set the medium model to <code>Annex60.Media.Air</code>.":
                        "Set the medium model to <code>Buildings.Media.PerfectGases.MoistAirUnsaturated</code>."})
            # Update the models that we use from Buildings.HeatTransfer rather
            # than from the MSL
            rep.update({"Modelica.Thermal.HeatTransfer.Sources.PrescribedTemperature":
                        "Buildings.HeatTransfer.Sources.PrescribedTemperature",
                        "Modelica.Thermal.HeatTransfer.Sources.FixedTemperature":
                        "Buildings.HeatTransfer.Sources.FixedTemperature",
                        "Modelica.Thermal.HeatTransfer.Sources.PrescribedHeatFlow":
                        "Buildings.HeatTransfer.Sources.PrescribedHeatFlow"})

        # Read destination file if it exists.
        # This is needed as we do not yet want to replace the medium.
        if os.path.isfile(destination_file):
            f_des = open(destination_file, 'r')
            desLin = f_des.readlines()
        else:
            desLin = None

        # Read source file, store the lines and update the content of the lines
        f_sou = open(source_file, 'r')
        lines = list()
        for i, lin in enumerate(f_sou):
            if desLin is not None and i < len(desLin)-1:
                # Check if the destination file contains at that line a medium declaration.
                patAnn = re.compile('package\s+Medium\w*\s*=\s*Annex60.Media')
                patDes = re.compile('package\s+Medium\w*\s*=\s*Buildings.Media|package\s+Medium\w*\s*=\s*Modelica.Media')
                if patDes.search(desLin[i]) and patAnn.search(lin):
                    # This line contains the Media declaration.
                    # Copy the declaration from the destination file into this line
                    lin = desLin[i]
            for ori, new in rep.iteritems():
                lin = string.replace(lin, ori, new)
            lines.append(lin)
        f_sou.close
        # Write the lines to the new file
        f_des = open(destination_file, 'w')
        f_des.writelines(lines)
        f_des.close()

    def merge(self):
        """ Merge all files except the license file and the top-level ``package.mo``

            .. warning:: This method is experimental. Do not use it without
                         having a backup of your code.

            A typical usage is
                >>> import buildingspy.development.merger as m
                >>> import os
                >>> home = os.path.expanduser("~")
                >>> root = os.path.join(home, "test")
                >>> annex60_dir = os.path.join(root, "modelica-annex60", "Annex60")
                >>> dest_dir = os.path.join(root, "modelica-buildings", "Buildings")
                >>> mer = m.Annex60(annex60_dir, dest_dir) # doctest: +SKIP
                >>> mer.merge()                            # doctest: +SKIP

        """
        import os
        import shutil
        import re
        import fnmatch

        excludes = '|'.join([x for x in self._excluded_packages]) or r'$.'
        
        # path where a list of all copied files is saved
        copFilPat = os.path.join(self._target_home,"CopiedFiles.txt")
        
        # remove files from previous merge
        if os.path.isfile(copFilPat):
            with open(copFilPat,'r') as fp:
                files = fp.read()
            for filPat in files.split("\n"):
                if not filPat.startswith("#") and os.path.isfile(filPat):
                    os.remove(filPat)
        
        
        copiedFiles='# Do not edit this file unless you know what you are doing! \n#This file is used by the Annex60 merge script - generated by BuildingsPy\n'
        
        # Location of reference results
        ref_res = os.path.join(self._target_home, "Resources", "ReferenceResults", "Dymola")

        for root, dirs, files in os.walk(self._annex60_home):
            # Exclude certain folders
            dirs[:] = [os.path.join(root, d) for d in dirs]
            dirs[:] = [d for d in dirs if not re.search(excludes, d)]

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
                    copiedFiles = copiedFiles + desFil + "\n"
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
                        self._copy_mo_and_mos(srcFil, desFil)
                    # Only copy reference results if no such file exists.
                    # If a reference file already exists, then don't change it.
                    # This requires to replace
                    # the name of the library in names of the result file
                    elif desFil.startswith(ref_res):
                        dir_name = os.path.dirname(desFil)
                        base_name = os.path.basename(desFil)
                        new_file = os.path.join(dir_name,
                                                base_name.replace("Annex60",
                                                                  self._new_library_name))
                        if not os.path.isfile(new_file):
                            shutil.copy2(srcFil, new_file)

                    # Copy all other files. This may be images, C-source, libraries etc.
                    else:
                        shutil.copy2(srcFil, desFil)
            
            #save a list of all files that were copied            
            with open(copFilPat,'w') as fp:
                fp.write(copiedFiles)
