
from time import sleep

from Clock import *

__all__ = ['VirtualClock']

class VirtualClock(Clock):
    """
    Virtual Clock
    """

    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self, config, onePPS,parent):
        """
        Constructs a software GPS clock object according to the supplied XML
        description.  Additionally accepts an external OnePPSSignal object by
        which it can synchronize its data generation with other software-based
        serial streams.
        """
        Clock.__init__(self,parent)
        # Initialize data members
        self.onePPS = onePPS
        self._quality = VIRTUAL_GPS

        # Read serial port configuration
        now = datetime.utcnow()    #use CPU time as default

        startYear = self.GetIntElemVal(config, "StartYear",now.year)
        startMonth = self.GetIntElemVal(config, "StartMonth",now.month)
        startDay = self.GetIntElemVal(config, "StartDay",now.day)
        startHour = self.GetIntElemVal(config, "StartHour",now.hour)
        startMinute = self.GetIntElemVal(config, "StartMinute",now.minute)
        startSecond = self.GetIntElemVal(config, "StartSecond",now.second)
        self.timestamp = datetime(year=startYear, month=startMonth, day=startDay, hour=startHour, minute=startMinute, second=startSecond)


    # =======
    # Methods
    # =======
    def Start(self):
        """
        Begins acquisition of GPS clock data.
        """
        # Start the GPS clock
        self.thread = Thread(target=self.MainLoop)
        self.thread.start()

    def Stop(self):
        """
        Stops generation of GPS clock data.
        """
        # Stop the GPS clock
        if self.thread is not None:
            self.running = False        # Kill the thread
            self.thread.join()
            self.thread = None
        self.onePPS.Stop()              # stop the 1PPS signal

    # ==============
    # Helper Methods
    # ==============
    def MainLoop(self):
        # Begin recording the GPS data
        self.running = True
        while self.running:
            # "Get" the next timestamp
            self.onePPS.Wait()
            sleep(0.1)
            # Parse the timestamp
            self.timestamp += timedelta(seconds=1)
            # Put the newest GPS information block into the queue
            self.postToQueue(self.timestamp,0,0,0,self._quality)



# =========
# Unit Test
# =========
if __name__ == "__main__":
    from xml.dom.minidom import parseString
    from time import ctime
    from OnePPSSignal import OnePPSSignal

    # Create the Motorola GPS clock object
    settings = """\
    <GpsClock module="VirtualClock">
        <StartYear>1982</StartYear>
        <StartMonth>6</StartMonth>
        <StartDay>28</StartDay>
        <StartHour>6</StartHour>
        <StartMinute>28</StartMinute>
        <StartSecond>0</StartSecond>
    </GpsClock>
    """
    onePPS = OnePPSSignal()
    gps = VirtualClock(parseString(settings), onePPS)

    # Start the GPS clock
    print "Starting GPS clock at %s." % ctime()
    gps.Start()
    print "Started GPS clock at %s." % ctime()

    # Start reading the GPS timestamps
    for i in range(10):
        gpsInfo = gps.Get()
        print gpsInfo[0].ctime()

    # Start the GPS clock
    print "Stopping GPS clock at %s." % ctime()
    gps.Stop()
    print "Stopped GPS clock at %s." % ctime()