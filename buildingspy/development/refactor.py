#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################
# Script with functions to refactor a Modelica library
#
# MWetter@lbl.gov                            2014-11-23
#######################################################
"""
  This module provides functions to

  * create Modelica packages and autopopulate for example the
    `package.mo` and `package.order` files
  * move Modelica classes include any associated `.mos` scripts,
    reference results and images, and
  * rewrite the `package.order` file.

"""
import os
import re

__all__ = ["create_modelica_package", "move_class", "write_package_order"]

# Constants that are used to properly order models prior to packages in
# the package.order file.
# First, models are listed, then records, then packages and at the end constants.
__MOD = 0
__REC = 1
__PAC = 2
__CON = 3


def _sort_package_order(package_order):
    """ Sort a list of strings that are the entries of the `packager.order` file.

    Each element of the string is an array of the form `[int, 'name']
    where `int` is an integer that is used for the sorting.

    :param package_order: List of strings that are the entries of the `packager.order` file.
    """
    from operator import itemgetter

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

    # Sort models alphabetically

    # Per the Modelica standard,
    # "Classes and constants that are stored in package.mo are also present in package.order
    # but their relative order should be identical to the one in package.mo
    # (this ensures that the relative order between classes and constants stored in different ways is preserved).
    # Therefore, we put in the constants in the original order in which they were.
    # See also https://github.com/lbl-srg/modelica-buildings/pull/1874
    s_con = []
    s_oth = []
    for ele in package_order:
        if ele[0] == __CON:
            # We found a constant
            s_con.append(ele)
        else:
            s_oth.append(ele)

    s = sorted(s_oth, key=itemgetter(1))
    s = sorted(s, key=itemgetter(0))

    # Some items can be files or they can be in an own directory
    # such as UsersGuilde/package.mo
    s = moveItemToFront([__MOD, "Tutorial"], s)
    s = moveItemToFront([__PAC, "Tutorial"], s)
    s = moveItemToFront([__MOD, "UsersGuide"], s)
    s = moveItemToFront([__PAC, "UsersGuide"], s)
    s.extend(s_con)
    s = moveItemToEnd([__PAC, "Data"], s)
    s = moveItemToEnd([__MOD, "Data"], s)
    s = moveItemToEnd([__PAC, "Types"], s)
    s = moveItemToEnd([__MOD, "Types"], s)
    s = moveItemToEnd([__PAC, "Examples"], s)
    s = moveItemToEnd([__PAC, "Validation"], s)
    s = moveItemToEnd([__PAC, "Benchmarks"], s)
    s = moveItemToEnd([__PAC, "Experimental"], s)
    s = moveItemToEnd([__PAC, "Interfaces"], s)
    s = moveItemToEnd([__PAC, "BaseClasses"], s)
    s = moveItemToEnd([__PAC, "Internal"], s)
    s = moveItemToEnd([__PAC, "Obsolete"], s)

    return s


def _sh(cmd, directory):
    """ Run the command ```cmd``` command in the directory ```directory```

    :param cmd: List with the commands as is used in `subprocess.Popen()`.
    :param directory: Directory in which the command is executed.
    """
    import subprocess

    p = subprocess.Popen(cmd, cwd=directory)
    p.communicate()
    if p.returncode != 0:
        raise ValueError("Error: Execution of %s returned %s." % (cmd, p.returncode))


def create_modelica_package(directory):
    """ Create in `directory` a Modelica package.

    If `directory/package.mo` exists, this method returns and does
    nothing. Otherwise, it creates the directory and populates
    it with a `package.mo` and `package.order` file.

    :param directory: The directory in which the package is created.

    """
    dirs = directory.split(os.path.sep)
    fd = ""
    for d in dirs:
        fd = os.path.join(fd, d)
        if not os.path.exists(fd):
            os.makedirs(fd)
        parentPackage = fd[:fd.rfind(os.path.sep)].replace(os.path.sep, ".")
        package_mo = os.path.join(fd, "package.mo")
        # If package.mo does not exist, create it
        if not os.path.exists(package_mo):
            f = open(package_mo, mode="w", encoding="utf-8")
            if d == "Examples":
                s = '''within %s;
package Examples "Collection of models that illustrate model use and test models"
  extends Modelica.Icons.ExamplesPackage;
annotation (preferredView="info", Documentation(info="<html>
<p>
This package contains examples for the use of models that can be found in
<a href=\\"modelica://%s\\">
%s</a>.
</p>
</html>"));
end Examples;
''' % (parentPackage, parentPackage, parentPackage)
            elif d == "Validation":
                s = '''within %s;
package Validation "Collection of validation models"
  extends Modelica.Icons.ExamplesPackage;

annotation (preferredView="info", Documentation(info="<html>
<p>
This package contains validation models for the classes in
<a href=\\"modelica://%s\\">
%s</a>.
</p>
<p>
Note that most validation models contain simple input data
which may not be realistic, but for which the correct
output can be obtained through an analytic solution.
The examples plot various outputs, which have been verified against these
solutions. These model outputs are stored as reference data and
used for continuous validation whenever models in the library change.
</p>
</html>"));
end Validation;
''' % (parentPackage, parentPackage, parentPackage)
            elif d == "BaseClasses":
                s = '''within %s;
package BaseClasses "Package with base classes for %s"
  extends Modelica.Icons.BasesPackage;
annotation (preferredView="info", Documentation(info="<html>
<p>
This package contains base classes that are used to construct the models in
<a href=\\"modelica://%s\\">
%s</a>.
</p>
</html>"));
end BaseClasses;
''' % (parentPackage, parentPackage, parentPackage, parentPackage)
            else:
                s = '''within %s;
package %s "fixme: add brief description"
  extends Modelica.Icons.Package;
annotation (preferredView="info", Documentation(info="<html>
<p>
fixme: add a package description.
</p>
</html>"));
end %s;
''' % (parentPackage, d, d)
            f.write(s)
            f.close()

            # Create the package.order file
            write_package_order(directory=directory, recursive=False)

            # Add the created package.mo file and package.order file to git.
            # This is also needed if a package is created, and then the parent package
            # moved as otherwise, "git mv" will fail as it operates on a file that is not in git
            _sh(cmd=['git', 'add', "package.mo"], directory=fd)
            _sh(cmd=['touch', "package.order"], directory=fd)
            _sh(cmd=['git', 'add', "package.order"], directory=fd)


def _git_move(source, target):
    """ Moves `source` to `target` using `git mv`.

    This method calls `git mv source target` in the current directory.
    It also creates the required subdirectories.

    :param source: Source file.
    :param target: Target file.

    """
    # Due to the recursive calls, this could be invoked to git mv an empty directory.
    # The directory would exist, but has no files in it.
    # In this case, simply delete the empty directory and return
    if os.path.isdir(source) and len(os.listdir(source)) == 0:
        os.rmdir(source)
        return

    # Throw an error if source is not a file that exist.
    if not (os.path.isfile(source) or os.path.isdir(source)):
        raise ValueError("Failed to move file '%s' as it does not exist." %
                         os.path.abspath(os.path.join(os.path.curdir, source)))

    # Throw an error if target is an existing file, except if it is the package.mo file
    if os.path.isfile(target):
        if target.endswith("package.mo"):
            print("*** Warning: Did not move {}.".format(target))
            return
        else:
            raise ValueError("Failed to move '{}' to target '{}' as target already exists.".format(
                os.path.abspath(os.path.join(os.path.curdir, source)),
                os.path.abspath(os.path.join(os.path.curdir, target))))

    # If the destination directory does not exist, create it.
    targetDir = os.path.dirname(target)
    ext = os.path.splitext(target)[1]
    if not os.path.exists(targetDir):
        # Directory does not exist.
        if ext == ".mo":
            # It is a Modelica package.
            # Recursively create and populate it.
            create_modelica_package(targetDir)
        else:
            # Directory does not exist.
            os.makedirs(targetDir)

    _sh(cmd=['git', 'mv', source, target], directory=os.path.curdir)


def get_modelica_file_name(source):
    """ Return for the Modelica class `source` its file name.

    This method assumes the Modelica class is in a file
    with the same name.

    :param source: Class name of the source.
    :return: The file name of the Modelica class.
    """
    return os.path.join(*source.split(".")) + ".mo"


def replace_text_in_file(file_name, old, new, isRegExp=False):
    """ Replace `old` with `new` in file `file_name`.

        If `isRegExp==True`, then old must be a regular expression, and
        `re.sub(old, new, ...)` is called where `...` is each line of the file.
    """
    # Read source file, store the lines and update the content of the lines
    modified = False
    with open(file_name, mode="r", encoding="utf-8-sig") as f_sou:
        lines = list()
        for lin in f_sou:
            if isRegExp:
                lin1 = re.sub(old, new, lin)
            else:
                lin1 = lin.replace(old, new)
            lines.append(lin1)
            if lin1 != lin:
                modified = True
    # Write the lines to the new file
    if modified:
        with open(file_name, mode="w", encoding="utf-8") as f_des:
            f_des.writelines(lines)


def _move_mo_file(source, target):
    """ Move the `.mo` file `sourceFile` to `targetFile` and update its content.

    :param source: Class name of the source.
    :param target: Class name of the target.
    :param sourceFile: Name of the source file.
    :param targetFile: Name of the target file.
    """
    import os

    sourceFile = get_modelica_file_name(source)
    targetFile = get_modelica_file_name(target)

    _git_move(sourceFile, targetFile)
    # The targetFile may have `within Buildings.Fluid;`
    # Update this if needed.

    for fi in [sourceFile, targetFile]:
        di = os.path.dirname(fi)
        write_package_order(directory=di, recursive=False)

    if not os.listdir(os.path.dirname(sourceFile)):
        os.rmdir(os.path.dirname(sourceFile))

    def sd(s): return "within " + s[:s.rfind('.')] + ";"
    replace_text_in_file(targetFile, sd(source), sd(target))
    # Update the class name
    replace_text_in_file(targetFile,
                         " " + source[source.rfind('.') + 1:],
                         " " + target[target.rfind('.') + 1:])


def _move_mos_file(source, target):
    """ Move the `.mos` script `sourceFile` to `targetFile` and its content.

    :param source: Class name of the source.
    :param target: Class name of the target.
    :param sourceMosFile: Name of the source file.
    :param targetMosFile: Name of the target file.
    """
    sourceFile = get_modelica_file_name(source)
    targetFile = get_modelica_file_name(target)

    # mos file name for sourceFile.
    sourceMosFile = source[:source.find(".")] + \
        os.path.sep + \
        os.path.join("Resources", "Scripts", "Dymola") + \
        os.path.sep + \
        os.path.join(*source.split(".")[1:]) + ".mos"

    # mos file for targetFile (if there is a sourceMosFile).
    if not os.path.isfile(sourceMosFile):
        targetMosFile = None
    else:
        sourceFile = get_modelica_file_name(source)
        targetFile = get_modelica_file_name(target)
        targetMosFile = sourceMosFile.replace(os.path.join(*sourceFile.split("/")[1:]),
                                              os.path.join(*targetFile.split("/")[1:]))

    if os.path.isfile(sourceMosFile):
        # Remove the top-level package name from source and target, then
        # replace this in the name of the mos file and move the mos file to
        # its new name.
        _git_move(sourceMosFile,
                  targetMosFile)

        if not os.listdir(os.path.dirname(sourceMosFile)):
            os.rmdir(os.path.dirname(sourceMosFile))

        # Replace the Modelica class name that may be used in simulate.
        replace_text_in_file(targetMosFile, source, target)
        # The result file name is typically the model name.
        # Update this name with the new model name

        def l(s): return s[s.rfind(".") + 1:]
        replace_text_in_file(targetMosFile, l(source), l(target))


def _move_reference_result(source, target):
    """ Move the reference results from the model `source` to `target`.

        If the model `source` has no reference results, then this function
        returns doing nothing.

    :param source: Class name of the source.
    :param target: Class name of the target.

    """
    # Reference result file for sourceFile.
    sourceRefFile = source[:source.find(".")] + \
        os.path.sep + \
        os.path.join("Resources", "ReferenceResults", "Dymola") + \
        os.path.sep + \
        source.replace(".", "_") + ".txt"

    if os.path.isfile(sourceRefFile):
        _git_move(sourceRefFile,
                  sourceRefFile.replace(source.replace(".", "_"),
                                        target.replace(".", "_")))


def _move_openmodelica_script(source, target):
    """ Move the OpenModelica script from the model `source` to `target`.

        If the model `source` has no reference results, then this function
        returns doing nothing.

    :param source: Class name of the source.
    :param target: Class name of the target.

    """
    # Reference result file for sourceFile.
    sourceRefFile = source[:source.find(".")] + \
        os.path.sep + \
        os.path.join("Resources", "Scripts", "OpenModelica", "compareVars") + \
        os.path.sep + \
        source + ".mos"

    if os.path.isfile(sourceRefFile):
        _git_move(sourceRefFile,
                  sourceRefFile.replace(source,
                                        target))


def _move_image_files(source, target):
    """ Move the image files of the model `source` to `target`.

    :param source: Class name of the source.
    :param target: Class name of the target.

    """

    # Name of directory that may contain the image files
    def imgDir(s): return os.path.join(os.path.curdir, "Resources",
                                       "Images", os.path.join(*s.split(".")[1:-1]))
    sourceImgDir = imgDir(source)
    if os.path.isdir(sourceImgDir):
        files = [f for f in os.listdir(sourceImgDir) if os.path.isfile(f)]
        for f in files:
            # This iterates through all files in this directory.
            if os.path.splitext(f) is source[source.rfind(".") + 1:]:
                # This image has the same name (and directory) as the model that needs to be
                # renamed. Hence, move it to the new location.
                _git_move(os.path.join(sourceImgDir, f),
                          os.path.join(imgDir(target), f))


def write_package_order(directory=".", recursive=False):
    """ Write the `package.order` file in the directory `directory`.

        Any existing `package.order` file will be overwritten.

        :param directory: The name of the directory in which the `package.order` file
                          will be written.
        :param recursive: Set to `True` to recursively include all sub directories.

        Usage: To rewrite `package.order` in the current directory, type

        >>> import buildingspy.development.refactor as r
        >>> r.write_package_order(".") #doctest: +ELLIPSIS

    """
    # If there is no package.mo file in this directory, then it is not
    # a Modelica package, and neither are its subdirectories.
    if not os.path.exists(os.path.join(directory, 'package.mo')):
        return

    if recursive:
        s = set()
        for root, _, files in os.walk(directory):
            for fil in files:
                if fil.endswith(".mo"):
                    # Include the directory
                    s.add(root)
    #            srcFil=os.path.join(root, fil)
        if not s:
            s.add(directory)
        for ele in s:
            write_package_order(directory=ele, recursive=False)
    else:
        # Update the package.order file in the current directory.
        files = [f for f in os.listdir(directory)]
        pacLis = list()
        for f in files:
            if os.path.isfile(os.path.join(directory, f)):
                pacLis = pacLis + _get_package_list_for_file(directory, f)

            # Add directories.
            if os.path.isdir(os.path.join(directory, f)):
                # List all files in this directory. If there is at least one
                # file with the .mo extension, then it is a Modelica package.
                pat = os.path.join(directory, f)
                files_in_sub_dir = (fil for fil in os.listdir(pat)
                                    if os.path.isfile(os.path.join(pat, fil)))
                for file_in_sub_dir in files_in_sub_dir:
                    if file_in_sub_dir.endswith(".mo"):
                        pacLis.append([__PAC, f])
                        break

        pacLis = _sort_package_order(pacLis)
        # Write the new package.order file
        with open(os.path.join(directory, 'package.order'), mode="w", encoding="utf-8") as filPac:
            for p in pacLis:
                filPac.write(p[1] + "\n")


def _get_constants(lines):
    """ Get a list with all constants.

    :param: lines All lines of the Modelica file.
    """
    import re
    # Constants can be "constant Real n = ..." or "constant someClass n(..."
    # or "constant Real n[:] = ..." or or "constant Real n[4] = ..."
    # See also https://regex101.com/r/cD5nE0/2 for testing
    f = re.findall(
        r"\s*constant\s+[\w+\.]+\s+(\w+)(\[\w+\]|\[\s*[\w:]\s*(,\s*[\w:]\s*)*\])?\s*[=\(]",
        lines,
        re.MULTILINE)
    r = []
    for ele in f:
        r.append(ele[0])
    return r


def _get_package_list_for_file(directory, file_name):
    """ Gets the package list for the file `directory/file_name`
    """

    pacLis = list()

    if file_name == 'package.mo':
        # Some package.mo files contain a UsersGuide.
        # Add this to the list if needed.
        with open(os.path.join(directory, file_name), mode="r", encoding="utf-8-sig") as fil:
            for line in fil:
                if "package UsersGuide" in line:
                    pacLis.append([__MOD, "UsersGuide"])
                    break
        # Some package.mo files contain constants for the whole package.
        # They need to be added to the package.order as well.
        with open(os.path.join(directory, file_name), mode="r", encoding="utf-8-sig") as fil:
            lines = fil.read()
            con = _get_constants(lines)
            for ele in con:
                # Found a constant whose name is in con.group(1)
                pacLis.append([__CON, ele])

            # Some packages contain types, such as
            # type Reset = enumeration(
            #      Disabled   "Disabled",
            #      Parameter   "Use parameter value",
            #      Input   "Use input signal")
            #      "Options for integrator reset"
            #      annotation (
            #      preferedView="info",
            #      Documentation(info="<html>...");
            con = re.findall(r"type\s*(?P<name>\w*)\s*=\s*enumeration", lines, re.MULTILINE)

            for ele in con:
                # Found a constant whose name is in con.group(1)
                pacLis.append([__CON, ele])

    elif file_name.endswith(".mo"):
        # Check the first two lines for "record class_name" as
        # records should be listed after all the models.
        class_name = file_name[:-3]
        recordString = "record %s" % class_name
        with open(os.path.join(directory, file_name), mode="r", encoding="utf-8-sig") as fil:
            typ = __MOD
            for _ in range(2):
                if recordString in fil.readline():
                    typ = __REC
                    break

        pacLis.append([typ, class_name])

    return pacLis


def _move_images_directory(source, target):
    """ Move the directory with the images if it exists.

    Both arguments need to be package names
    such as `Buildings.Fluid.Sensors`, which are in corresponding
    directories, e.g., in `Buildings/Fluid/Sensors`.

    :param source: Package name of the source.
    :param target: Package name of the target.

    If the package has no images, then this function does nothing
    and returns.
    """

    # source_dir is of the form Buildings.Fluid.Sensors, but the
    # images would be in Buildings/Resources/Images/Fluid/Sensors
    insertion = os.path.sep + os.path.join("Resources", "Images") + os.path.sep

    source_dir = source.replace(".", os.path.sep).replace(os.path.sep, insertion, 1)

    if os.path.isdir(source_dir):
        target_dir = target.replace(".", os.path.sep).replace(os.path.sep, insertion, 1)
        _git_move(source_dir, target_dir)


def _move_class_directory(source, target):
    """ Move the directory `source`, which has a file `source/package.mo`,
    to the `target` name.

    Both arguments need to be package names
    such as `Buildings.Fluid.Sensors`, which are in corresponding
    directories, e.g., in `Buildings/Fluid/Sensors`.

    :param source: Package name of the source.
    :param target: Package name of the target.
    """
    import glob

    source_dir = source.replace(".", os.path.sep)
    target_dir = target.replace(".", os.path.sep)

    # Recursively create the target directory if it does not yet exist
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)

    # Copy the package.mo file if it does not exist in the target
    if not os.path.exists(os.path.join(target_dir, "package.mo")):
        _git_move(os.path.join(source_dir, "package.mo"),
                  os.path.join(target_dir, "package.mo"))

        # If a directory is moved from A/package.mo to A/B/C/package.mo, and B and C are new packages,
        # then A/package.mo and B/package.mo may not exist.
        # Check if they need to be created by calling create_modelica_package for directories
        # A and A/B (A/B/C/package.mo was already copied)
        rec = ""
        for di in target_dir.split(os.path.sep)[:-1]:
            rec = os.path.join(rec, di)
            create_modelica_package(rec)

        # The targetFile may have `within Buildings.Fluid;`
        # Update this if needed.
        def sd(s): return "within " + s[:s.rfind('.')] + ";"
        replace_text_in_file(os.path.join(target_dir, "package.mo"), sd(source), sd(target))
        # Update the class name
        replace_text_in_file(os.path.join(target_dir, "package.mo"),
                             " " + source[source.rfind('.') + 1:],
                             " " + target[target.rfind('.') + 1:])
        # Rename references to this package
        _update_all_references(source, target)

    # Move the package.order file, as it will be recreated
    if os.path.exists(os.path.join(source_dir, "package.order")):
        _git_move(os.path.join(source_dir, "package.order"),
                  os.path.join(target_dir, "package.order"))

    # In Buildings, all classes are in their own .mo file. Hence,
    # we iterate through these files.
    # Iterate through files
    mo_files = [f for f in glob.glob(os.path.join(source_dir, "*.mo"))
                if not f.endswith("package.mo")]
    for fil in mo_files:
        move_class(source + "." + fil[len(source_dir) + 1:-3],
                   target + "." + fil[len(source_dir) + 1:-3])
    # Iterate through directories
    if os.path.exists(source_dir):
        for di in next(os.walk(source_dir))[1]:
            src = ".".join([source, di])
            tar = ".".join([target, di])
            move_class(src, tar)

    # Move the Resources/Images directory
    _move_images_directory(source, target)


def move_class(source, target):
    """ Move the class from the `source`
    to the `target` name.

    Both arguments need to be Modelica class names
    such as `Buildings.Fluid.Sensors.TemperatureTwoPort`,
    or a directory with a top-level `package.mo` file, such as
    `Buildings/Fluid`, that contains a file `Buildings/Fluid/package.mo`.

    :param source: Class name of the source.
    :param target: Class name of the target.

    Usage: Type

        >>> import buildingspy.development.refactor as r
        >>> old = "Buildings.Fluid.Movers.FlowControlled_dp"
        >>> new = "Buildings.Fluid.Movers.Flow_dp"
        >>> r.move_class(old, new) #doctest: +SKIP

    """
    ##############################################################
    # First, remove empty subdirectories
    _remove_empty_folders(source.replace(".", os.path.sep),
                          removeRoot=False)
    ##############################################################
    # Check if it is a directory with a package.mo file
    if os.path.isdir(source.replace(".", os.path.sep)):
        _move_class_directory(source, target)
        return
    ##############################################################
    # Move .mo file
    _move_mo_file(source, target)

    ##############################################################
    # Move .mos file if it exists
    _move_mos_file(source, target)

    ##############################################################
    # Move reference result file if it exists
    _move_reference_result(source, target)

    ##############################################################
    # If there are image files that start with the model name,
    # then these also need to be renamed
    _move_image_files(source, target)

    ##############################################################
    # Move OpenModelica script if present.
    _move_openmodelica_script(source, target)

    _update_all_references(source, target)


def _remove_empty_folders(path, removeRoot=True):
    ''' Remove empty directories
    '''
    if not os.path.isdir(path):
        return

    # remove empty subfolders
    files = os.listdir(path)
    if len(files):
        for f in files:
            fullpath = os.path.join(path, f)
            if os.path.isdir(fullpath):
                _remove_empty_folders(fullpath)

    # if folder empty, delete it
    files = os.listdir(path)
    if len(files) == 0 and removeRoot:
        os.rmdir(path)


def _update_all_references(source, target):
    """ Updates all references in `.mo` and `.mos` files.

    :param source: Class name of the source.
    :param target: Class name of the target.
    """
#    from multiprocessing import Pool

    # Update all references in the mo and mos files
    fileList = list()
    for root, _, files in os.walk(os.path.curdir):
        # Exclude certain folders
        # dirs[:] = [os.path.join(root, d) for d in dirs]
        # dirs[:] = [d for d in dirs if not re.search(excludes, d)]

        for fil in files:
            fileList.append([root, fil, source, target])
    # Update the files
#    pool=Pool(processes=4)
#    pool.map(_updateFile, fileList)    # This can fail with OSError: [Errno 24] Too many open files
            # when moving large packages
    for ele in fileList:
        _updateFile(ele)


def _getShortName(filePath, classPath):
    """Returns the shortest reference to a class within a file.

    Args:
        filePath: file path relative to the library root path (e.g., `Buildings/package.mo`).
        classPath: full library path of the class to be shortened (e.g., `Buildings.Class`).
    """

    pos = re.search(r'\w', filePath).start()
    splFil = filePath[pos:].split(os.path.sep)
    splCla = classPath.split(".")
    shortSource = None
    for i in range(min(len(splFil), len(splCla))):
        if splFil[i] != splCla[i]:
            # See https://github.com/lbl-srg/BuildingsPy/issues/382 for the rationale
            # behind the code below.
            idx_start = i
            if i > 0:
                for k in range(i + 1, len(splFil)):
                    lookup_path = os.path.sep.join(splFil[:k])
                    if splCla[i] in [re.sub(r'\.mo', '', el) for el in os.listdir(lookup_path)]:
                        idx_start = i - 1
                        break
            shortSource = '.'.join(splCla[idx_start:len(splCla)])
            # shortSource starts with a space as instance names are
            # preceded with a space.
            shortSource = ' ' + shortSource
            break
    return shortSource


def _updateFile(arg):
    """ Update all `.mo`, `package.order` and reference result file

        The argument `arg` is a list providing
        [
            the path of the package directory where the file is located, relative
                to the current working directory (e.g., `./Buildings` when working from `~/modelica-buildings/.`),
            the file name (e.g., `package.mo`),
            the full library path of the source class (e.g., `Buildings.SourceClass`),
            the full library path of the target class (e.g., `Buildings.TargetClass`),
        ]

        This function has been implemented as doing the text replace is time
        consuming and hence this is done in parallel.

        :param arg: A list with the arguments.
    """

    root = arg[0]
    fil = arg[1]
    source = arg[2]
    target = arg[3]

    srcFil = os.path.join(root, fil)
    # Loop over all
    # - .mo
    # - package.order
    # - ReferenceResults
    if srcFil.endswith(".mo"):
        # Replace the Modelica class name that may be used in hyperlinks
        # or when instantiating the class.
        # For now, this requires a full class name.
        replace_text_in_file(srcFil, source, target)

        # Replace links to images such as
        # ref=\"modelica://Buildings/Resources/Images/Fluid/Movers/UsersGuide/2013-IBPSA-Wetter.pdf
        src_link = 'modelica://{}/Resources/Images/{}'.format(
            source.split(".")[0], "/".join(source.split('.')[1:]))
        tar_link = 'modelica://{}/Resources/Images/{}'.format(
            target.split(".")[0], "/".join(target.split('.')[1:]))
        replace_text_in_file(srcFil, src_link, tar_link)

        # For example, in Buildings/Fluid/Sources/xx.mo, the model Buildings.Fluid.Sensors.yy
        # may be instantiated as Sensors.yy.
        # Hence, we search for the common packages, remove them from the
        # source name, call this shortSource, and replace this short name
        # with the new name.
        # The same is done with the target name so that short instance names
        # remain short instance names.

        shortSource = _getShortName(srcFil, source)
        shortTarget = _getShortName(srcFil, target)
        if shortSource is None or shortTarget is None:
            return

        # If shortSource is only one class (e.g., "xx" and not "xx.yy",
        # then this is also used in constructs such as "model xx" and "end xx;"
        # Hence, we only replace it if it is
        #   . preceded by empty characters, and
        #   . followed by some optional empty characters and \s or [ or , or ;.
        # (We use a "negative lookbehind assertion" to do so.)
        if "." in shortSource:
            replace_text_in_file(srcFil, shortSource, shortTarget, isRegExp=False)
        else:
            regExpSource = r'(?<!\w)' + shortSource + r'(\s*(\s|\[|,|;))'
            regExpTarget = shortTarget + r'\1'
            replace_text_in_file(srcFil, regExpSource, regExpTarget, isRegExp=True)
        # Replace the hyperlinks, without the top-level library name.
        # This updates for example the RunScript command that points to
        # "....Dymola/Fluid/..."
        def sd(s): return "Resources/Scripts/Dymola/" + s[s.find('.') + 1:].replace(".", "/")
        replace_text_in_file(srcFil, sd(source), sd(target))
    elif srcFil.endswith("package.order"):
        # Update package.order
        write_package_order(os.path.dirname(srcFil))
