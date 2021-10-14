"""
python setup_csig_proc.py build_ext --inplace
"""

# from distutils.core import setup
# from distutils.extension import Extension
from setuptools import setup
from setuptools import Extension
from Cython.Distutils import build_ext
import numpy
import os, shutil

shutil.copyfile('csig_proc.py','csig_proc.pyx')

setup(
  name = "csig_proc",
  ext_modules=[
    Extension("csig_proc", ["csig_proc.pyx"],
    include_dirs = [numpy.get_include()])
    ],
  cmdclass = {'build_ext': build_ext}
)