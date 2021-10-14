from SerialClock import *
from GPSExceptions import *

__all__ = ['TrueTimeClock']


class TrueTimeClock(SerialClock):
    """
    TrueTime GPS
    """

    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self, config, parent):
        """
        Constructs a TrueTime GPS clock object according to the supplied XML
        description.
        """
        # Initialize data members
        SerialClock.__init__(self,config,parent)

    def GetStopCommand(self):
        return '@@Eq\x004\x0d\x0a'


    def MainLoop(self):
##        print 'Queue count: %d' % self.queue.qsize()

        #Querry lat/lon/alt once:
        self.ser.write('\x03F50\r')

        byte = self.readFromSerial(1)
        for ii in range(3):   #try 3 times
            if byte != 'F': #Serial port returned something else
                while ord(self.ser.read(1)) != 10:
                    pass
                self.ser.write('F50\r')         #don't pass in Ctrl-C
                byte = self.readFromSerial(1)
                self.logger.debug('Check for F iteration: %d out of 3' % (ii+1))
            else:
                break

        self.logger.debug('Should be F: %s' % byte)
        assert byte == 'F'
        serbuf = [self.readFromSerial(1)]
        while ord(serbuf[-1]) != 10:
            serbuf.extend(self.readFromSerial(1))
        (lat,lon,alt) = self.DecodePosition("".join(serbuf))

        #Querry quality once:
        self.ser.write('F72\r') #don't need to error check here
        byte = self.readFromSerial(1)
        assert byte == 'F'
        serbuf = [self.readFromSerial(1)]
        while ord(serbuf[-1]) != 10:
            serbuf.extend(self.readFromSerial(1))
        quality = self.DecodeQuality("".join(serbuf))


        #Set up serial port to print time stamps each second:
        self.ser.write('\x03F08\r')         #Try Ctrl-C first

        # Sync up with incoming timestamps
        byte = self.readFromSerial(1)
        self.logger.debug('first read: %d' % ord(byte))
        for ii in range(3):   #try 3 times
            if byte != '\x01': #Serial port returned an error
                while ord(self.readFromSerial(1)) != 10:
                    pass
                self.ser.write('F08\r')         #don't pass in Ctrl-C
                byte = self.readFromSerial(1)
                self.logger.debug('Check for 1 iteration: %d out of 3' % (ii+1))
            else:
                break

        self.logger.debug('Should be 1: %d' % ord(byte))
        assert byte == '\x01', 'Serial port not locked; %d' % ord(byte)
        serbuf = self.readFromSerial(20)

        dt_previous = None

        # Begin recording the GPS data
        self.running = True
        while self.running:

##            print serbuf

            # Parse the timestamp
            dt = datetime.strptime(serbuf[:17],'%m/%d/%y %H:%M:%S')

            #post to GPS Queue:
            self.postToQueue(dt,lat,lon,alt,quality)


            # Get the next timestamp
            byte = self.readFromSerial(1)
            assert byte == '\x01', 'Serial port not locked; %s.' % byte
            serbuf = self.readFromSerial(20)



    def DecodePosition(self,st):
        """
        Decode output from F50 command into TrueTime
        """
        self.logger.debug('st: %s' % st)
        start = 3
        end = start + 12
        if ord(st[start + 11])==34:
            end = start + 11

        #50 N 37d23'34.0" W 122d02'17.3"   -3m pdob 0.00
        lat = float(st[start + 2:start + 4]) +\
              float(st[start + 5:start + 7])/60.0 +\
              float(st[start + 8:end])/3600.0
        if st[start] == 'S':
            lat *= -1.0

        start = end + 2
        end = start + 13
        if ord(st[start+12])==34:
            end = start + 12

        lon = float(st[start + 2:start + 5]) + \
            float(st[start + 6:start + 8])/60.0 + \
            float(st[start + 9:end])/3600.0
        if st[start] == 'W':
            lon *= -1.0


        sign  = st[end+4]
        start = end+5
        while st[end] not in ['M','m','F','f']:
            end += 1

        alt = float(st[start:end])
        if sign == '-':
            alt *= -1.0

        self.logger.debug('lat: %3.4f, lon: %3.4f, alt: %3.4f' % (lat, lon, alt))
        return (lat, lon, alt)

    def DecodeQuality(self,st):
        """
        Decode GPS quality string
        """
        start = 4
        while st[start-4:start] != 'GPS:':
            start += 1
##        print st, st[start+1]
        if st[start+1] == 'U':
            return TT_UNLOCKED   #unlocked -- revert back in matFileWriter
        else:
            return TT_LOCKED  #locked -- revert back in matFileWriter



# =========
# Unit Test
# =========
if __name__ == "__main__":
    from xml.dom.minidom import parseString
    from time import ctime

    # Create the Motorola GPS clock object
    settings = """\
    <GpsClock module="MotorolaClock">
        <ComPortNumber>1</ComPortNumber>
        <BaudRate>9600</BaudRate>
        <DataBits>8</DataBits>
        <Parity>N</Parity>
        <StopBits>1</StopBits>
    </GpsClock>
    """
    gps = MotorolaClock(parseString(settings))

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