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

        By default, the top-level packages `Experimental`
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

            try:
                t.Tester().isValidLibrary(lib_home)
            except ValueError as e:
                s = "{}\n    Did not do anything.".format(e.message)
                raise ValueError(s)

        isValidLibrary(annex60_dir)
        isValidLibrary(dest_dir)

        # --------------------------
        # Class variables
        self._annex60_home=annex60_dir
        self._target_home=dest_dir
        # Library name, such as Buildings
        self._new_library_name = os.path.basename(dest_dir)

        # Exclude top-level packages
        self.set_excluded_packages(["Experimental", "Obsolete"])

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
            # Update the models that we use from Buildings.HeatTransfer rather
            # than from the MSL
            rep.update({"Modelica.Thermal.HeatTransfer.Sources.PrescribedTemperature":
                        "Buildings.HeatTransfer.Sources.PrescribedTemperature",
                        "Modelica.Thermal.HeatTransfer.Sources.FixedTemperature":
                        "Buildings.HeatTransfer.Sources.FixedTemperature",
                        "Modelica.Thermal.HeatTransfer.Sources.PrescribedHeatFlow":
                        "Buildings.HeatTransfer.Sources.PrescribedHeatFlow"})

        # Read source file, store the lines and update the content of the lines
        f_sou = open(source_file, 'r')
        lines = list()
        for _, lin in enumerate(f_sou):
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
            Modelica libraries. 

            In the top-level directory of the
            destination library, this function creates the file
            `.copiedFiles.txt` that lists all files that have been
            copied. In subsequent calls, this function
            deletes all files listed in `.copiedFiles.txt`,
            then merges the libraries, and creates a new version of
            `.copiedFiles.txt`. Therefore, if a model is moved
            in the `Annex60` library, it will also be moved in the
            target library by deleting the old file and copying
            the new file.

            This function will merge all Modelica files,
            Modelica scripts, regression results and images.
            An exception is the file `Annex60/package.mo`, as libraries
            typically have their own top-level package file that contains
            their release notes and version information.

            When copying the files, all references and file names 
            that contain the string `Annex60` will be renamed with 
            the name of the top-level
            directory of the destination library.
            Afterwards, the `package.order` files will be regenerated,
            which allows libraries to have Modelica classes in the same
            directory as are used by the `Annex60` library, as long
            as their name differs.

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

        # Build a list of files that were previously merged.
        # If these file will not be merged again, then we will
        # delete them.
        previouslyCopiedFiles = list()
        if os.path.isfile(copFilPat):
            roo = self._target_home.rsplit(self._new_library_name, 1)[0]
            with open(copFilPat,'r') as fp:
                files = fp.read().splitlines()
                for fil in files:
                    fil = os.path.normpath(fil.rstrip())
                    if not fil.startswith('#'):
                        absFil = os.path.join(roo, fil)
                        if os.path.isfile(absFil):
                            previouslyCopiedFiles.append(fil)

        copiedFiles=list()

        # Location of reference results
        ref_res = os.path.join(self._target_home, "Resources", "ReferenceResults", "Dymola")

        excluded_dirs =  '|'.join([x for x in (self._excluded_packages)]) or r'$.'
        excluded_files = '|'.join(["{}_{}_".format("Annex60", x) for x in (self._excluded_packages)]) or r'$.'

        for root, dirs, files in os.walk(self._annex60_home):
            # Exclude certain folders
            dirs[:] = [os.path.join(root, d) for d in dirs]
            dirs[:] = [d for d in dirs if not re.search(excluded_dirs, d)]

            # Exclude certain files
            files = [os.path.join(root, f) for f in files]
            files = [f for f in files if not re.search(excluded_files, f)]

            for fil in files:
                srcFil=os.path.join(root, fil)
                # Loop over all
                # - .mo files except for top-level .mo file
                # - .mos files
                # - ReferenceResults
                # - OpenModelica/compareVars, as they are autogenerated
                if (not srcFil.endswith(os.path.join("Annex60", "package.mo")) \
                    or srcFil.endswith("legal.html"))\
                    and os.path.join("OpenModelica", "compareVars") not in srcFil:

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

        # Delete the files that were previously merged, but are no longer in Annex60.
        # First, remove from the list the files that were copied just now
        for fil in copiedFiles:
            filNam = self._new_library_name + fil.split(self._target_home)[1]
            if previouslyCopiedFiles.count(filNam) > 0:
                previouslyCopiedFiles.remove(filNam)
        # Now, remove the files, unless they are no longer in the repository anyway.
        for fil in previouslyCopiedFiles:
            filNam = os.path.join(self._target_home[0: self._target_home.rfind( self._new_library_name )], fil)
            if os.path.isfile(filNam):
                os.remove(filNam)
            
        # Generate package.order files
        r.write_package_order(self._target_home, True)
        # Save a list of all files that were copied.
        with open(copFilPat,'w') as fp:
            fp.write("# Do not edit this file unless you know what you are doing.\n")
            fp.write("# This file is used by the Annex60 merge script and generated by BuildingsPy.\n")
            for fil in sorted(copiedFiles):
                fp.write(self._new_library_name + fil.split(self._target_home)[1] + "\n")
