import os
from setuptools import setup
# Python setup file.
# See http://packages.python.org/an_example_pypi_project/setuptools.html

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "buildingspy",
    version = "1.6.0",
    author = "Michael Wetter",
    author_email = "mwetter@lbl.gov",
    description = ("Package for simulating and testing models from the Modelica Buildings and IBPSA libraries"),
    long_description = read('buildingspy/README.rst'),
    license = "3-clause BSD",
    keywords = "modelica dymola openmodelica mat",
    url = "http://simulationresearch.lbl.gov/modelica/",
    install_requires = ['future',
                        'pytidylib',
                        'gitpython'],
    packages = ['buildingspy',
                'buildingspy/development',
                'buildingspy/examples',
                'buildingspy/fmi',
                'buildingspy/io',
                'buildingspy/simulate',
                'buildingspy/thirdParty',
                'buildingspy/thirdParty.dymat',
                'buildingspy/thirdParty.dymat.DyMat',
                'buildingspy/thirdParty.dymat.DyMat.Export'],
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Topic :: Utilities"
    ],
)
