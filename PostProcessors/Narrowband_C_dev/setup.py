# from distutils.core import setup,
from setuptools import setup
from setuptools import Extension

module1 = Extension('nbmodule',sources=['nbmodule.cpp','MIXER.cpp', 'FIR.cpp', 'MSK.cpp', 'PHASE.cpp', 'AMP.cpp'])

setup(name = 'nbmodule',
        version = '1.1', 
        description = 'continuous narrowband filtering module', 
        ext_modules = [module1])


#extra_compile_args = ["-O4"]  # You could put "-O4" etc. here.
