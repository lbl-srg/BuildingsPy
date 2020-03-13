import platform
import os
from setuptools import setup
from buildingspy import __version__
# Python setup file.
# See http://packages.python.org/an_example_pypi_project/setuptools.html


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="buildingspy",
    version=__version__,
    author="Michael Wetter",
    author_email="mwetter@lbl.gov",
    description=(
        "Package for simulating and testing models from the Modelica Buildings and IBPSA libraries"),
    long_description=read('README.rst'),
    license="3-clause BSD",
    keywords="modelica dymola openmodelica mat",
    url="http://simulationresearch.lbl.gov/modelica/",
    install_requires=[
        'future>=0.16',
        'gitpython>=2.1',
        'jinja2>=2.10',
        'matplotlib>=2.2',
        'numpy>=1.14',
        'pytidylib>=0.3.2',
        'scipy>=1.1',
        'simplejson>=3.14',
        'six>=1.11',
    ],
    dependency_links=[
        'git+https://github.com/lbl-srg/funnel.git@issue42_syslogCheck#egg=package-0.1.0',
    ],
    packages=[
        'buildingspy',
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
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Topic :: Utilities",
    ],
)
