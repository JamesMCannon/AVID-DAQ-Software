
from threading import Event, Thread, Lock
import time, os, sys, random, re
sys.path.append(['..'])
if os.name != 'nt':
    time.clock = time.time
from datetime import datetime, timedelta
import logging
import traceback
#from utilities import read_config

class TaskError(Exception):
    pass
    
class Task:


    def __init__(self, config, logger, tasknum):

        self.running = False
        self.logger = logger

        self.randInterval = 10

        self.last_scan = None

        self.logging_error = True   #avoid too many repeat error logs
        self.lastlogtime = datetime.utcnow()
        
        self.taskname = 'T%d: ' % tasknum

        self.start_task_time = self.decodeTimeString(config.GetStrElemVal("StartTime", "00:00"))
        self.end_task_time = self.decodeTimeString(config.GetStrElemVal("EndTime", "23:59"))


###############################################################################

    def Start(self):
        self.logger.debug('Starting...')
        self.thread = Thread(target=self.MainLoop)
        self.thread.start()
        self.logger.info('Started')

###############################################################################

    def Stop(self):

        if self.thread is not None:
            self.logger.debug('Stopping...')
            self.running = False
            self.thread.join()
            self.thread = None
            self.logger.info('Stopped.')
###############################################################################

###############################################################################

    def MainLoop(self):

        self.running = True

        while self.running:
            #sleep for a second so that this thread
            #doesn't hog the CPU
            time.sleep(1)
            
            if not self.running:
                break
                
            if self.TimeToDoTask():
                #self.waitRandN()
                try:
                    self.DoTask()
                except:
                    # The buck stops here. Exceptions in task gets displayed here.
                    
                    #msg = 'Exception in %s' % self.taskname
                    #self.logger.error(msg)
                    #raise TaskError(msg)
                    pass


###############################################################################

    def DoTask(self):
    
        # NOTE: 
        # Any function exceptions should be caught and displayed in module so that full info is captured and displayed
        # return from function immediately.
    
        raise NotImplementedError()
        pass

###############################################################################

    def waitRandN(self):
        #wait unif(N) seconds (so not every sensor does task at same time)
        for i in range(random.randint(0,int(self.randInterval))):   #don't want all sites posting at same time
            if not self.running:
                break
            time.sleep(1)


    def decodeTimeString(self,time_string):
        """
        Ideally, time string given in format HH:MM
        """
        r = re.compile(r"^([0-9]{1,2})[:, ]+([0-9]{1,2})")
        m = r.match(time_string.strip())
        if m is None:
            raise 'Invalid time string: %s' % time_string
        return datetime(2000,1,1,int(m.group(1)),int(m.group(2)),0).time()

###############################################################################

    def resetLogFlag(self,timestamp):
        if (timestamp-self.lastlogtime).seconds > 3600: #reset each hour
            self.lastlogtime = timestamp
            self.logging_error = True   #set to False after first log

###############################################################################

    def _startTask(self,timestamp):
        self.resetLogFlag(timestamp)
        self.last_scan = timestamp
        return True

###############################################################################

    def TimeToDoTask(self):
        timestamp = datetime.utcnow()

        if timestamp.time() < self.start_task_time:
            return False

        if timestamp.time() > self.end_task_time:
            return False

        if self.last_scan is None:
            return self._startTask(timestamp)

        beginningOfDay = datetime(year=timestamp.year, month=timestamp.month, day=timestamp.day)
        if ((timestamp-beginningOfDay).seconds % self.interval) == 0:
            return self._startTask(timestamp)

        if (timestamp - self.last_scan) >= timedelta(seconds=self.interval):
            return self._startTask(timestamp)

        return False

