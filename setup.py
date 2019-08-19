import platform
import os
from setuptools import setup
from buildingspy import __version__
# Python setup file.
# See http://packages.python.org/an_example_pypi_project/setuptools.html


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


os_name = platform.system()
lib_data = 'funnel/lib'
if os_name == 'Windows':
    lib_data = '{}/win64/*.dll'.format(lib_data)
elif os_name == 'Linux':
    lib_data = '{}/linux64/*.so'.format(lib_data)
elif os_name == 'Darwin':
    lib_data = '{}/darwin64/*.dylib'.format(lib_data)
else:
    raise RuntimeError('Could not detect standard (system, architecture).')

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
        'future',
        'gitpython',
        'jinja2',
        'matplotlib',
        'numpy',
        'pytidylib',
        'scipy',
        'simplejson',
        'six',
    ],
    packages=[
        'buildingspy',
        'buildingspy/development',
        'buildingspy/examples',
        'buildingspy/fmi',
        'buildingspy/funnel',
        'buildingspy/funnel.bin',
        'buildingspy/io',
        'buildingspy/simulate',
        'buildingspy/thirdParty',
        'buildingspy/thirdParty.dymat',
        'buildingspy/thirdParty.dymat.DyMat',
        'buildingspy/thirdParty.dymat.DyMat.Export',
    ],
    package_data={
        '': ['*.template', 'templates/*', lib_data],
    },
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
