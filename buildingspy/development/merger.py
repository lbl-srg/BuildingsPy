#!/usr/bin/env python
#######################################################
# Script that merges a Modelica library with
# the Annex60 Modelica library.
#
# MWetter@lbl.gov                            2014-04-15
#######################################################
from docutils.nodes import Root
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

            This function merges the `Annex60` library into other
            Modelica libraries. In the top-level directory of the
            destination library, this function creates the file
            `.copiedFiles.txt` that lists all files that have been
            copied. In subsequent calls, this function
            deletes all files listed in `.copiedFiles.txt`,
            then merges the libraries, and creates a new version of
            `.copiedFiles.txt`. Therefore, if a model is moved
            in the `Annex60` library, it will also be moved in the
            target library by deleting the old file and copying
            the new file.

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

        import buildingspy.development.refactor as r

        # path where a list of all copied files is saved
        copFilPat = os.path.join(self._target_home, ".copiedFiles.txt")

        # Remove files from previous merge
        if os.path.isfile(copFilPat):
            roo = self._target_home.split(self._new_library_name)[0]
            with open(copFilPat,'r') as fp:
                files = fp.read().splitlines()
                for fil in files:
                    if not fil.startswith('#'):
                        absFil = os.path.join(roo, fil)
                        if os.path.isfile(absFil):
                            os.remove(fil)

        copiedFiles=list()

        # Location of reference results
        ref_res = os.path.join(self._target_home, "Resources", "ReferenceResults", "Dymola")

        excludes = '|'.join([x for x in self._excluded_packages]) or r'$.'

        for root, dirs, files in os.walk(self._annex60_home):
            # Exclude certain folders
            dirs[:] = [os.path.join(root, d) for d in dirs]
            dirs[:] = [d for d in dirs if not re.search(excludes, d)]

            for fil in files:
                srcFil=os.path.join(root, fil)
                # Loop over all
                # - .mo files except for top-level .mo file
                # - .mos files
                # - ReferenceResults
                if (not srcFil.endswith(os.path.join("Annex60", "package.mo")) \
                    or srcFil.endswith("legal.html")):

                    desFil=srcFil.replace(self._annex60_home, self._target_home)
                    desPat=os.path.dirname(desFil)
                    if not os.path.exists(desPat):
                        os.makedirs(desPat)
                    # Process file.
                    # Copy mo and mos files, and replace the library name
                    if desFil.endswith(".mo") or desFil.endswith(".mos"):
                        copiedFiles.append(desFil)
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
                            copiedFiles.append(new_file)
                            shutil.copy2(srcFil, new_file)

                    # Copy all other files. This may be images, C-source, libraries etc.
                    else:
                        copiedFiles.append(desFil)
                        shutil.copy2(srcFil, desFil)

        # Generate package.order files
        r.write_package_order(self._target_home, True)
        # Save a list of all files that were copied.
        with open(copFilPat,'w') as fp:
            fp.write("# Do not edit this file unless you know what you are doing.\n")
            fp.write("# This file is used by the Annex60 merge script and generated by BuildingsPy.\n")
            for fil in copiedFiles:
                fp.write(self._new_library_name + fil.split(self._target_home)[1] + "\n")
