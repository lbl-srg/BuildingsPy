#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################
# Script that merges a Modelica library with
# the IBPSA Modelica library.
#
# MWetter@lbl.gov                            2014-04-15
#######################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from io import open

from builtins import object

class IBPSA(object):
    ''' Class that merges a Modelica library with the `IBPSA` library.

        Both libraries need to have the same package structure.

        By default, the top-level packages `Experimental`
        and `Obsolete` are not included in the merge.
        This can be overwritten with the function
        :meth:`~set_excluded_packages`.

    '''
    def __init__(self, ibpsa_dir, dest_dir):
        ''' Constructor.

        :param ibpsa_dir: Directory where the `IBPSA` library is located.
        :param dest_dir: Directory where the library to be updated is located.
        '''
        import os

        # Check arguments
        def isValidLibrary(lib_home):
            import buildingspy.development.regressiontest as t

            try:
                t.Tester().isValidLibrary(lib_home)
            except ValueError as e:
                s = "{!s}\n    Did not do anything.".format(e.args[0])
                raise ValueError(s)

        isValidLibrary(ibpsa_dir)
        isValidLibrary(dest_dir)

        # --------------------------
        # Class variables
        self._src_library_name = os.path.basename(ibpsa_dir)
        self._ibpsa_home=ibpsa_dir
        self._target_home=dest_dir
        # Library name, such as Buildings
        self._new_library_name = os.path.basename(dest_dir)

        # Exclude packages and files
        self.set_excluded_packages(["Experimental", \
                                    "Obsolete"])
        self._excluded_files = [os.path.join(ibpsa_dir, "package.mo"), \
                                os.path.join(ibpsa_dir, "Fluid", "package.mo"), \
                                os.path.join(ibpsa_dir, "legal.html")]

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

        rep = {self._src_library_name:
               self._new_library_name}
        # For the Buildings library, do these additional replacements.
        if self._new_library_name == "Buildings":
            # Update the models that we use from Buildings.HeatTransfer rather
            # than from the MSL
            rep.update({"Modelica.Thermal.HeatTransfer.Sources.PrescribedTemperature":
                        "Buildings.HeatTransfer.Sources.PrescribedTemperature",
                        "Modelica.Thermal.HeatTransfer.Sources.FixedTemperature":
                        "Buildings.HeatTransfer.Sources.FixedTemperature"})

        # Read source file, store the lines and update the content of the lines
        with open(source_file, mode="r") as f_sou:
            lines = list()
            for _, lin in enumerate(f_sou):
                for ori, new in rep.items():
                    lin = lin.replace(ori, new)
                lines.append(lin)
        # Write the lines to the new file
        f_des = open(destination_file, mode="w")
        f_des.writelines(lines)
        f_des.close()


    def merge(self):
        """ Merge all files except the license file and the top-level ``package.mo``

            .. warning:: This method is experimental. Do not use it without
                         having a backup of your code.

            This function merges the `IBPSA` library into other
            Modelica libraries.

            In the top-level directory of the
            destination library, this function creates the file
            `.copiedFiles.txt` that lists all files that have been
            copied. In subsequent calls, this function
            deletes all files listed in `.copiedFiles.txt`,
            then merges the libraries, and creates a new version of
            `.copiedFiles.txt`. Therefore, if a model is moved
            in the `IBPSA` library, it will also be moved in the
            target library by deleting the old file and copying
            the new file.

            This function will merge all Modelica files,
            Modelica scripts, regression results and images.
            An exception is the file `IBPSA/package.mo`, as libraries
            typically have their own top-level package file that contains
            their release notes and version information.

            When copying the files, all references and file names
            that contain the string `IBPSA` will be renamed with
            the name of the top-level
            directory of the destination library.
            Afterwards, the `package.order` files will be regenerated,
            which allows libraries to have Modelica classes in the same
            directory as are used by the `IBPSA` library, as long
            as their name differs.

            A typical usage is
                >>> import buildingspy.development.merger as m
                >>> import os
                >>> home = os.path.expanduser("~")
                >>> root = os.path.join(home, "test")
                >>> ibpsa_dir = os.path.join(root, "modelica", "IBPSA")
                >>> dest_dir = os.path.join(root, "modelica-buildings", "Buildings")
                >>> mer = m.IBPSA(ibpsa_dir, dest_dir) # doctest: +SKIP
                >>> mer.merge()                            # doctest: +SKIP

        """
        import os
        import shutil

        import buildingspy.development.refactor as r

        # path where a list of all copied files is saved
        copFilPat = os.path.join(self._target_home, ".copiedFiles.txt")

        # Build a list of files that were previously merged.
        # If these file will not be merged again, then we will
        # delete them.
        previouslyCopiedFiles = list()
        if os.path.isfile(copFilPat):
            roo = self._target_home.rsplit(self._new_library_name, 1)[0]
            with open(copFilPat, mode="r") as fp:
                files = fp.read().splitlines()
                for fil in files:
                    fil = os.path.normpath(fil.rstrip())
                    if not fil.startswith('#'):
                        absFil = os.path.join(roo, fil)
                        if os.path.isfile(absFil):
                            previouslyCopiedFiles.append(fil)

        copiedFiles=list()


        for root, dirs, files in os.walk(self._ibpsa_home, topdown=True):
            # Exclude certain folders
            dirs[:] = [d for d in dirs if d not in self._excluded_packages]
            dirs[:] = [os.path.join(root, d) for d in dirs]

            # Exclude certain files
            files = [os.path.join(root, f) for f in files]
            files = [f for f in list(files) if f not in self._excluded_files]

            # Location of reference results
            ref_res = os.path.join(self._target_home, "Resources", "ReferenceResults", "Dymola")

            for fil in files:
                srcFil=os.path.join(root, fil)
                # Loop over all
                # - .mo files except for top-level .mo file
                # - .mos files
                # - ReferenceResults
                # - OpenModelica/compareVars, as they are autogenerated
                if os.path.join("OpenModelica", "compareVars") not in srcFil:

                    desFil=srcFil.replace(self._ibpsa_home, self._target_home)
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

                        # Check if the file needs be skipped because it is from an excluded package.
                        skip=False
                        for pac in self._excluded_packages:
                            if "{}_{}".format(self._src_library_name, pac) in base_name:
                                skip=True
                        if not skip:
                            new_file = os.path.join(dir_name,
                                                    base_name.replace(self._src_library_name,
                                                                      self._new_library_name))
                            if not os.path.isfile(new_file):
                                copiedFiles.append(new_file)
                                shutil.copy2(srcFil, new_file)

                    # Copy all other files. This may be images, C-source, libraries etc.
                    else:
                        copiedFiles.append(desFil)
                        shutil.copy2(srcFil, desFil)

        # Delete the files that were previously merged, but are no longer in IBPSA.
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
        with open(copFilPat, mode="w") as fp:
            fp.write("# Do not edit this file unless you know what you are doing.\n")
            fp.write("# This file is used by the IBPSA merge script and generated by BuildingsPy.\n")
            for fil in sorted(copiedFiles):
                fp.write(self._new_library_name + fil.split(self._target_home)[1] + "\n")
