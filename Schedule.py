from datetime import date, time, datetime, timedelta
from utilities.DAQConfig import DAQConfig

__all__ = ['Schedule']

_FULLDAY = 3600*24



class LifetimeLog:
    """
    Keep track of lifetime activity
    """
    def __init__(self,logname='lifetime.log'):
        self.logname = logname
        self.start = None
        self.lasttime = None

    def write(self,string):
        fid = open(self.logname,'a')
        fid.write(string)
        fid.close()

    def logend(self,timestamp):
        if isinstance(timestamp,datetime):
            self.write(timestamp.strftime('\nEnd:   %Y-%m-%d %H:%M:%S'))
        else:
            self.write('\nEnd:   Not a datetime object: %s' % str(timestamp))
        self.start = None

    def log(self,timestamp):
        if self.start is None:
            self.write(timestamp.strftime('\nStart: %Y-%m-%d %H:%M:%S'))
            self.start = timestamp
        elif self.lasttime.date() != timestamp.date():
            self.write(timestamp.strftime('\nCont:  %Y-%m-%d %H:%M:%S'))
        elif self.lasttime.hour != timestamp.hour:
            self.write(timestamp.strftime(', %H'))
        else:
            pass
        self.lasttime = timestamp


class Schedule:
    """
    The Schedule class implements a representation of a master on/off schedule
    for the data acquisition.  An Engine object uses a Schedule object to start
    and stop its DAQ Card object's data acquisition.  Fine-tuning of the actual
    data acquistion processing activity must occur at the level of the
    individual Post Processor objects.
    """


    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self, config, parent):
        """
        Build the Schedule object from the supplied XML description of the
        schedule.
        """
        # Logger
        self.logger = parent.SCH_logger
        
        # Generate the schedule
        self.schedule = []
        entriesSettings = config.childNodes
        
        def IsEntryNode(x): return str(x.nodeName) == "Entry"
        entriesSettings = filter(IsEntryNode, entriesSettings)
        
        for entrySettings in entriesSettings:
            start = self.GetStrElemVal(entrySettings, "Start").split(':')
            start = time(hour=int(start[0]), minute=int(start[1]))
            #this starts the schedule entry NOW (or very soon anyway), uncomment for testing)
            #start = time(hour=datetime.now().hour-9, minute=datetime.now().minute+1); print start
            seconds = int(self.GetStrElemVal(entrySettings, "Duration"))
            if seconds == -1:   #continuous
                seconds = _FULLDAY
            base = datetime(year=2000, month=1, day=1)
            secondsToMidnight = (base + timedelta(days=1) - datetime.combine(base, start)).seconds
            self.schedule.append([start, seconds])
            if (secondsToMidnight < seconds) and (secondsToMidnight != 0):
                self.schedule.append([time(hour=0), seconds-secondsToMidnight])

    # =========
    # Accessors
    # =========
    def SecondsLeftInAcquisition(self, timestamp):
        """
        Returns the number of seconds left in the current acquisition given the
        supplied timestamp.  By default, the result is shifted forward by one seconds so that
        an Engine object can know when to start its DAQ Card object's data
        acquisition (preventing a missing of the first second in the
        acquisition.)
        """
        # Returns how many second are left in the current acquisition
        timestamp = timestamp + timedelta(seconds=1)
        today = date(year=timestamp.year, month=timestamp.month, day=timestamp.day)
        for entry in self.schedule:
            start = datetime.combine(today, entry[0])
            seconds = timedelta(seconds=entry[1])
            if (timestamp >= start) and (timestamp < (start + seconds)):
                timeleft = (start + seconds - timestamp).seconds
                if entry[1]==_FULLDAY and timeleft == 0:  #special case
                    return _FULLDAY
                return timeleft


        return 0

    # ==============
    # Helper Methods
    # ==============
    def GetStrElemVal(self, config, tag):
        return str(config.getElementsByTagName(tag)[0].firstChild.data)

# =========
# Unit Test
# =========
if __name__ == "__main__":
    from xml.dom.minidom import parseString

    # Create the Schedule object
    settings = """\
    <Schedule>
        <Entry>
            <Start>23:58</Start>
            <Duration>30</Duration>
        </Entry>
        <Entry>
            <Start>23:59</Start>
            <Duration>30</Duration>
        </Entry>
        <Entry>
            <Start>0:00</Start>
S            <Duration>30</Duration>
        </Entry>
    </Schedule>
    """
##    settings = """\
##    <Schedule>
##        <Entry>
##            <Start>0:01</Start>
##            <Duration>86400</Duration>
##        </Entry>
##    </Schedule>
##    """

    llog = LifetimeLog()

    settings = parseString(settings)
    schedule = Schedule(settings.getElementsByTagName("Schedule")[0])
    today = date.today()
    for i in range(86400):
        offset = i
        timestamp = datetime.combine(today, time(hour=23,minute=57,second=50)) + timedelta(seconds=offset)
        llog.log(timestamp)
        if i==100:
            llog.logend(timestamp)
##        print timestamp, schedule.SecondsLeftInAcquisition(timestamp)
    print schedule.schedule
