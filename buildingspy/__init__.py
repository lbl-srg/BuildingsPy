"""
:mod:`buildingspy` Modules for post-processing simulation output files
======================================================================
"""

import os

# Version.
version_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'VERSION'))
with open(version_path) as f:
    __version__ = f.read().strip()

class BuildingsPy:
    """Class with static methods that are used in various modules.

    """
    @staticmethod
    def getModelicaPathSeparator():
        ''' Returns the `MODELICAPATH` separator, which is `;` on Windows and `:` otherwise.
        '''
        import platform
        return ';' if platform.system() == 'Windows' else ':'
