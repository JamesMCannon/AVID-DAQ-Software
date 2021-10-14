import ctypes
#import array
import numpy
from Queue import Full, Empty
from multiprocessing import Process, Queue, Lock
import random
import sys, os, time
from time import sleep
from datetime import datetime

from DAQExceptions import *

if os.name != 'nt':
    time.clock = time.time


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
DAQmx_Val_ChanForAllLines = 1

DAQmx_Val_Falling_Rising = [DAQmx_Val_Falling,DAQmx_Val_Rising]

__all__ = ['DAQ']

    
# NIDAQ Class
class DAQ:
    """
    The NIDAQmx DAQ card class implements an interface to a NIDAQmx DAQ card.
    The interface treats the NIDAQmx DAQ card like the consumer end of a queue
    whose elements are produced by the signal source the DAQ card is acquiring.
    The elements in the queue are lists of channel data.

    It is assumed that the NIDAQmx DAQ card object will be the last serial
    stream to produce a data element each second.  Thus, the NIDAQmx DAQ card
    object accepts an external Event object that other threads (namely, the main
    loop of an Engine object) can use to synchronize their activity.
    
    Exception and Error Handling:
        
        Init()                  Exception
                                    unknown OS             
                                        Not handled
        
        EveryNCallback()        DAQSampleError
                                    Number of samples returned != expected
                                        return _StopAndSignalRestart()
                                RuntimeError
                                    error reading data from driver
                                        return _StopAndSignalRestart()
                                Full
                                    data queue full
                                        noncritical - continue
                                Exception
                                    unexpected error reading data from daq
                                        return _StopAndSignalRestart()
                                    unexpected error repacking data
                                        return _StopAndSignalRestart()
                                    unexpected error putting data into queue
                                        return _StopAndSignalRestart()
        
        _DeviceErrorCheck()      [error #]
                                    if DAQ driver operation illegal, will return error number
                                        _StopAndSignalRestart()
                                        
        **_StopAndSignalRestart() puts None in data queue, raise error flag, and return 0
        
    """

    # =========
    # Constants
    # =========
    
    DAQ_QUEUE_SIZE = 3600 # 60  # APS 4.24.2018
    DAQ_LR_TURNOFF_TIME = 1
    DAQ_LR_TURNON_TIME = 1

    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self, config, queue_in, queue_out, logger, flags, have_gps): 
        """
        Constructs a NIDAQmx DAQ card object according to the supplied XML
        description.  Also accepts an external Event object with which other
        threads (namely, the main loop of an Engine object) can synchronize
        their activity.
        """
        
        # Initialize data members
        self.have_gps = have_gps
        
        #load the shared library
        if os.name == 'nt': #windows
            self.driver = ctypes.windll.nicaiu
        elif os.name == 'posix':    #Linux
            self.driver = ctypes.cdll.LoadLibrary('libnidaqmx.so')
        else:
            raise Exception('Unknown os')

        
        #self.DEBUG_FLAG = os.path.isfile('DAQ_DEBUG_TRUE')

        # Variable to track if process is running
        #*********need to make this thread safe**********
        self.running = False
        
        # Variable to track time difference between DAQ callbacks
        self.lastDAQTime = None

        # Task pointers
        self.ai_task = TaskHandle(0)
        self.ao_task = TaskHandle(1) # Analog outputs
        self.di_task = TaskHandle(2) # Digital Inputs
        self.do_task = TaskHandle(3) # Digital Outputs
        self.counter_task = TaskHandle(4) # Edge counter
##        self.isReady = isReady

        self.dataBuffers = None
        self.queue = queue_out
        self.messages = queue_in
        #self.log = log_queue
        self.logger = logger
        
        self.rawBufferCounter=0  #this is incremented every time new data is appended to the rawBuffer

        # State flags
        self.flags = flags
        
        # Read configuration 
        self.devName = config.GetStrElemVal("DevName")
        self.numChannels = config.GetIntElemVal("NumChannels")
        self.sampleRate = config.GetIntElemVal("SampleRate")
        
        self.singleEnded = config.GetIntElemVal("SingleEndedInput",1)
        
        #this is the number of samples to read (per channel) every time the EveryNSamples callback is called
        if self.sampleRate >= 1000000:
            #self.samplesToRead = 10000        
            #self.samplesToRead = 100000        
            self.samplesToRead = 200000        
        elif self.sampleRate >= 200000:
            self.samplesToRead = 20000
        elif self.sampleRate >= 10000:
            self.samplesToRead=10000 
        elif self.sampleRate >= 1000:
            self.samplesToRead=1000
        elif self.sampleRate >= 100:
            self.samplesToRead = 100
        elif self.sampleRate >= 10:
            self.samplesToRead = 10
        else:
            self.samplesToRead = 1
            
        self.startTriggerName = config.GetStrElemVal("StartTriggerName",'PFI0')  #1pps
        self.startTriggerPolarity = config.GetIntElemVal("StartTriggerPolarity",0)
        self.logger.info("Start Trigger Polarity: %d" % self.startTriggerPolarity)

        self.sampleClockName = config.GetStrElemVal("SampleClockName",'PFI2')    #Sample trigger
        self.sampleClockPolarity = config.GetIntElemVal("SampleClockPolarity",1)
        self.logger.info("Sample Clock Polarity: %d" % self.sampleClockPolarity)
        
        
        self.VOLT_RAIL = config.GetDblElemVal("VoltageRail",5.0)

        self.timePerBuffer = float(self.samplesToRead)/float(self.sampleRate)

        self.bufferLength = self.samplesToRead*self.numChannels
        self.tempBuffer = numpy.zeros(self.bufferLength, dtype=numpy.int16)
        self.rawBuffer = numpy.zeros(self.sampleRate*self.numChannels,dtype = numpy.int16)    #buffer for 1 second of data

        #assert numpy.mod(self.sampleRate,self.samplesToRead)==0, 'Sample rate must be an integer multiple of the buffer size'
        assert self.sampleRate%self.samplesToRead==0, 'Sample rate must be an integer multiple of the buffer size' #remove dependency on numpy
        
        self.numBuffersPerSecond = self.sampleRate/self.samplesToRead
        self.logger.debug('numBuffersPerSecond=%d' % self.numBuffersPerSecond)

        self.logger.debug('Sample: %d; 1PPS: %d' % (self.sampleClockPolarity,self.startTriggerPolarity))

        self.callback_lock = Lock()#make sure only one callback running at a time
        
        self.CALLBACKFUNCTION = ctypes.CFUNCTYPE(uInt32, TaskHandle, int32, uInt32, ctypes.c_void_p)
        self.callbackfn = self.CALLBACKFUNCTION(self.EveryNCallback)

        self.fullcount = 0

        self._name = "NIDAQmx.py"

        try:
            # Device Reset
            if not self._DeviceReset():
                self.flags.error.set()
                return
        except:
            # this catches if the DAQ is not installed or does not exist
            self.flags.error.set()
            return
        
        # Device Self Test
        if not self._DeviceSelfTest():
            self.flags.error.set()            
            return
        
        # Setup Digital IO
        if not self._DeviceDigitalOutputSetup():
            self.flags.error.set()            
            return
            
        # Reset LR power
        if not self._LineReceiverRestart():
            self.flags.error.set()            
            return        
        # Setup device
        if not self._DeviceSetup():
            self.flags.error.set()            
            return
            
        self.logger.status("DAQ Init Complete.")
        #self.ENG_MSG.put('DAQ_READY')
        self.flags.is_stopped.clear()
        self.flags.init.set()
    
    # =======
    # Methods
    # =======

    def MainLoop(self):

        self.logger.debug("Entering DAQ mainloop")
        self.running = True
        
        i = 0 
        # Begin acquiring data
        while self.running:
            #time.sleep(1.0)
            try:
                # Blocks for one second
                message = self.messages.get(timeout=1)
                self.logger.debug("msg: %s" % message)
                
                # Not too concerned with speed there, so staying with if..elif statements
                if message == 'START':
                    self.logger.info("START received.")
                    
                    self.DAQStart()

                elif message == 'STOP':
                    #stop the task
                    self.logger.info("STOP received.")
                    
                    self.DAQStop()

                elif message == 'QUIT':
                    #quit the task
                    self.logger.info("QUIT received.")
                    self.DAQQuit()
                    break                            
                    
                elif message == 'RESTART':
                    # Hard restart entire DAQ
                    self.logger.info("RESTART received.")
                    self.DAQRestart('FULL')
                    self.logger.info("Finished restart operation.")
                    
                elif message == 'RESTART_LR':
                    self.logger.info("RESTART_LR received.")
                    self.DAQRestart('LR')
                    self.logger.info("Line Receiver restarted.")
                    
                elif message == 'RESTART_A':
                    # Restart the analog tasks only
                    self.logger.info("RESTART_A received.")
                    self.DAQRestart('AN')
                    self.logger.info("Analog restarted.")

                else:
                    self.logger.info('Unknown command issued/ignored: "%s"' % message)
                    
            except Empty:
                pass

            i += 1
            
            if i%10 == 0:
                self.logger.debug("Waiting for DAQ command")
        
        if self.flags.is_running.is_set():
            self.logger.debug('DAQ running flag is still set??')
            self.flags.is_running.clear()
            
        # DAQ process is fully stopped
        #self.flags.is_stopped.set()
        if not self.flags.is_stopped.is_set():
            self.logger.debug('DAQ stopped flag is still not set??')
            self.flags.is_stopped.set()
            
        #self.logger.debug('flag cleared')
        self.logger.info('%s: Daq card stopped. ' % self._name)
                
    def DAQStart(self):
        self.flags.init.clear()
        self.flags.is_running.set()
        
        # Start the task
        self._DeviceAnalogStart()
        
    def DAQStop(self):
        self._DeviceAnalogStop()
        self.flags.is_running.clear()
        
        # Stop flag is set at conclusion of mainloop
        self.flags.is_stopped.set()
        
    def DAQQuit(self):
        """
        Terminates execution of the data acquisition.
        """
        if not self.running:
            return  #nothing to do
    
        self.logger.info('Stopping DAQ card tasks.')
    
        self.running= False
        self.flags.is_running.clear()
        self.flags.is_stopped.set()
        
        self.rawBufferCounter=0   #fixed .1*n offset

        # Stop and clear the task
        self._DeviceAnalogStop()
        self._DeviceAnalogClear()
        
        # Clearing buffers
        self.dataBuffers = []
        self.tempBuffer = []
        self.rawBuffer = []
        self.callback_lock = None 
        self.CALLBACKFUNCTION = None
        self.callbackfn = None
        
        #try:
        #    #self.log.put('%s: Daq stopped. ' % self._name,block=False)
        #    self.logger.error('%s: Daq stopped. ' % self._name)
        #except Full:
        #    pass

        #self.logger.info('%s: Daq card stopped. ' % self._name)
        self.logger.status('DAQ card quit() complete')
    
    def DAQRestart(self, arg='FULL'):
        
        self.flags.num_restarts += 1
        self.logger.warning('***This is DAQ restart #%d!!!***' % self.flags.num_restarts)
        
        # Clear any error flags
        if self.flags.error.is_set():
            self.flags.error.clear()
    
        # Reset buffers
        #self.tempBuffer = numpy.zeros(self.bufferLength, dtype=numpy.int16)
        #self.rawBuffer = numpy.zeros(self.sampleRate*self.numChannels,dtype = numpy.int16)    #buffer for 1 second of data
            
        if arg == 'FULL':
            # This is a hard full restart of the DAQ
            
            self.logger.warning("Full Restart of DAQ")
            
            # Clear running flag so that other processes can wait on the flag
            self.flags.is_running.clear()
            self.flags.init.clear()
            
            # Steps:
            # 1 Stop sampling task
            self._DeviceAnalogStop()
            
            # 2 Clear analog task
            self._DeviceAnalogClear()
            
            # 3 Toggle I/O lines to toggle line receiver power
            self._LineReceiverRestart()
            
            # 4 re-setup analog task          
            self._DeviceAnalogSetup()
            
            # 5 re-start analog task 
            # (this is done by engine)
            #self._DeviceAnalogStart()
            
            # set running flag so that other processes can restart
            #self.flags.is_running.set()
            self.flags.init.set()
            
        elif arg == 'LR':
            # This restarts the Line Receiver, 
            # but first we want to pause the DAQ task
            # then restart the DAQ task after reset
            
            self.logger.warning("Restarting Line Receiver...")
            
            # Clear running flag so that other processes can wait on the flag
            self.flags.is_running.clear()
            self.flags.init.clear()
            
            # Steps:
            # 1 Stop sampling task
            self._DeviceAnalogStop()
            
            # 2 Toggle I/O lines to toggle line receiver power
            self._LineReceiverRestart()
            
            # 3 Restart sampling tasks            
            #self._DeviceAnalogStart()
            
            # set running flag so that other processes can restart
            #self.flags.is_running.set()
            self.flags.init.set()
            
        elif arg == 'AN':
            # This restarts the analog tasks only
            self.logger.warning("Restarting DAQ Analog task")

            # Clear running flag so that other processes can wait on the flag
            self.flags.is_running.clear()
            self.flags.init.clear()
            
            # Steps:
            # 1 Stop sampling task
            self._DeviceAnalogStop()
            
            # Maybe need to check if stopped correctly, if not clear and resetup
            
            # 2 re-start analog task
            #self._DeviceAnalogStart()
            
            # set running flag so that other processes can restart
            #self.flags.is_running.set()
            self.flags.init.set()
            
        else:
            self.logger.warning("Unknonwn restart command.")
            pass
        
        
    # ==============
    # Helper Methods
    # ==============

    # questionable or beta
    def _StopAndSignalRestart(self):
        """
        stopping here locks up program? Try only putting None in queue, let Engine stop DAQ
        Also need to pop queue element just in case!
        """
        #self.Stop()
        if self.queue.qsize() > 3:
            self.queue.get()
            
        self.queue.put((None, None))
        
        self.lastDAQTime = None
        
        # set error flag
        self.flags.error.set()
        
        # release lock in case DAQ still runs along
        self.callback_lock.release()
        
        return 0


    def sampleClockCallback(self):
        # function to check if sample trigger has stabilized (not fit for production yet)
        # read counter value
        
        if self.totalCountersRead == 60:
            # Are they stable? If not, keep going
            if (self.totalCounterAverage < 1000000) or (self.totalCounterAverage > 1000000):
                # not ready yet...keep waiting
                self.logger.info("Counter not stable yet. Please wait some more.")
                self.totalCountersRead = 0
                
            else:
                # All good, stop and clear task.
                self._DeviceErrorCheck(self.driver.DAQmxStopTask(self.counter_task))
                self._DeviceErrorCheck(self.driver.DAQmxClearTask(self.counter_task))    
    
    def _LineReceiverRestart(self):
        #self.logger.info("Turning off Board Power.")
        if not self._LineReceiverOff():
            return False
        #sleep(30)

        #self.logger.info("Turning on Board Power.")
        if not self._LineReceiverOn():
            return False
            
        #sleep(30)                
        self.logger.status("LR reset.")
        
        return True
        
    def _LineReceiverOff(self):
        self.logger.debug("Turning off LR Power.")
        byte = 256
        if not self._DeviceErrorCheck(self.driver.DAQmxWriteDigitalScalarU32(self.do_task, int32(1),  float64(10.0), uInt32(byte), None)):
            return False
        
        self.logger.warning("Waiting %ss to turn off board power." % self.DAQ_LR_TURNOFF_TIME)
        sleep(self.DAQ_LR_TURNOFF_TIME)
        
        return True
    
    def _LineReceiverOn(self):
        self.logger.debug("Turning on LR Power.")
        byte = 0
        if not self._DeviceErrorCheck(self.driver.DAQmxWriteDigitalScalarU32(self.do_task, int32(1),  float64(10.0), uInt32(byte), None)):
            return False
        
        self.logger.warning("Waiting %ss for board power stabilization." % self.DAQ_LR_TURNON_TIME)
        sleep(self.DAQ_LR_TURNON_TIME)
        
        return True
        
    def _DeviceSelfTest(self):
        self.logger.info("Running DAQ self test.")
        return self._DeviceErrorCheck(self.driver.DAQmxSelfTestDevice(self.devName))    
    
    def _DeviceReset(self):
        self.logger.info("Resetting DAQ device %s" % self.devName)
        return self._DeviceErrorCheck(self.driver.DAQmxResetDevice(self.devName))
       
    def _DeviceAnalogSetup(self):
    
        self.logger.info("Creating DAQ Task")
        if not self._DeviceErrorCheck(self.driver.DAQmxCreateTask("", ctypes.byref(self.ai_task))):
            return False

        self.logger.info("Setting up /%s/ai0:%d." % (self.devName, self.numChannels-1))
        
        if not self._DeviceErrorCheck(self.driver.DAQmxCreateAIVoltageChan(self.ai_task, "/%s/ai0:%d" % (self.devName, self.numChannels-1), "", DAQmx_Val_Diff, float64(-self.VOLT_RAIL), float64(self.VOLT_RAIL), DAQmx_Val_Volts, None)):
            return False

        buff_fctr = 2.0
        #buff_fctr = 1.0/10.0 #use for debugging NIDAQ crash
        if not self._DeviceErrorCheck(self.driver.DAQmxCfgInputBuffer(self.ai_task, uInt32(int(self.sampleRate*self.numChannels*buff_fctr)))):
            return False
        
        # external or fake sample trigger
        if self.have_gps:
            self.logger.info('Setup sample clk using GPS timesync')
            if not self._DeviceErrorCheck(self.driver.DAQmxCfgSampClkTiming(self.ai_task, "/%s/%s" % (self.devName, self.sampleClockName), float64(self.sampleRate), DAQmx_Val_Falling_Rising[self.sampleClockPolarity], DAQmx_Val_ContSamps, uInt64(self.sampleRate))):
                return False
                
            # external start trigger
            if not self._DeviceErrorCheck(self.driver.DAQmxCfgDigEdgeStartTrig(self.ai_task, "/%s/%s" % (self.devName, self.startTriggerName), DAQmx_Val_Falling_Rising[self.startTriggerPolarity])):
                return False

        else:
            self.logger.info('Setup sample clk without GPS.')
            if not self._DeviceErrorCheck(self.driver.DAQmxCfgSampClkTiming(self.ai_task, '', float64(self.sampleRate), DAQmx_Val_Rising, DAQmx_Val_ContSamps, uInt64(self.sampleRate))):
                return False

        #Reset counters/buffers
        self.logger.debug("Clearing and resetting all buffers and counters")
        self.lastDAQTime = None
        self.rawBufferCounter = 0    
        self.tempBuffer = numpy.zeros(self.bufferLength, dtype=numpy.int16)
        self.rawBuffer = numpy.zeros(self.sampleRate*self.numChannels,dtype = numpy.int16)    #buffer for 1 second of data
            
        # Setup callback
        return self._DeviceErrorCheck(self.driver.DAQmxRegisterEveryNSamplesEvent(self.ai_task, int32(DAQmx_Val_Acquired_Into_Buffer), int32(self.samplesToRead), uInt32(0), self.callbackfn, None))

    def _DeviceAnalogStop(self):
        # Stop and clear the task
        self.logger.warning("Stopping analog tasks.")
        self.lastDAQTime = None
        return self._DeviceErrorCheck(self.driver.DAQmxStopTask(self.ai_task))

    def _DeviceAnalogStart(self):

        #Reset counters/buffers
        self.lastDAQTime = None
        self.rawBufferCounter = 0    
        self.tempBuffer = numpy.zeros(self.bufferLength, dtype=numpy.int16)
        self.rawBuffer = numpy.zeros(self.sampleRate*self.numChannels,dtype = numpy.int16)    #buffer for 1 second of data
        
        self.logger.info("Starting analog tasks.")
        return self._DeviceErrorCheck(self.driver.DAQmxStartTask(self.ai_task))

    def _DeviceAnalogClear(self):
        self.logger.warning("Clearing analog tasks.")
        self.lastDAQTime = None
        return self._DeviceErrorCheck(self.driver.DAQmxClearTask(self.ai_task))
        
    def _DeviceDigitalOutputSetup(self):
        # Setup motherboard enable signal. Mobo v2.2.1
        """
        P2.0 = FPGA EN
        P2.1 = +5V Digital /EN
        P2.4 = +5V Analog /EN
        P2.6 = =5V Analog /EN
        """

        if not self._DeviceErrorCheck(self.driver.DAQmxCreateTask("", ctypes.byref(self.do_task))):
            return False
        
        self.logger.info("Setting up DAQ Digital Outputs.")
        
        if not self._DeviceErrorCheck(self.driver.DAQmxCreateDOChan(self.do_task, "/%s/port2/line0:7," % (self.devName), "", DAQmx_Val_ChanForAllLines)):
            return False
        
        self.logger.info("Starting up DAQ Digital Outputs.")
        
        return self._DeviceErrorCheck(self.driver.DAQmxStartTask(self.do_task))
    
    
    def _DeviceSetup(self):
        """
        Common to both with and without GPS
        """

        if not self._DeviceSelfTest():
            return False
        
        if not self._DeviceAnalogSetup():
            return False

        self.logger.debug("DAQ Setup Finished.")
    
        return True
    
    def _DeviceErrorCheck(self, error):
        # Checks NIDAQmx calls for errors and reports them

        if error == 0:
            #self.logger.debug("No errors running DAQ command.")
            return True

        errBuffer = ctypes.create_string_buffer('\000' * 0)
        bufferSize = self.driver.DAQmxGetExtendedErrorInfo(ctypes.byref(errBuffer), 0)
        
        errBuffer = ctypes.create_string_buffer('\000' * bufferSize)
        bufferSize = self.driver.DAQmxGetExtendedErrorInfo(ctypes.byref(errBuffer), bufferSize)
        
        #errString = 'DAQError %d: %s' % (error , repr(errBuffer.value))
        errString = '\n  DAQError: %d\n    %s\n' % (error , errBuffer.value.replace("\n\n", "\n").replace("\n", "\n    "))
        
        #self.log.put(errString)
        #self.logger.error(errString)
        
        if error > 0:
            self.logger.warning('%s    Warning   ' % errString)
            return True
        elif error == -50103:
            # This is when the daq doesn't support selftesting (6034 and 6251)
            # Allow to continue
            self.logger.info('%s    Error non-critical, continuing...' % errString)
            return True
        elif error == -200019:
            # This is error seen when the daq clock skips some ticks and doesn't return data in time,
            # and the engine attempts a restart by clearing the analog task.
            # We'll let the engine continue without raising an exception
            self.logger.info('%s    DAQ clock skipped a beat. Allowing engine restart...' % errString)
            self.flags.resync.set()
            return True
        elif error == -200220:
            # This error is seen when the DAQ requested does not exist.
            self.logger.error('%s    Please check if NIDaq is installed properly or check the NI Testpanel for correct device number' % errString)
            return False
        elif error == -98705 or error == --88705:
            # This error is seen when the DAQ requested does not exist.
            self.logger.error('%s    DAQ is not present.' % errString)
            return False      
        else:
            self.logger.error('%s....Restarting DAQ.' % errString)
            self._StopAndSignalRestart()

    def EveryNCallback(self, taskHandle, everyNSamplesEventType, nSamples, callbackData):

        t_lock_acq = 0
        t_read_data = 0
        t_copy_data = 0
        t_repackage_data = 0
        
        #self.logger.debug("DAQ Callback.")
        
        if not self.running:
            return

        # check how much time to acquire lock (mean collision if high)
        tt1 = time.clock()
        self.callback_lock.acquire()
        t_lock_acq = time.clock() - tt1
        
        if t_lock_acq > self.timePerBuffer:
            self.logger.error('Took too long (%3.2fms) to acquire callback lock' % (t_lock_acq))
            return self._StopAndSignalRestart()

        samplesPerChannelRead=int32(0)

        try:
            tt = time.clock()
            
            self._DeviceErrorCheck(self.driver.DAQmxReadBinaryI16(self.ai_task, self.samplesToRead, float64(10.0), DAQmx_Val_GroupByScanNumber, \
                                                           self.tempBuffer.ctypes.data, self.samplesToRead*self.numChannels, \
                                                           ctypes.byref(samplesPerChannelRead), None))

            t_read_data = time.clock() - tt #for windows systems
            self.rawBufferCounter += 1
            
            # Check if returned buffer is of proper length
            if samplesPerChannelRead.value*self.numChannels != self.bufferLength:
                actual_needed = (samplesPerChannelRead.value*self.numChannels,self.bufferLength)
                raise DAQSampleError('NiDAQ did not return correct number of samples: %d, need %d' % actual_needed)
                
            #append self.samplesToRead samples to the end of self.rawBuffer
            tt = time.clock()
            self.rawBuffer[(self.rawBufferCounter-1)*self.bufferLength:self.rawBufferCounter*self.bufferLength] = self.tempBuffer
##                self.rawBuffer = numpy.concatenate((self.rawBuffer, tempBuffer))
            t_copy_data = time.clock() - tt #for windows systems

            #DEBUG:
#            if random.randint(0,100)==10:
#                raise Exception("Random error")
            
        except RuntimeError:
            self.logger.exception("Exception occurred in reading data from %s driver." % self._name)
            return self._StopAndSignalRestart()

        except DAQSampleError:
            self.logger.exception("Exception occurred in reading data from DAQ")
            return self._StopAndSignalRestart()
            
        except Exception:
            self.logger.exception("Unexpected error occured in %s." % self._name)
            return self._StopAndSignalRestart()
            
        self.logger.debug("DAQ read %d/%d in %dus-%dus-%dus" % (self.rawBufferCounter, self.numBuffersPerSecond, t_lock_acq*100000, t_read_data*100000, t_copy_data*100000))

        #if we've read a second of data, push it onto the queue for post-processing
        if(self.rawBufferCounter == self.numBuffersPerSecond):
##                self.logger.debug('Buffer ready for post-processing.  # Segments = %d' % self.rawBufferCounter)
            self.rawBufferCounter=0
            # Seperate the channels
            self.dataBuffers = []
##                tmp = numpy.frombuffer(self.rawBuffer, numpy.int16, self.numChannels*self.sampleRate, 0)

            tt = time.clock()
            try:
                for i in xrange(self.numChannels):
                    self.dataBuffers.append(self.rawBuffer[i::self.numChannels].copy())
            except Exception, err:
                self.logger.exception("Unexpected error occured while recombining data from DAQ.")
                return self._StopAndSignalRestart()
            t_repackage_data = time.clock() - tt #for windows systems
            self.logger.debug("Repackage data: %f" % (t_repackage_data))
            
            # Get current date/time
            timestamp = datetime.utcnow()
            self.logger.debug("ts: %s" % timestamp)
            
            # Check if full 1s buffer is approx 1 second apart
            daq_time = time.clock()
            
            if self.lastDAQTime is not None:
                #check to see how much time has elapsed:
                etime = daq_time - self.lastDAQTime
                
                
                # this operation takes a while, may create cascading effect! Bump etime up to 1.5 seconds to only trip in extreme cases.
                # theoretically, this would cause a 1/10 second buffer to await readout, maybe cause potential overlap in data somewhere.
                if (etime > (1.0+1.0/self.numBuffersPerSecond)) or (etime < (1.0-1.0/self.numBuffersPerSecond)): 
                    self.logger.error("DAQ delta t out of range: %3.2f seconds" % etime)
                    return self._StopAndSignalRestart()
                else:
                    self.logger.debug('DAQ delta t: %3.6f seconds' % etime)
                    
            self.lastDAQTime = daq_time
            
            #Put the data in the queue
            try:
                # Put a tuple (timestamp, data) into queue
                self.queue.put((timestamp, self.dataBuffers),timeout=0.99)

            except Full:
                self.logger.error("DAQ Data Queue Full")
                return self._StopAndSignalRestart()
                return 0
            except Exception, err:
                self.logger.exception("Unexpected error occured while putting DAQ data in queue.")
                return self._StopAndSignalRestart()
            """
            else:
            
            
                daq_time = time.clock()
                if self.lastDAQTime is not None:
                    #check to see how much time has elapsed:
                    etime = daq_time - self.lastDAQTime
                    self.logger.debug('DAQ block time: %3.2f seconds' % etime)
                    
                    if etime > 1.3: #this operation takes a while, may create cascading effect! Bump etime up to 1.5 seconds to only trip in extreme cases.
                        self.logger.error("Time since last DAQ block: %3.2f seconds" % etime)
                        return self._StopAndSignalRestart()
                        
                self.lastDAQTime = daq_time
            
                self.logger.debug("Repackage data: %f" % (t_repackage_data))
            """

        #self.logger.debug('getBufferData elapsed time: %2.3f' % (time.clock()-tt1))
        self.callback_lock.release()
        return 0

