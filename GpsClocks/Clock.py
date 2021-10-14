from datetime import datetime, timedelta
from threading import Thread, Lock
from Queue import Queue, Full, Empty
import sys, os, time

from GPSExceptions import *

if os.name != 'nt':
    time.clock = time.time

__all__ = ['Clock']
    
TT_UNLOCKED = 50
TT_LOCKED = 51
VIRTUAL_GPS = 20
LOCK_THRESHOLD = 5
    
class Clock:
    """
    Implements an interface to a GPS clock.  The interface treats the
    GPS clock like the consumer end of a queue whose elements are
    produced by the GPS clock.  The elements in the queue are lists of
    the form
        [DateTime, [Latitude, Longitude, Altitude], [NumSatellites]]
    where

        DateTime is a time.datetime object representing the date and time
        Latitude is a float representing the GPS receiver's latitude
        Longitude is a float representing the GPS receiver's longitude
        Altitude is a float representing the GPS receiver's altitude
        NumSatellites is the number of satellites the GPS receiver can see
        
    Public Functions:
    
        Start():
        Stop():
        Restart():
        MainLoop():
        SetQuality():
        GetQuality():
        HaveLock():    
        SetInternalTime():
        SetInternalLocation():
        Get():
        GetFast():
        GetQueueSize():
        Flush():

    Private Functions:

        _PostToQueue():
        _log_qsize():
        _StopAndSignalRestart()
        
    Error Handling:
    
        Get()           ClockNoDataError
                            timestamp queue timeout error
                                error raised and handled by engine
                        ClockError
                            unknown error getting data from queue
                                error raised and handled by engine
        
        GetFast()       same as Get()
                            same as Get()
                                error raised and handled by engine
        
        Flush()         same as Get()
                            same as Get()
                                error raised and handled by engine
        
        _PosttoQueue()  ClockQueueFull()
                            queue is full
                                noncritical - continued operation (this is result of engine not handling data)
                        Exception
                            unknown error putting data to queue
                                set flags - since this is a possible issue
        
    """
    
    def __init__(self,parent):
        # Initialize data members
        self.QUEUE_SIZE = 120
        self.parent = parent
        self.logger = parent.GPS_logger
        
        # Message passing flags
        #self.ENG_MSG = parent.GPS_msg
        self.flags = parent.GPS_flags
        
        self.running = False
        
        self.quality = 0
        
        # Queue for decoded timestamps
        self.timestamp_queue = Queue(self.QUEUE_SIZE)
        
        self.lock = Lock()
        self.thread = None
        
        self.last_qsize = 0
        self.fullcount = 0
        self.dt_previous = None
        self.timeLastQueuePost = None

        self.internal_dt = None
        self.internal_lat = None
        self.internal_lon = None
        self.internal_alt = None
        self.internal_quality = None

        self.timediff = None
        
        self.numHangs = 0
        
    def __del__(self):
        """
        Makes sure that the Motorola GPS clock is shut down properly and that
        the serial port is closed.
        """
        # Make sure the GPS clock is shut down properly
        self.Stop()

    def Start(self):
        raise NotImplementedError()
        pass

    def Stop(self):
        raise NotImplementedError()
        pass    
        
    def Restart(self):
        raise NotImplementedError()
        pass

    def MainLoop(self):
        raise NotImplementedError()
        pass
        
    def SetQuality(self,quality=0):
        """
        May want to set quality to 0 to ensure reading actual GPS quality later
        """
        self.lock.acquire()
        self.quality = quality
        self.lock.release()

    def GetQuality(self):
        """
        Returns the
        """
        # Report whether or not the GPS receiver has a lock
        self.lock.acquire()
        quality = self.quality
        self.lock.release()
        return quality
    
    def HaveLock(self):
        """
        Returns whether or not the GPS clock has a signal lock.
        """
        quality = self.GetQuality()
        if not isinstance(quality,int):
            return False
        
        #Truetime GPS unlocked:
        if quality == TT_UNLOCKED:
            return False
        
        if quality < LOCK_THRESHOLD:
            return False
        
        #no GPS:
        if quality == VIRTUAL_GPS:
            return False
        
        return True

    def IsVirtualClock(self):
        return self.GetQuality() == VIRTUAL_GPS

    def SetInternalTime(self,gpsData):
        #---
        #Problem: Motorola GPS not very reliable when it comes to posting time stamps to the serial port
        #Solution: Use internal counter after acquisition loop started
        #gpsData= [dt, [lat, lon, alt], [quality]]
        if gpsData is not None:
            self.logger.debug("Setting internal time")
            self.internal_dt = gpsData[0]
        
            self.logger.debug("Setting internal location")
            self.SetInternalLocation(gpsData)

            #reset lag counters:
            #self.absolute_lag = 0
            #self.cum_lag = 0
        else:
            self.logger.warning("Somehow gps data of type \"None\" was passed to SetInternalTime()")

    def SetInternalLocation(self,gpsData):
        self.internal_lat = gpsData[1][0]
        self.internal_lon = gpsData[1][1]
        self.internal_alt = gpsData[1][2]
        self.internal_quality = gpsData[2][0]
        
    def Get(self):
        """
        Blocks until the next GPS clock data element in the queue is available.
        """

        # Retrieve the oldest GPS information block from the queue
        try:
            return self.timestamp_queue.get(timeout=self.QUEUE_SIZE-1)
        except Empty:
            self.logger.error('Clock queue timed out - %ds.' % (self.QUEUE_SIZE-1))
            self.numHangs += 1
            raise ClockNoDataError("GPS Unresponsive. Clock queue empty for %d seconds. " % (self.QUEUE_SIZE-1))
        except:
            raise ClockError("Unknown GPS get() error.")            

    def GetFast(self):
        """
        
        """
        #self.logger.info("getfast")
        self.internal_dt += timedelta(seconds=1)

        #time.sleep(0.1)

        
        gpsData = (None, None)
        
        #simple flush
        while True:
            
            # Get latest gps info
            try:
                #self.logger.info("Get")
                gpsData = self.Get()
            except:
                self.logger.error("Exception getting GPS data")
                raise
                
            if gpsData[0] is None:
                self.logger.debug("Get() returned None")
                return gpsData  #restart if found timing error
            
            if self.timestamp_queue.empty():
                break

        #if no lock, don't try to reconcile
        if not self.HaveLock(): 
            #return
            self.logger.debug("No gps lock...")
            #gpsData = (None, None)

        if gpsData[0] is not None:
            self.SetInternalLocation(gpsData[1])
            self.timediff = self.internal_dt - gpsData[1][0]
            self.logger.debug("timediff=%d" % self.timediff.seconds)

        return (gpsData[0], [self.internal_dt, [self.internal_lat, self.internal_lon, self.internal_alt], [self.internal_quality]])

    def GetQueueSize(self):
        return self.timestamp_queue.qsize()
    
    def Flush(self):
    
        self.logger.debug("Flushing GPS queue")
    
        i = 0
    
        while self.GetQueueSize()>0:
            try:
                self.Get()
                
                i += 1
                
            except:
                self.logger.error("Exception on Get() while flushing queue.")
                raise

        self.logger.info("Flushed %d from GPS queue" % i) 
                
    ##################
    # Internal Methods
    ##################
    def _PostToQueue(self,dt,lat,lon,alt,quality):

        self.lock.acquire()
        self.quality = quality
        self.lock.release()
        
        ERROR = False   
        error_msg = ''

        if self.timeLastQueuePost is not None:
            if (time.clock()-self.timeLastQueuePost > 1.9):
                self.logger.warning('GPS erratic: %3.2f s since last post ' % (time.clock()-self.timeLastQueuePost))
        
        if self.dt_previous is not None:
            if ((dt-self.dt_previous).seconds < 0):
                self.logger.error('GPS reverted: (%s) to (%s) ' % (self.dt_previous,dt))
                #self.logger.warning('GPS reverted: (%s) to (%s) ' % (self.dt_previous,dt))
                #error_msg = 'GPS reverted: (%s) to (%s) ' % (self.dt_previous,dt)
                ERROR = True
                #raise ClockSkipError(error_msg)
                
            elif ((dt-self.dt_previous).seconds==0):
                self.logger.error('GPS repeated %s; %3.2f s elapsed ' %  (self.dt_previous,(time.clock()-self.timeLastQueuePost)))
                #self.logger.warning('GPS repeated %s; %3.2f s elapsed ' %  (self.dt_previous,(time.clock()-self.timeLastQueuePost)))
                dt += timedelta(0,1)    #add a second to dt
                ERROR = True
            
            elif ((dt-self.dt_previous).seconds>1):
                self.logger.error('GPS skipped: (%s) to (%s) ' % (self.dt_previous,dt))
                #self.logger.warning('GPS skipped: (%s) to (%s) ' % (self.dt_previous,dt))
                #error_msg = 'GPS skipped: (%s) to (%s) ' % (self.dt_previous,dt)
                ERROR = True
                #raise ClockSkipError(error_msg)

        timestamp = datetime.utcnow()
        self.logger.debug("ts: %s" % timestamp)
        
        try:
            if ERROR:
                #raise ClockSkipError(error_msg)
                self.timestamp_queue.put((None, None), timeout=0.90) 
                #self.timestamp_queue.put(None, timeout=0.90) 
            else:
                self.timestamp_queue.put((timestamp, [dt, [lat, lon, alt], [quality]]), timeout=0.90)
                #self.timestamp_queue.put([dt, [lat, lon, alt], [quality]], timeout=0.90)

        except Full:
            # Being full is not a critical error - engine not doing it's job
            error_msg = 'GPS Queue was full (%d seconds behind)' % (self.QUEUE_SIZE)
            self.logger.error(error_msg)
            self.flags.error.set()
        except:
            self.logger.error("Unknown error putting timestamp to queue.")
            self.flags.error.set()


        else:
            
            self.timeLastQueuePost = time.clock()
            self._log_qsize()
            
            if ERROR:
                self.dt_previous = None
                
            else:
                self.dt_previous = dt
                #self.logger.debug('Posted %s to queue' % str(dt))

        #Sleep to release GIL
        time.sleep(.01)
        
    def _log_qsize(self):
        qsize = self.timestamp_queue.qsize()
        if (qsize>self.last_qsize):
            message = 'GPS queue population: %d  ' % qsize
            if (qsize>9 and qsize % 10==0):
                self.logger.warning(message)
            elif (qsize==5):
                self.logger.info(message)
            elif (qsize>2):
                self.logger.debug(message)
            else:
                pass
        self.last_qsize = qsize

