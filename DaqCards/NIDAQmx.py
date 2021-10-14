# Main wrapper for NiDAQ cards (USB, PCI, PCIe)
# Calls actual daqcard class as subprocess.

import time
from time import sleep
from Queue import Full, Empty
from multiprocessing import Process, Queue, Lock

from DaqCard import *
from DAQExceptions import *

__all__ = ['NIDAQmx', 'DAQ']

class NIDAQmx():
    """
    Starts process to wrap around actual DAQ process.
    
    Init:
    Requires parent to have EngineFlag class and logger
    
    Start will raise DAQStartError if the DAQ does not start up within 60 seconds
    
    Exception Handling:
    Start()             DAQStartError
                            is_running flag not set within timeout, meaning something hung
                                raised within engine.SyncDAQwithGPS(), caught within engine.MainLoop
    Stop()              DAQStopError
                            is_stopped flag not set within 60s
                                raised to be handled in engine
    Get()               DAQNoDataError
                            on queue.get timeout
                                raised, caught by MainLoop
    Restart()
    RestartAnalog()
    RestartLR()         return false on error   
                            these functions are called within eception handlers, so no catching of exceptions
                                return False and caught by checks.
    """
    
    def __init__(self, config, parent, have_gps = True):
    
        self.parent = parent
        self.process = None
        self.config = config
        self.queue = Queue(DAQ.DAQ_QUEUE_SIZE)
        self.messages = Queue(4)
        self.logger = parent.DAQ_logger
        self.have_gps = have_gps

        self.daq_flags = parent.DAQ_flags
        
        self.numHangs = 0
        self.pid = -1
        
        self.logger.info('External trigger?: %s' % str(have_gps))
        
        self.numChannels = self.config.GetIntElemVal("NumChannels")
        self.sampleRate = self.config.GetIntElemVal("SampleRate")

        self.process = Process(target = DAQ_Process, args = (self.config, self.messages, self.queue, self.logger, self.daq_flags, self.have_gps))

        self.process.daemon = True
        self.process.start()
        
        # If DAQ card does not exist, it should fail out really really quickly. This catches that.
        if self.daq_flags.error.wait(5):
            raise DAQInitError('DAQ did not start as expected.')

        # This will hold the rest of the function until the DAQ process has actually finished initialization
        # This should mean that everything went peachy
        self.logger.info("Waiting for DAQ to start...")
        if not self.daq_flags.init.wait(DAQ.DAQ_LR_TURNOFF_TIME + DAQ.DAQ_LR_TURNON_TIME + 30):
            raise DAQInitError('DAQ initialization timed-out')
            
        #self.logger.info('Waiting 40s for init()')
        #sleep(45.0)
        
        self.pid = self.process.pid
        self.logger.info('Initialized on pid: %d' % self.pid)

        
    def Start(self):
        
        #if self.process is not None:
        #    self.Stop()
            
        while not self.queue.empty():
            self.queue.get()
            
        while not self.messages.empty():
            self.messages.get()
        
        self.logger.debug('Sending "START".')
        self.messages.put('START')
        
        if not self.daq_flags.is_running.wait(DAQ.DAQ_LR_TURNOFF_TIME + DAQ.DAQ_LR_TURNON_TIME + 30):
            raise DAQStartError('DAQ did not start as expected')
        
        self.logger.info("DAQ started.")
        
    def Stop(self):
        self.logger.debug('Sending "STOP".')
        self.messages.put('STOP')        
           
        
    def Quit(self):
    
        if self.process is not None:
        
            self.logger.info('DAQ polling process alive?: %s' % str(self.process.is_alive()))
            
            if self.process.is_alive():

                # If DAQ is not already stopped
                if self.daq_flags.is_stopped.is_set():
                    self.logger.warning("DAQ process is already flagged as stopped, but process is still alive.")
                    return
            
                self.logger.debug('sending "QUIT"')
                self.messages.put('QUIT')
                self.process.join(timeout=30.0)
                
                if self.process.is_alive():
                    self.logger.warning("DAQ process join() timedout.")
                    #self.process.terminate()
                    #self.process = None

                while not self.queue.empty():
                    self.queue.get()
                    
                while not self.messages.empty():
                    self.messages.get()
                    
                # if process is still alive, then possible orphaned subprocesses
                self.process.terminate()
                
                self.logger.info('DAQ process terminated')

            self.process = None
        
        else:
            self.logger.warning("DAQ process is already terminated.")
            return
            
        if not self.daq_flags.is_stopped.wait(60):
            raise DAQStopError('DAQ did not terminate within 60 seconds.')
        
        self.logger.status("DAQ process quit() complete")

        
    def Restart(self):
        self.logger.info('Sending "RESTART" to DAQ process.')
        self.messages.put('RESTART')
        sleep(0.1)
        
        # verify restart
        if not self.daq_flags.init.wait(60):
            self.logger.warning('Full restart did not re-init properly.')
            return False
            # Exceptions won't work very well here, since this is run from an exception handler
            #raise DAQInitError('DAQ did not restart as expected after full reset.')
        return True
        
    def RestartAnalog(self):
        self.logger.info('Sending "Restart Analog".')
        self.messages.put('RESTART_A')
        sleep(0.1)

        # verify restart        
        if not self.daq_flags.init.wait(60):
            self.logger.warning('DAQ Analog restart did not re-init properly.')
            return False
            # Exceptions won't work very well here, since this is run from an exception handler
            #raise DAQInitError('DAQ did not restart as expected after full reset.')
        return True
                
    def RestartLineReceiver(self):
        self.logger.info('Sending "Restarting Line Receiver".')
        self.messages.put('RESTART_LR')
        sleep(0.1)
        
        # verify restart
        if not self.daq_flags.init.wait(DAQ.DAQ_LR_TURNOFF_TIME + DAQ.DAQ_LR_TURNON_TIME + 30):
            self.logger.warning('Line Receiver restart did not re-init properly.')
            return False
            # Exceptions won't work very well here, since this is run from an exception handler
            #raise DAQInitError('DAQ did not restart as expected after full reset.')
        return True
                    
    def Get(self, timeout=59):
        """
        Blocks until the next data element in the queue is available.
        """
        # Retrieve the oldest DAQ information block from the queue

        try:
            #self.logger.debug("Timeout is: %d" % timeout)
            return self.queue.get(True,timeout)
        except Empty:
            #self.logger.error('DAQ Queue empty for %s seconds.' % timeout)
            self.numHangs += 1
            #return None
            raise DAQNoDataError("DAQ Queue empty for %s seconds." % timeout)
        except:
            self.logger.error("Some other error getting from DAQ queue.")
            raise DAQError("Some other error getting from DAQ queue.")
        
    def Flush(self):
        self.logger.debug("Flushing DAQ queue")
    
        i = 0
    
        while self.GetQueueSize()>0:
            try:
                self.Get(1)
                i += 1
            except:
                self.logger.error("Exception on Get() while flushing queue.")
                raise

        self.logger.info("Flushed %d from DAQ queue" % i) 
        
    def GetQueueSize(self):
        return self.queue.qsize()
    
    def GetSampleRate(self):
        return self.sampleRate
    
    def GetNumChannels(self):
        return self.numChannels
    
    def GetPID(self):
        return self.pid

def DAQ_Process(config, queue_in, queue_out, logger, flags, have_gps):
    # This function has to be decoupled from the NiDAQmx class
    # Otherwise will cause a pickle error on restart

    # This sets up the DAQ and initialize all I/O pins
    d = DAQ(config, queue_in, queue_out, logger, flags, have_gps)
    
    # Starts the DAQ card
    d.MainLoop()
        
        