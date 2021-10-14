import numpy
import time
import random #just for debugging purposes
from Queue import Queue,Empty
from threading import Thread

__all__ = ['VirtualCard']

class DAQError(Exception):
    pass

class VirtualCard:
    """
    The VirtualCard DAQ card class implements a DAQ card in software.  The
    interface treats the software DAQ card like the consumer end of a queue
    whose elements are produced by the signal source the software DAQ card is
    internally generating.  The elements in the queue are lists of channel data.

    It is assumed that the software DAQ card object will be the last serial
    stream to produce a data element each second.  Thus, the NIDAQmx DAQ card
    object accepts an external Event object that other threads (namely, the main
    loop of an Engine object) can use to synchronize their activity.
    
    The VirtualCard DAQ card requires an external OnePPSSignal object to
    synchronize its internal data generation with.
    """

    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self, config, isReady, onePPS, parent):
        """
        Constructs a software DAQ card object according to the supplied XML
        description.  Also accepts an external Event object with which other
        threads (namely, the main loop of an Engine object) can synchronize
        their activity.  Additionally accepts an external OnePPSSignal object
        by which it can synchronize its data generation with other
        software-based serial streams.
        """
        # Initialize data members
        self.running = False
        self.thread = None
        self.isReady = isReady
        self.onePPS = onePPS
        self.config = config
        self.bufferLength = None
        self.rawBuffer = None
        self.dataBuffers = None
        
        self.queue = Queue(4)
        
        self.parent = parent
        self.logger = parent.DAQ_logger
        

        self.InitBuffers()

        print "initialized virtualcard"

    def InitBuffers(self):    
        # Read configuration
        self.numChannels = self.GetIntElemVal(self.config, "NumChannels")
        self.logger.debug("NumChannels: %d" % self.numChannels)
        self.sampleRate = self.GetIntElemVal(self.config, "SampleRate")
        self.logger.debug("SampleRate: %d" % self.sampleRate)
         
        #this is the number of samples to read (per channel) every time the EveryNSamples callback is called
        if self.sampleRate >= 1000000:
            self.samplesToRead = 100000        
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
            
        self.timePerBuffer = float(self.samplesToRead)/float(self.sampleRate)

        self.bufferLength = self.samplesToRead*self.numChannels
        self.logger.debug("bufferlength: %d" %self.bufferLength)
        
        self.tempBuffer = numpy.zeros(self.bufferLength, dtype=numpy.int16)
        self.rawBuffer = numpy.zeros(self.sampleRate*self.numChannels, dtype = numpy.int16)    #buffer for 1 second of data
        
        self.rawBufferCounter = 0
        
        assert numpy.mod(self.sampleRate,self.samplesToRead)==0,'Sample rate must be an integer multiple of the buffer size'
        self.numBuffersPerSecond = self.sampleRate/self.samplesToRead
            

        
    # =======
    # Methods
    # =======
    def Start(self):
        """
        Begins execution of the data generation in a thread.
        """
        # Allocate memory for buffers
        #self.bufferLength = self.sampleRate * self.numChannels
        #self.rawBuffer = numpy.zeros((self.bufferLength), dtype=numpy.int16)

        self.InitBuffers()
        
        # Launch the thread
        self.thread = Thread(target=self.MainLoop)
        self.thread.start()

    def Stop(self):
        """
        Terminates execution of the data generation.
        """
        # Shutdown the DAQ card properly
        if self.thread is not None:
            self.running = False            # Kill the thread
            self.thread.join()
            self.thread = None

        # Flush the queue
        while not self.queue.empty():
            self.queue.get()

    # =========
    # Accessors
    # =========
    def GetNumChannels(self):
        """
        Returns the number of channels.
        """
        # Return the number of channels
        return self.numChannels

    def Get(self, timeout=59):
        """
        Loops until the next data element in the queue is available, or
        when the engine stops/restarts
        """
        # Retrieve the oldest GPS information block from the queue
        self.isReady.clear()
        item = None
        while item==None:
            try:
                item = self.queue.get(True, timeout)
            except Empty:
                item = None
            if self.parent.restarting:
                break
        return item

    def GetQueueSize(self):
        return self.queue.qsize()
    
    def GetSampleRate(self):
        return self.sampleRate
    
    def GetNumChannels(self):
        return self.numChannels
    
    def GetPID(self):
        return self.pid

        
        
    # ==============
    # Helper Methods
    # ==============
    def MainLoop(self):
    
        # Begin acquiring data
        self.running = True
        self.firstRun = True
        count = 0
        try:
            while self.running:
            
                t_lock_acq = 0
                t_read_data = 0
                t_repackage_data = 0
                
                #These 2 lines are just for exception handling/engine restart testing
                #if random.random() < .3334:
                #    raise TypeError("Random Error!")
                
                # Read 1 second of data (fill in fake data here)
                self.onePPS.Wait()
                self.logger.debug("1PPS triggered.")
                
                while True:
                    # mimic daq callback
                    #self.logger.debug("Sleeping %f" % self.timePerBuffer)
                    time.sleep(self.timePerBuffer)
                    
                    tt = time.clock()
                    for i in range(self.numChannels):
                        self.tempBuffer[(self.samplesToRead*i):(self.samplesToRead*(i+1))] = numpy.zeros((self.samplesToRead), dtype=numpy.int16) + (i+1)*self.rawBufferCounter 
                    t_read_data = time.clock() - tt
                    self.rawBufferCounter += 1
                    
                    #self.logger.debug("%d %d" % ((self.rawBufferCounter-1)*self.bufferLength, self.rawBufferCounter*self.bufferLength))
                    self.rawBuffer[(self.rawBufferCounter-1)*self.bufferLength:self.rawBufferCounter*self.bufferLength] = self.tempBuffer
                    
                    self.logger.debug("DAQ read %d/ch. %d/%d in %dms-%dus" % (self.bufferLength, self.rawBufferCounter, self.numBuffersPerSecond, t_lock_acq*100, t_read_data*100000))

                    if (self.rawBufferCounter == self.numBuffersPerSecond):

                        self.rawBufferCounter=0
                        
                        # Seperate the channels
                        self.dataBuffers = []

                        tt = time.clock()
                        for i in xrange(self.numChannels):
                            self.dataBuffers.append(self.rawBuffer[i::self.numChannels].copy())
                        t_repackage_data = time.clock() - tt #for windows systems
                            
                            
                        # Put the data in the queue
                        if self.firstRun:
                            self.firstRun = False
                        else:
                            self.queue.put(self.dataBuffers)
                            self.isReady.set()
                            
                        self.logger.debug("Repackage data: %f" % (t_repackage_data))
                        
                        break
                        
        except:
            self.logger.exception("What happened?")
            raise DAQError("Exception Occurred in VirtualCard.py, Restarting...")
        


    def GetIntElemVal(self, config, tag):
        return int(config.getElementsByTagName(tag)[0].firstChild.data)

    def GetSampleRate(self):
        return self.sampleRate

# =========
# Unit Test
# =========
if __name__ == "__main__":
    from xml.dom.minidom import parseString
    from time import ctime
    from threading import Event
    from software.utilities.OnePPSSignal import OnePPSSignal

    # Create the NIDAQmx DAQ card object
    settings = """\
    <DaqCard module="VirtualCard">
        <NumChannels>3</NumChannels>
        <SampleRate>192</SampleRate>
    </DaqCard>
    """
    isReady = Event()
    onePPS = OnePPSSignal()
    daq = VirtualCard(parseString(settings), isReady, onePPS)

    print "Starting DAQ card at %s." % ctime()
    daq.Start()
    print "Started DAQ card at %s." % ctime()
    for i in range(10):
        isReady.wait()
        data = daq.Get()
        print "Received data at %s." % ctime()
    print "Stopping DAQ card at %s." % ctime()
    daq.Stop()
    print "Stopped DAQ card at %s." % ctime()
