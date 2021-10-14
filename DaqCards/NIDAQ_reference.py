#!/usr/bin/python

"""This module implements a pure Python interface to the NIDAQmxBase
API for interfacing with National Instruments input/output devices."""

import ctypes
import numpy
import re
import atexit
import os

__author__ = "Quentin Smith <quentin@mit.edu>"
__version__ = "0.3"

def _find_library():
    """First try using ctypes to find the nidaqmxbase library, then
    fall back to trying hard-coded paths."""
    import ctypes.util
    f = ctypes.util.find_library("nidaqmxbase")
    if f: return f
    search = ["/usr/local/natinst/nidaqmxbase/lib/libnidaqmxbase.so.2.1.0", "/Library/Frameworks/nidaqmxbase.framework/nidaqmxbase"]
    for f in search:
        if os.path.exists(f):
            return f
    return "nidaqmxbase"

nidaq = ctypes.CDLL(_find_library(), ctypes.RTLD_GLOBAL)

int32 = ctypes.c_long
uInt32 = ctypes.c_ulong
uInt64 = ctypes.c_ulonglong
float64 = ctypes.c_double
TaskHandle = uInt32

DAQmx_Val_Cfg_Default = int32(-1)

DAQmx_Val_RSE = 10083
DAQmx_Val_NRSE = 10078
DAQmx_Val_Diff = 10106

DAQmx_Val_Volts = 10348

DAQmx_Val_Rising = 10280
DAQmx_Val_Falling = 10171

DAQmx_Val_FiniteSamps = 10178
DAQmx_Val_ContSamps = 10123

DAQmx_Val_GroupByChannel = 0
DAQmx_Val_GroupByScanNumber = 1

DAQmx_Val_ChanForAllLines = 1

def chanNumber(chanList):
    """Returns the number of channels in a channel specification or None if the list is malformed."""
    chanNum = 0
    chanMatch = re.compile("Dev(\d+)/\w+(\d+)(:\d+)?")
    for chan in chanList:
	m = chanMatch.match(chan)
	if m is None:
	    return None
        start = m.group(2)
	end = m.group(3)
	if end is not None:
	    chanNum += (int(end)-int(start)+1)
	else:
            chanNum += 1
    return chanNum

def CHK(err):
    """Check the return code of a NIDAQmx Base library call and throw
    an exception if it indicates failure."""
    if err < 0:
        buf_size = 2048
        buf = ctypes.create_string_buffer('\000' * buf_size)
        nidaq.DAQmxBaseGetExtendedErrorInfo(ctypes.byref(buf),buf_size)
        raise RuntimeError('nidaq call failed with error %d: %s'%(err,repr(buf.value)))

class NITask(object):
    def __init__(self):
        self.nidaq = nidaq # Save a copy of nidaq so it's not destroyed before we are
        self.CHK = CHK # ditto
        atexit.register(self.cleanup)
        
	self.taskHandle = TaskHandle(0)

    def start(self):
        self.CHK(self.nidaq.DAQmxBaseStartTask(self.taskHandle))

    def stop(self):
        self.CHK(self.nidaq.DAQmxBaseStopTask(self.taskHandle))
	
    def cleanup(self):
        print "Cleaning up "+str(self)
        if self.taskHandle:
            self.stop()
            self.CHK(self.nidaq.DAQmxBaseClearTask(self.taskHandle))
    __del__ = cleanup
    
class AITask(NITask):
    def __init__(self, min=-10.0, max=10.0,
		 channels=["Dev1/ai0", "Dev1/ai1", "Dev1/ai2", "Dev1/ai3", "Dev1/ai4", "Dev1/ai5", "Dev1/ai6", "Dev1/ai7"],
		 clockSource="OnboardClock", sampleRate=200,
		 samplesPerChan=8, totalSamples=None,
		 timeout=10.0):
        NITask.__init__(self)
        
        self.min = min
	self.max = max
	self.channels = channels
	self.clockSource = clockSource
	self.sampleRate = sampleRate
	self.samplesPerChan = samplesPerChan
	self.totalSamples = totalSamples
	self.timeout = timeout

	self.numChan = chanNumber(channels)

	if self.numChan is None:
	    raise ValueError("Channel specification is invalid")

        chan = ", ".join(self.channels)
	
	self.CHK(self.nidaq.DAQmxBaseCreateTask("",ctypes.byref(self.taskHandle)))
	self.CHK(self.nidaq.DAQmxBaseCreateAIVoltageChan(self.taskHandle, chan, "", DAQmx_Val_RSE, float64(self.min), float64(self.max), DAQmx_Val_Volts, None))
        if self.totalSamples:
            self.CHK(self.nidaq.DAQmxBaseCfgSampClkTiming(self.taskHandle, self.clockSource, float64(self.sampleRate), DAQmx_Val_Rising, DAQmx_Val_FiniteSamps, uInt64(self.totalSamples)))
        else:
            self.CHK(self.nidaq.DAQmxBaseCfgSampClkTiming(self.taskHandle, self.clockSource, float64(self.sampleRate), DAQmx_Val_Rising, DAQmx_Val_ContSamps, uInt64(self.samplesPerChan)))

    def read(self, samplesPerChan=None):
        if samplesPerChan is None:
	    samplesPerChan = self.samplesPerChan
	data = numpy.zeros((samplesPerChan,self.numChan),dtype=numpy.float64)
	nRead = int32()
	self.CHK(self.nidaq.DAQmxBaseReadAnalogF64(self.taskHandle,
                                                   int32(samplesPerChan),float64(self.timeout),
                                                   DAQmx_Val_GroupByScanNumber,
                                                   data.ctypes.data,samplesPerChan*self.numChan,
                                                   ctypes.byref(nRead),None))
	#print "Acquired %d samples for %d channels." % (nRead.value, self.numChan)
        if nRead.value != samplesPerChan:
            print "Expected %d samples! Attempting to resize." % samplesPerChan
            data.resize((nRead.value, self.numChan))
	return data

class AOTask(NITask):
    def __init__(self, min=0.0, max=5.0,
		 channels=["Dev1/ao0"],
		 timeout=10.0):
        NITask.__init__(self)
        
        self.min = min
	self.max = max
	self.channels = channels
	self.timeout = timeout

	self.numChan = chanNumber(channels)

	if self.numChan is None:
	    raise ValueError("Channel specification is invalid")

        chan = ", ".join(self.channels)
	
	self.CHK(self.nidaq.DAQmxBaseCreateTask("",ctypes.byref(self.taskHandle)))
	self.CHK(self.nidaq.DAQmxBaseCreateAOVoltageChan(self.taskHandle, chan, "", float64(self.min), float64(self.max), DAQmx_Val_Volts, None))

    def write(self, data):
	nWritten = int32()
        data = data.astype(numpy.float64)
	self.CHK(self.nidaq.DAQmxBaseWriteAnalogF64(self.taskHandle,
                                                    int32(1), int32(0),
                                                    float64(self.timeout),
                                                    DAQmx_Val_GroupByScanNumber,
                                                    data.ctypes.data,
                                                    ctypes.byref(nWritten),None))
        if nWritten.value != self.numChan:
            print "Expected to write %d samples!" % self.numChan

class DITask(NITask):
    def __init__(self,
		 channels=["Dev1/port0"],
		 timeout=10.0):
        NITask.__init__(self)
        
	self.channels = channels
	self.timeout = timeout

	self.numChan = chanNumber(channels)

	if self.numChan is None:
	    raise ValueError("Channel specification is invalid")

        chan = ", ".join(self.channels)
	
	self.CHK(self.nidaq.DAQmxBaseCreateTask("",ctypes.byref(self.taskHandle)))
	self.CHK(self.nidaq.DAQmxBaseCreateDIChan(self.taskHandle, chan, "", DAQmx_Val_ChanForAllLines, None))

    def read(self):
        byte = uInt32(0)
	self.CHK(self.nidaq.DAQmxBaseReadDigitalScalarU32(self.taskHandle,
                                                          float64(self.timeout),
                                                          ctypes.by_ref(byte),
                                                          None))
        return byte

class DOTask(NITask):
    def __init__(self,
		 channels=["Dev1/port0"],
		 timeout=10.0):
        NITask.__init__(self)
        
	self.channels = channels
	self.timeout = timeout

	self.numChan = chanNumber(channels)

	if self.numChan is None:
	    raise ValueError("Channel specification is invalid")

        chan = ", ".join(self.channels)
	
	self.CHK(self.nidaq.DAQmxBaseCreateTask("",ctypes.byref(self.taskHandle)))
	self.CHK(self.nidaq.DAQmxBaseCreateDOChan(self.taskHandle, chan, "", DAQmx_Val_ChanForAllLines, None))

    def write(self, byte):
	self.CHK(self.nidaq.DAQmxBaseWriteDigitalScalarU32(self.taskHandle,
                                                    int32(1),
                                                    float64(self.timeout),
                                                    uInt32(byte),
                                                    None))

if __name__ == "__main__":
    import time
    testAI = AITask(channels=["Dev1/ai0"])
    testAI.start()
    time.sleep(1)
    for i in xrange(100):
        print testAI.read()
    testAI.stop()
