import io
import platform
import os
from setuptools import setup

# Python setup file.
# See http://packages.python.org/an_example_pypi_project/setuptools.html

MAIN_PACKAGE = 'buildingspy'
PACKAGE_PATH =  os.path.abspath(os.path.join(os.path.dirname(__file__), MAIN_PACKAGE))

# Version.
version_path = os.path.join(PACKAGE_PATH, 'VERSION')
with open(version_path) as f:
    VERSION = f.read().strip()

# Readme.
readme_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'README.rst'))
with io.open(readme_path, encoding='utf-8') as f:  # io.open for Python 2 support with encoding
    README = f.read()

setup(
    name=MAIN_PACKAGE,
    version=VERSION,
    author="Michael Wetter",
    author_email="mwetter@lbl.gov",
    description=(
        "Package for simulating and testing models from the Modelica Buildings and IBPSA libraries"),
    long_description=README,
    long_description_content_type='text/x-rst',
    license="3-clause BSD",
    keywords="modelica dymola openmodelica mat",
    url="http://simulationresearch.lbl.gov/modelica/",
    python_requires='>=3.8',
    install_requires=[
        'gitpython>=3.1.33',
        'jinja2>=2.10',
        'matplotlib>=3.5',
        'numpy>=1.21',
        'scipy>=1.7',
        'pytidylib>=0.3.2',
        'simplejson>=3.16',
        'six>=1.14',
        'pyfunnel>=0.3.0',
        'PyYAML>=5.4',
        'cerberus>=1.3.4',
    ],
    packages=[
        MAIN_PACKAGE,
        'buildingspy/development',
        'buildingspy/examples',
        'buildingspy/fmi',
        'buildingspy/io',
        'buildingspy/simulate',
        'buildingspy/thirdParty',
        'buildingspy/thirdParty.dymat',
        'buildingspy/thirdParty.dymat.DyMat',
        'buildingspy/thirdParty.dymat.DyMat.Export',
    ],
    include_package_data=True,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.8",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Topic :: Utilities",
    ],
)
