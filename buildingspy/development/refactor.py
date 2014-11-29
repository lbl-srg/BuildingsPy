#!/usr/bin/env python
#######################################################
# Script with functions to refactor a Modelica library
#
# MWetter@lbl.gov                            2014-11-23
#######################################################
import os

class Refactor:
    ''' Class with functions to refactor a Modelica library
        that follows the directory structure and the
        coding convention of the `Annex60` library.

    '''
    def __init__(self):
        ''' Constructor.

        '''

    @staticmethod
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

        FIL=0
        DIR=1

        # Sort models alphabetically
        s = sorted(package_order, key=itemgetter(1))
        s = sorted(s, key=itemgetter(0))

        s = moveItemToFront([FIL, "UsersGuide"], s)
        s = moveItemToEnd([DIR, "Data"], s)
        s = moveItemToEnd([DIR, "Types"], s)
        s = moveItemToEnd([DIR, "Examples"], s)
        s = moveItemToEnd([DIR, "Validation"], s)
        s = moveItemToEnd([DIR, "Experimental"], s)
        s = moveItemToEnd([DIR, "BaseClasses"], s)
        s = moveItemToEnd([DIR, "Interfaces"], s)
        s = moveItemToEnd([DIR, "Internal"], s)
        s = moveItemToEnd([DIR, "Obsolete"], s)

        return s

    @staticmethod
    def _sh(cmd, directory):
        ''' Run the command ```cmd``` command in the directory ```directory```

        :param cmd: List with the commands as is used in `subprocess.Popen()`.
        :param directory: Directory in which the command is executed.
        '''
        import subprocess

        p = subprocess.Popen(cmd, cwd=directory)
        p.communicate()
        if p.returncode != 0:
            raise ValueError("Error: Execution of %s returned %s." % (cmd, p.returncode))


    @staticmethod
    def create_modelica_package(directory):
        ''' Create in `directory` a Modelica package.

        If `directory` exists, this method returns and does
        nothing. Otherwise, it creates the directory and populates
        it with a `package.mo` and `package.order` file.

        :param directory: The directory in which the package is created.
        '''
        dirs = directory.split(os.path.sep)
        fd = ""
        for d in dirs:
            fd = os.path.join(fd, d)
            if not os.path.exists(fd):
                os.makedirs(fd)
                parentPackage = fd[:fd.rfind(os.path.sep)].replace(os.path.sep, ".")
                if d == "Examples":
                    f = open(os.path.join(fd, "package.mo"), "w")
                    s = '''
within %s;
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
                    f.write(s)
                    f.close()
                elif d == "Validation":
                    f = open(os.path.join(fd, "package.mo"), "w")
                    s = '''
within %s;
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
                    f.write(s)
                    f.close()

                else:
                    f = open(os.path.join(fd, "package.mo"), "w")
                    s = '''
within %s;
package %s "fixme: add brief description"
  extends Modelica.Icons.Package;
annotation (preferredView="info", Documentation(info="<html>
<p>
fixme: add a package description.
</p>
</html>"));
end %s;
''' % (parentPackage, d, parentPackage, parentPackage, d)
                    f.write(s)
                    f.close()

                # If the parent directory has no package.order, create it.
                parentPackageOrder = os.path.join(
                    parentPackage.replace(".", os.path.sep), 'package.order')
                if not os.path.isfile(parentPackageOrder):
                    f = open(parentPackageOrder, "w")
                    f.write("d")
                    f.close()

    @staticmethod
    def _git_move(source, target):
        ''' Moves `source` to `target` using `git mv`.

        This method calls `git mv source target` in the current directory.
        It also creates the required subdirectories.

        :param source: Source file.
        :param target: Target file.

        '''
        # Throw an error if source is not a file that exist.
        if not os.path.isfile(source):
            raise ValueError("Failed to move file '%s' as it does not exist." % 
                            os.path.abspath(os.path.join(os.path.curdir, source)))

        # If the destination directory does not exist, create it.
        targetDir = os.path.dirname(target)
        ext       = os.path.splitext(target)[1]
        if not os.path.exists( targetDir ):
            # Directory does not exist.
            if ext == ".mo":
                # It is a Modelica package.
                # Recursively create an populate it.
                Refactor.create_modelica_package(targetDir)
            else:
                # Directory does not exist and it is not a Modelica package.
                # Recursively create it.
                os.makedirs(targetDir)

#fixme: add 'git'
        Refactor._sh(cmd=['mv', source, target], directory=os.path.curdir)

    @staticmethod
    def get_modelica_file_name(source):
        ''' Return for the Modelica class `source` its file name.
        
        This method assumes the Modelica class is in a file
        with the same name.
        
        :param source: Class name of the source.
        :return: The file name of the Modelica class.
        '''
        return os.path.join(*source.split(".")) + ".mo"

    @staticmethod
    def replace_text_in_file(file_name, old, new):
        ''' Replace `old` with `new` in file `file_name`.
        '''
        # Read source file, store the lines and update the content of the lines
        f_sou = open(file_name, 'r')
        lines = list()
        for _, lin in enumerate(f_sou):
            lin = lin.replace(old, new)
            lines.append(lin)
        f_sou.close
        # Write the lines to the new file
        f_des = open(file_name, 'w')
        f_des.writelines(lines)
        f_des.close()


    @staticmethod
    def _move_mo_file(source, target):
        ''' Move the `.mo` file `sourceFile` to `targetFile` and update its content.
        
        :param source: Class name of the source.
        :param target: Class name of the target.
        :param sourceFile: Name of the source file.
        :param targetFile: Name of the target file.
        '''
        sourceFile = Refactor.get_modelica_file_name(source)
        targetFile = Refactor.get_modelica_file_name(target)

        Refactor._git_move(sourceFile, targetFile)
        # The targetFile may have `within Buildings.Fluid;`
        # Update this if needed.
        sd = lambda s: "within " + s[:s.rfind('.')] + ";"
        Refactor.replace_text_in_file(targetFile, sd(source), sd(target))
        # Update the class name
        Refactor.replace_text_in_file(targetFile,
                                  " " + source[source.rfind('.')+1:],
                                  " " + target[target.rfind('.')+1:])

    @staticmethod
    def _move_mos_file(source, target):
        ''' Move the `.mos` script `sourceFile` to `targetFile` and its content.

        :param source: Class name of the source.
        :param target: Class name of the target.
        :param sourceMosFile: Name of the source file.
        :param targetMosFile: Name of the target file.
        '''
        sourceFile = Refactor.get_modelica_file_name(source)
        targetFile = Refactor.get_modelica_file_name(target)
        
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
            sourceFile = Refactor.get_modelica_file_name(source)
            targetFile = Refactor.get_modelica_file_name(target)
            targetMosFile = sourceMosFile.replace(os.path.join(*sourceFile.split("/")[2:]),
                                                  os.path.join(*targetFile.split("/")[2:]))

        if os.path.isfile(sourceMosFile):
            # Remove the top-level package name from source and target, then
            # replace this in the name of the mos file and move the mos file to
            # its new name.
            Refactor._git_move(sourceMosFile,
                           targetMosFile)
            # Replace the Modelica class name that may be used in simulate.
            Refactor.replace_text_in_file(targetMosFile, source, target)
            # The result file name is typically the model name.
            # Update this name with the new model name
            l = lambda s: s[s.rfind(".")+1:]
            Refactor.replace_text_in_file(targetMosFile, l(source), l(target))


    @staticmethod
    def _move_reference_result(source, target):
        ''' Move the reference results from the model `source` to `target`.
        
            If the model `source` has no reference results, then this function
            returns doing nothing.
            
        :param source: Class name of the source.
        :param target: Class name of the target.

        '''
        # Reference result file for sourceFile.
        sourceRefFile = source[:source.find(".")] + \
            os.path.sep + \
            os.path.join("Resources", "ReferenceResults", "Dymola") + \
            os.path.sep + \
            source.replace(".", "_") + ".txt"

        if os.path.isfile(sourceRefFile):
            Refactor._git_move(sourceRefFile,
                           sourceRefFile.replace(source.replace(".", "_"),
                                                 target.replace(".", "_")))

    @staticmethod
    def _move_image_files(source, target):
        ''' Move the image files of the model `source` to `target`.
        
        :param source: Class name of the source.
        :param target: Class name of the target.

        '''

        # Name of directory that may contain the image files
        imgDir = lambda s: os.path.join(os.path.curdir, "Resources", "Images", os.path.join(*s.split(".")[1:-1]))
        sourceImgDir = imgDir(source)
        if os.path.isdir(sourceImgDir):
            files = [f for f in os.listdir( sourceImgDir ) if os.path.isfile(f)]
            for f in files:
                # This iterates through all files in this directory.
                if os.path.splitext(f) is source[source.rfind(".")+1:]:
                    # This image has the same name (and directory) as the model that needs to be
                    # renamed. Hence, move it to the new location.
                    Refactor._git_move(os.path.join(sourceImgDir, f),
                                       os.path.join(imgDir(target), f))


    @staticmethod
    def write_package_order(directory):
        ''' Write the `package.order` file in the directory `directory`.
        
            Any existing `package.order` file will be overwritten.
            
            :param directory: The name of the directory in which the `package.order` file
                              will be written.
        
        '''
        files = [f for f in os.listdir( directory )]
        pacLis = list()
        FIL=0
        DIR=1
        for f in files:
            if os.path.isfile(os.path.join(directory, f)):
                if f.endswith(".mo") and (not f == 'package.mo'):
                    pacLis.append([FIL, f[:-3]])
                if f == 'package.mo':
                    # Some package.mo file contain a UsersGuide.
                    # Add this to the list if needed.
                    with open(os.path.join(directory, f), 'r') as fil:
                        for line in fil:
                            if "package UsersGuide" in line:
                                pacLis.append([FIL, "UsersGuide"])
                                break
            # Add directories.
            if os.path.isdir(os.path.join(directory, f)):
                pacLis.append([DIR, f])
        
        pacLis = Refactor._sort_package_order(pacLis)
        # Write the new package.order file
        filPac = open(os.path.join(directory, 'package.order'), 'w')
        for p in pacLis:
            filPac.write(p[1] + "\n")
        filPac.close()

    
    @staticmethod
    def moveClass(source, target):
        ''' Move the class from the `source`
        to the `target` name.

        Both arguments need to be Modelica class names
        such as `Buildings.Fluid.Sensors.TemperatureTwoPort`.

        :param source: Class name of the source.
        :param target: Class name of the target.

        '''
        ##############################################################
        # Move .mo file
        Refactor._move_mo_file(source, target)
        
        ##############################################################
        # Move .mos file if it exists
        Refactor._move_mos_file(source, target)

        ##############################################################
        # Move reference result file if it exists
        Refactor._move_reference_result(source, target)

        ##############################################################
        # If there are image files that start with the model name,
        # then these also need to be renamed
        Refactor._move_image_files(source, target)

        # Update all references in the mo and mos files
        for root, _, files in os.walk(os.path.curdir):
            # Exclude certain folders
#            dirs[:] = [os.path.join(root, d) for d in dirs]
#            dirs[:] = [d for d in dirs if not re.search(excludes, d)]

            for fil in files:
                srcFil=os.path.join(root, fil)
                # Loop over all
                # - .mo
                # - package.order
                # - ReferenceResults
                if fil.endswith(".mo"):
                    # Replace the Modelica class name that may be used in hyperlinks
                    # or when instantiating the class.
                    # For now, this requires a full class name.
                    Refactor.replace_text_in_file(srcFil, source, target)
                    # Replace the hyperlinks, without the top-level library name.
                    # This updates for example the RunScript command that points to
                    # "....Dymola/Fluid/..."
                    sd = lambda s: "Resources/Scripts/Dymola/" + s[s.find('.')+1:].replace(".", "/")
                    Refactor.replace_text_in_file(srcFil, sd(source), sd(target))
                elif fil.endswith("package.order"):
                    # Update package.order
                    Refactor.write_package_order(os.path.dirname(srcFil))
