''' Test suite for numpyIO

Typically, should be run using 'nosetests -v'

Author: Alan C. Brooks, alancbrooks(noSpam)@gmail.com
'''

from __future__ import with_statement
import numpy as np
from numpyIO import fread, fwrite

def timed(func):
    '''Decorator that prints & returns the time it takes to run a function'''
    import time
    def wrapper(*__args,**__kw):
        start = time.time()
        out = func(*__args,**__kw)
        end = time.time()
        dt = end-start
        print "in %f sec" % dt,
        return (out, dt)
    return wrapper
    
def subReadWrite(a, size, fn, fread, fwrite, what='Some'):
    import os
    print " %s testing .." % what,
    
    # Speed tests
    @timed
    def innerSpeedTestWrite():
        fwrite(fid, size, a)
    @timed
    def innerSpeedTestRead():
        return fread(fid, size, 'd')
    with open(fn,'w+b') as fid:
        tmp, dtW = innerSpeedTestWrite()
    with open(fn,'rb') as fid:
        a1, dtR = innerSpeedTestRead()
    os.remove(fn)
    
    # Test more options
    b = a[:10] # only use a few values for these tests
    with open(fn,'w+b') as fid:
        fwrite(fid, b.size, b, 'd', 1)
        fid.seek(0)
        # all data types: 'bBcS1hHfiIlu4dFD'
        b2 = fread(fid, b.size, 'd', 'f', 1) # convert to floats
        fid.seek(0)
        b3 = fread(fid, b.size, 'd', 'i', 1) # convert to int32
        fid.seek(0)
        b4 = fread(fid, b.size, 'd', 'b', 1) # convert to int8
        fid.seek(0)
        b5 = fread(fid, b.size, 'd', 'h', 1) # convert to int16
    os.remove(fn)
    
    # Finalize stuff
    if all(a == a1) and all(abs(b-b2) < 0.01) and \
       all(abs(b-b3) < 1) and all(abs(b-b4) < 1) and all(abs(b-b5) < 1):
        print ".. passed"
    else:
        print ".. failed"
        print " a=%s\na1=%s\nb2=%s\nb3=%s\nb4=%s\nb5=%s" % (
            a, a1, b2, b3, b4, b5)
    return dtW+dtR

def testFreadFwrite():
    # Unit tests of fread/fwrite
    from scipy.io import numpyio
    import time
    
    n = 10e5 #10e5 for quick dev; 10e6 for longer benchmark
    a = 127*(np.random.random_sample(n)-0.5)
    fn = 'temp.bin'
    dt = []
    print "Testing numpyIO with %d random samples written/read:" % n
    
    # Baseline scipy.io.numpyio
    t1 = subReadWrite(a, a.size, fn, numpyio.fread, numpyio.fwrite, 'numpyio')
    
    # Test this new package numpyIO & compare speed to baseline
    t2 = subReadWrite(a, a.size, fn, fread, fwrite, 'numpyIO')
    
    # Mix the two
    t3 = subReadWrite(a, a.size, fn, fread, numpyio.fwrite, 'numpyIo')
    t4 = subReadWrite(a, a.size, fn, numpyio.fread, fwrite, 'numpyiO')
    
    # Print the relative results
    def printSlower(t1, t2, what1='a', what2='b'):
        speed = ('slower','faster')[t2<t1]
        print " %s is %2d%% %s than %s" % (
            what2, 100*abs(t2-t1)/t1, speed, what1)
    printSlower(t1, t2, "SciPy's numpyio", "numpyIO")
    printSlower(t1, t3, "SciPy's numpyio", "numpyIo")
    printSlower(t1, t4, "SciPy's numpyio", "numpyiO")
        
def testAutoNum():
    import os
    print "Testing auto num feature of numpyIO ..",
    a = np.array((1,2,3),'d')
    fn = 'temp2.bin'
    with open(fn,'w+b') as fid:
        fwrite(fid, -1, a)
        fid.seek(0)
        a1 = fread(fid, -1, 'd')
    os.remove(fn)
    passed = all(a == a1)
    assert passed
    if passed:
        print "passed"
    else:
        print "failed"
        print " a=%s\na1=%s" % (a, a1)

def runAll():
    '''Run all unit tests'''
    testAutoNum()
    testFreadFwrite()
    
if __name__=='__main__':
    from numpy.testing import run_module_suite
    run_module_suite()
