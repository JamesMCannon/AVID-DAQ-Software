import shutil
import os
import time

##shutil.copy('Release/numpy_extensions.dll','numpy_extensions.pyd')
##time.sleep(1)

##import numpy_extensions as ne
import np_extensions as ne
import numpy as np
import cProfile
import pstats

NUM_TEST = 10
NUM_PROFILE = 1000

def test_multXbyAI():
    a = np.arange(NUM_PROFILE,dtype=np.float)
    b = np.arange(NUM_PROFILE,dtype=np.float)   #make two vectors to compare time
    ne.multXbyAI(b,3.0) #much faster with in-place computation, even with separate array creation (~ 10x faster)

def test_multXbyA():
    a = np.arange(NUM_PROFILE,dtype=np.float)
    b = ne.multXbyA(a,3.0)


def test_myMax():
    a = np.arange(NUM_PROFILE,dtype=np.float)
    a[345] = 2000
    (b,m) = ne.myMax(a) #much faster with in-place computation, even with separate array creation (~ 10x faster)

def test_rowMax():
    a = np.array([[1,2,3.0,4],[2,3,5,4]])
    value = np.empty(len(a))
    index = np.empty(len(a))
    ne.rowMax(a,index,value)
    print index, value


def profile():
    save_name = 'profile.txt'


    profile_name = 'processSferic.cprof'
    fd = open(save_name,'w')

    profile_calls = []
    profile_calls.append("for a in xrange(1000):test_multXbyAI() ")
    profile_calls.append("for a in xrange(1000):test_multXbyA() ")
    profile_calls.append("for a in xrange(1000):test_myMax() ")
    profile_calls.append("for a in xrange(1000):test_rowMax() ")

    for profile_call in profile_calls:
        print 'Profiling: %s' % profile_call
        fd.write('Profile call: %s \n' % profile_call)
        cProfile.runctx(profile_call,globals(),locals(),filename = profile_name)
        stats = pstats.Stats(profile_name,stream=fd)
        stats.strip_dirs().sort_stats('time').print_stats(20)
        time.sleep(.2)
    fd.close()
    del fd



if __name__ == '__main__':
##    profile()
    test_rowMax()