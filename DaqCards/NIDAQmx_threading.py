import ctypes
import numpy
from Queue import Queue, Full, Empty
from threading import Thread, Lock
import random
import sys, os, time
from sys import stdout, exc_info
import traceback
if os.name != 'nt':
    time.clock = time.time


__all__ = ['NIDAQmx']

# Typedefs
int32 = ctypes.c_long
uInt32 = ctypes.c_ulong
uInt64 = ctypes.c_ulonglong
float64 = ctypes.c_double
TaskHandle = uInt32

# DAQ constants
DAQmx_Val_Diff = 10106
DAQmx_Val_Volts = 10348
DAQmx_Val_Rising = 10280
DAQmx_Val_Falling = 10171
DAQmx_Val_ContSamps = 10123
DAQmx_Val_GroupByScanNumber = 1
DAQmx_Val_Acquired_Into_Buffer = 1

DAQmx_Val_Falling_Rising = [DAQmx_Val_Falling,DAQmx_Val_Rising]

class NIDAQmx:
    """
    Multithreaded approach
    
    The NIDAQmx DAQ card class implements an interface to a NIDAQmx DAQ card.
    The interface treats the NIDAQmx DAQ card like the consumer end of a queue
    whose elements are produced by the signal source the DAQ card is acquiring.
    The elements in the queue are lists of channel data.

    It is assumed that the NIDAQmx DAQ card object will be the last serial
    stream to produce a data element each second.  Thus, the NIDAQmx DAQ card
    object accepts an external Event object that other threads (namely, the main
    loop of an Engine object) can use to synchronize their activity.
    """

    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self, config, parent):
        """
        Constructs a NIDAQmx DAQ card object according to the supplied XML
        description.  Also accepts an external Event object with which other
        threads (namely, the main loop of an Engine object) can synchronize
        their activity.
        """
        # Initialize data members

        #load the shared library

        if os.name == 'nt': #windows
            self.driver = ctypes.windll.nicaiu
        elif os.name == 'posix':    #Linux
            self.driver = ctypes.cdll.LoadLibrary('libnidaqmx.so')
        else:
            raise Exception("Unknown OS: %s" % os.name)


        self.running = False
        self.thread = None
        self.task = TaskHandle(0)
##        self.isReady = isReady

        self.dataBuffers = None
        self.queue = Queue(30)
        self.rawBufferCounter=0  #this is incremented every time new data is appended to the rawBuffer


        # Read configuration
        self.devName = self.GetStrElemVal(config, "DevName")
        self.numChannels = self.GetIntElemVal(config, "NumChannels")
        self.sampleRate = self.GetIntElemVal(config, "SampleRate")
        if self.sampleRate >= 200000:
            self.samplesToRead = 20000
        elif self.sampleRate >= 10000:
            self.samplesToRead=10000 #this is the number of samples to read (per channel) every
                                     #time the EveryNSamples callback is called
        elif self.sampleRate >= 1000:
            self.samplesToRead=1000
        elif self.sampleRate >= 100:
            self.samplesToRead = 100
        elif self.sampleRate >= 10:
            self.samplesToRead = 10
        else:
            self.samplesToRead = 1

        self.sampleClockName = self.GetStrElemVal(config, "SampleClockName",'PFI2')    #Sample trigger
        self.sampleClockPolarity = self.GetIntElemVal(config,"SampleClockPolarity",1)
        self.startTriggerName = self.GetStrElemVal(config, "StartTriggerName",'PFI0')  #1pps
        self.startTriggerPolarity = self.GetIntElemVal(config,"StartTriggerPolarity",0)
        self.VOLT_RAIL = self.GetDblElemVal(config,"VoltageRail",5.0)

        self.timePerBuffer = float(self.samplesToRead)/float(self.sampleRate)

        self.bufferLength = self.samplesToRead*self.numChannels
        self.tempBuffer = numpy.zeros(self.bufferLength, dtype=numpy.int16)
        self.rawBuffer = numpy.zeros(self.sampleRate*self.numChannels,dtype = numpy.int16)    #buffer for 1 second of data

        assert numpy.mod(self.sampleRate,self.samplesToRead)==0,'Sample rate must be an integer multiple of the buffer size'
        self.numBuffersPerSecond = self.sampleRate/self.samplesToRead

##        print 'Sample: %d; 1PPS: %d' % (self.sampleClockPolarity,self.startTriggerPolarity)

        self.callback_lock = Lock()#make sure only one callback running at a time

        self.CALLBACKFUNCTION = ctypes.CFUNCTYPE(uInt32, TaskHandle, int32, uInt32, ctypes.c_void_p)
        self.callbackfn = self.CALLBACKFUNCTION(self.EveryNCallback)

        self.parent = parent
        self.logger = self.parent.logger
        self.fullcount = 0

        self._name = "NIDAQmx.py"


    # =======
    # Methods
    # =======
    def Start(self):
        """
        Begins execution of the data acquisition in a thread.
        """
        
        #stop if already running:
        if self.running:
            self.Stop()
        
        # Configure the hardware

        #reset device in case previous shutdown was an error
        self.ErrorCheck(self.driver.DAQmxResetDevice(self.devName))

        self.ErrorCheck(self.driver.DAQmxCreateTask("", ctypes.byref(self.task)))

        self.ErrorCheck(self.driver.DAQmxCreateAIVoltageChan(self.task, "/%s/ai0:%d" % (self.devName, self.numChannels-1), "", DAQmx_Val_Diff, float64(-self.VOLT_RAIL), float64(self.VOLT_RAIL), DAQmx_Val_Volts, None))

        self.ErrorCheck(self.driver.DAQmxCfgSampClkTiming(self.task, "/%s/%s" % (self.devName, self.sampleClockName), float64(self.sampleRate), DAQmx_Val_Falling_Rising[self.sampleClockPolarity], DAQmx_Val_ContSamps, uInt64(self.sampleRate)))

        buff_fctr = 2.0
##        buff_fctr = 1.0/10.0 #use for debugging NIDAQ crash
        self.ErrorCheck(self.driver.DAQmxCfgInputBuffer(self.task, uInt32(int(self.sampleRate*self.numChannels*buff_fctr))))

        self.ErrorCheck(self.driver.DAQmxCfgDigEdgeStartTrig(self.task, "/%s/%s" % (self.devName, self.startTriggerName), DAQmx_Val_Falling_Rising[self.startTriggerPolarity]))


        # Launch the thread
        self.thread = Thread(target=self.MainLoop)
        self.thread.start()

    def Stop(self):
        """
        Terminates execution of the data acquisition.
        """
        if not self.running:
            return  #nothing to do
        
        # Shutdown the DAQ card properly
        self.logger.info('%s: Shutting down daq ...' % self._name)
        if self.thread is not None:
            self.running = False            # Kill the thread
            self.thread.join()
            self.thread = None

        # Flush the queue
        while not self.queue.empty():
            self.queue.get()
        self.fullcount = 0
        self.rawBufferCounter=0   #fixed .1*n offset
        
        # Clear the task
        self.ErrorCheck(self.driver.DAQmxClearTask(self.task))
        self.logger.info('%s: Daq stopped. ' % self._name)

    # =========
    # Accessors
    # =========
    def GetNumChannels(self):
        """
        Returns the number of channels.
        """
        # Return the number of channels
        return self.numChannels

    def Get(self):
        """
        Blocks until the next data element in the queue is available.
        """
        # Retrieve the oldest DAQ information block from the queue
##        self.isReady.clear()
        try:
            return self.queue.get(timeout=29)
        except Empty:
            self.logger.error('DAQ Queue empty for 29 seconds.  Returning None to reset.')
            self.parent.numDAQHangs += 1
            return None

    def Flush(self):
        """
        Flushes GPS Queue
        """
        daq = None
        flushcount = 0
        while not self.queue.empty():
            daq = self.Get()
            flushcount += 1
        if flushcount > 0:
            self.logger.warning('DAQ Queue needed flushing: %d entries' % flushcount)
        self.fullcount = 0
        return daq

    def GetAndFlush(self):
        """
        Blocks until the next DAQ data element in the queue is available.  Flush the queue and retrieve the latest element.
        """
        daq = self.Get()
        # Flush the queue
        daq2 = self.Flush()
        if daq2 is None:
            return daq
        else:
            return daq2

    def GetQueueSize(self):
        return self.queue.qsize()

    # ==============
    # Helper Methods
    # ==============
    def ErrorCheck(self, error):
        # Checks NIDAQmx calls for errors and reports them

        if error == 0:
            return

        self.parent.lastError = error

        errBuffer = ctypes.create_string_buffer('\000' * 0)
        bufferSize = self.driver.DAQmxGetExtendedErrorInfo(ctypes.byref(errBuffer), 0)
        errBuffer = ctypes.create_string_buffer('\000' * bufferSize)
        bufferSize = self.driver.DAQmxGetExtendedErrorInfo(ctypes.byref(errBuffer), bufferSize)
        errString = '%s error %d: %s\n' % (self._name, error , repr(errBuffer.value))
        self.logger.error(errString)
        raise RuntimeError(errString)


    def EveryNCallback(self, taskHandle, everyNSamplesEventType, nSamples, callbackData):

        tt = time.clock()
        self.callback_lock.acquire()
        
        if time.clock()-tt > self.timePerBuffer:
            self.logger.warning('Took %3.2f ms to acquire callback lock' % (time.clock()-tt))
            
        samplesPerChannelRead=int32(0)

        try:
##                ttt = time.time()
            self.ErrorCheck(self.driver.DAQmxReadBinaryI16(self.task, self.samplesToRead, float64(10.0), DAQmx_Val_GroupByScanNumber, \
                                                           self.tempBuffer.ctypes.data, self.samplesToRead*self.numChannels, \
                                                           ctypes.byref(samplesPerChannelRead), None))
##                print 'Samples/channel read: %s; time in ReadBinary: %2.4f' % (samplesPerChannelRead.value,time.time()-ttt)

            self.rawBufferCounter += 1
            if samplesPerChannelRead.value*self.numChannels != self.bufferLength:
                actual_needed = (samplesPerChannelRead.value*self.numChannels,self.bufferLength)
                error_string =  'NiDAQ did not return correct number of samples: %d, need %d' % actual_needed
                self.logger.error(error_string)
                raise RuntimeError(error_string)

            #append self.samplesToRead samples to the end of self.rawBuffer
            self.rawBuffer[(self.rawBufferCounter-1)*self.bufferLength:self.rawBufferCounter*self.bufferLength] = self.tempBuffer
##                self.rawBuffer = numpy.concatenate((self.rawBuffer, tempBuffer))

            #DEBUG:
##                if int(np.round(np.random.random(1)[0]*100))==10:
##                    raise Exception("Random error")

        except RuntimeError, err:
            self.driver.DAQmxStopTask(self.task)
            self.logger.error("Exception Occurred in Reading Data from %s driver, Restarting..." % self._name)
            self.callback_lock.release()
            return self.stopAndSignalRestart()

        except Exception, err:
            self.handleUnexpectedException(err)


        #if we've read a second of data, push it onto the queue for post-processing
        if(self.rawBufferCounter == self.numBuffersPerSecond):
##                self.logger.debug('Buffer ready for post-processing.  # Segments = %d' % self.rawBufferCounter)
            self.rawBufferCounter=0
            # Seperate the channels
            self.dataBuffers = []
##                tmp = numpy.frombuffer(self.rawBuffer, numpy.int16, self.numChannels*self.sampleRate, 0)

            try:
                for i in xrange(self.numChannels):
                    self.dataBuffers.append(self.rawBuffer[i::self.numChannels].copy())
            except Exception, err:
                self.handleUnexpectedException(err)

            #Put the data in the queue
            try:
                if self.fullcount > 0:
                    self.queue.put(None, timeout=0.99)
                else:
                    self.queue.put(self.dataBuffers,timeout=0.99)

            except Full:
                self.fullcount += 1
                if self.fullcount == 1:
                    self.logger.error('DAQ Queue was full ( >30 seconds behind! )')
                if self.fullcount > 30:
                    self.callback_lock.release()
                    raise Exception("DAQ Queue Idle for 30 seconds")
            except Exception, err:
                self.handleUnexpectedException(err)

#        self.logger.debug('getBufferData elapsed time: %2.3f' % (time.clock()-tt))
        self.callback_lock.release()
        return 0




    def handleUnexpectedException(self,inst):
        (excType, excValue, excTb) = exc_info()
        self.logger.error('EXCEPTION: %s' % str(excValue))
        trace = "\n"
        for tb in traceback.extract_tb(excTb):
            trace += '\tFile: %s, Line %s in function %s: %s\n'% (tb[0],tb[1],tb[2],tb[3])
        self.logger.error(trace)
        self.logger.critical('Unexpected error in %s: %s.  Traceback:\n %s.\n System check required.' % (self._name, str(excValue),trace))

        self.callback_lock.release()
        return self.stopAndSignalRestart()

    def stopAndSignalRestart(self):
        self.running = False
        self.queue.put(None)
##        self.isReady.set()

        if self.parent:
            self.parent.SignalRestart(())#(True,False) use this as an argument instead to get a hard (python-interpreter-level) restart
        return 0


    def MainLoop(self):
        #register the callback function (CALLBACK)
        self.ErrorCheck(self.driver.DAQmxRegisterEveryNSamplesEvent(self.task, int32(DAQmx_Val_Acquired_Into_Buffer), int32(self.samplesToRead), uInt32(0), self.callbackfn, None))

        # Start the task
        self.ErrorCheck(self.driver.DAQmxStartTask(self.task))

        # Begin acquiring data
        self.running = True
        while self.running:
            time.sleep(1.0)

        # Stop the task
        self.ErrorCheck(self.driver.DAQmxStopTask(self.task))



    def GetStrElemVal(self, config, tag, default = None):
        if default is not None:
            if len(config.getElementsByTagName(tag))==0:
                return default
        child = config.getElementsByTagName(tag)[0].firstChild
        if child is None:
            return '.'
        else:
            return str(child.data)


    def GetIntElemVal(self, config, tag,default = None):
        if default is not None:
            if len(config.getElementsByTagName(tag))==0:
                return default
        child = config.getElementsByTagName(tag)[0].firstChild
        if child is None:
            return 0
        else:
            return int(child.data)


    def GetDblElemVal(self, config, tag,default = None):
        if default is not None:
            if len(config.getElementsByTagName(tag))==0:
                return default
        child = config.getElementsByTagName(tag)[0].firstChild
        if child is None:
            return 0.0
        else:
            return float(child.data)

    def GetPID(self):
        """
        Return 0 to indicate this version has no separate process
        """
        return 0

    def GetSampleRate(self):
        return self.sampleRate
# =========
# Unit Test
# =========
if __name__ == "__main__":
    from xml.dom.minidom import parseString
    from time import ctime
    from threading import Event

    # Create the NIDAQmx DAQ card object
    settings = """\
    <DaqCard module="NIDAQmx">
        <DevName>Dev1</DevName>
        <NumChannels>3</NumChannels>
        <SampleRate>100000</SampleRate>
        <SampleClockName>PFI2</SampleClockName>
        <StartTriggerName>PFI0</StartTriggerName>
    </DaqCard>
    """
##    isReady = Event()
    daq = NIDAQmx(parseString(settings))

    print "Starting DAQ card at %s." % ctime()
    daq.Start()
    print "Started DAQ card at %s." % ctime()
    for i in range(10):
##        isReady.wait()
        data = daq.Get()
        print "Received data at %s." % ctime()

    print "Stopping DAQ card at %s." % ctime()
    daq.Stop()
    print "Stopped DAQ card at %s." % ctime()
