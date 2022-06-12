"""
pyGDML setup.py file. Install with python setup.py
"""

import sys
import re
import os
import os.path
import pathlib
import pkg_resources as pk
from setuptools import setup

# get_version and conditional adding of pytest-runner
# are taken from 
# https://github.com/mark-adams/pyjwt/blob/b8cc504ee09b4f6b2ba83a3db95206b305fe136c/setup.py

def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    with open(os.path.join(package, '__init__.py'), 'rb') as init_py:
        src = init_py.read().decode('utf-8')
        return re.search("__version__ = ['\"]([^'\"]+)['\"]", src).group(1)

version = get_version('pygdml')

long_description = """GDML, the geometry description markup language is an open\ 
format wich allows to serialize complex geometries and is typically \
used within the physics community through ROOT and Geant4 libraries.\
This package allows geometry manipulation on the gdml file level."""

#parse the requirements.txt file
# FIXME: this might not be the best way
install_requires = []
with pathlib.Path('requirements.txt').open() as requirements_txt:
    for line in requirements_txt.readlines():
        if line.startswith('#'):
            continue
        try:
            req = str([j for j in pk.parse_requirements(line)][0])
        except Exception as e:
            print (f'WARNING: {e} : Can not parse requirement {line}')
            continue
        install_requires.append(req)

#requirements.append("tables>=3.3.0") # problem with travis CI, removed from requirments.txt

tests_require = [
    'pytest>=3.0.5',
    'pytest-cov',
    'pytest-runner',
]

needs_pytest = set(('pytest', 'test', 'ptr')).intersection(sys.argv)
setup_requires = ['pytest-runner'] if needs_pytest else []
#setup_requires += ["matplotlib>=1.5.0"]

setup(name='pygdml',
      version=version,
      python_requires='>=3.6.0',
      description='Manipulate gdml files',
      long_description=long_description,
      author='Achim Stoessl',
      author_email="achim.stoessl@gmail.com",
      url='https://github.com/achim1/pyGDML',
      install_requires=install_requires, 
      setup_requires=setup_requires,
      license="GPL",
      platforms=["Ubuntu 20.04", "Ubuntu 22.04"],
      classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.8",
        "Topic :: Scientific/Engineering :: Physics"
              ],
      keywords=["geometry", "description",\
                "hep", "particle physics"\
                "astrophysics", "CAD", "Geant4",\
                "GDML", "gdml"],
      tests_require=tests_require,
      packages=['pygdml'],
      #scripts=[],
      #package_data={'pyGDML': [ 'utils/PATTERNS.cfg',\
      #                          "icecube_goodies/geometry_ic86.h5"]}
      )
