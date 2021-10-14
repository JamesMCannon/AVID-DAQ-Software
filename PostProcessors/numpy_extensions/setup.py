# from distutils.core import setup, Extension
# try:
from setuptools import setup
from setuptools import Extension
# except ImportError:
#     from distutils.core import setup
#     from distutils.extension import Extension

import numpy


#Windows:
# If have visual studio 2003 installed (optimal for python25)
# setup.py build
# If have mingw installed (suboptimal)
# setup.py build -c mingw32
# then get np_extensions.pyd file in build directory and copy to parent directory
# #
#Linux:

module1 = Extension('np_extensions',
                    sources = ['np_extensions.cpp'],
                    include_dirs = ['.'])

setup (name = 'NumpyExtensions',
       version = '1.1',
       description = 'Helper functions to receiver program',
       include_dirs = [numpy.get_include()],
       ext_modules = [module1])