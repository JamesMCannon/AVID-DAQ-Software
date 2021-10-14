from NIDAQmx import *
HAVE_GPS = False

NIDAQmx_no_gps = NIDAQmx

# =========
# Unit Test
# =========
if __name__ == "__main__":
    from xml.dom.minidom import parseString
    from time import ctime
    from threading import Event

    # Create the NIDAQmx DAQ card object
    settings = """\
    <DaqCard module="NIDAQmx_no_gps">
        <DevName>Dev1</DevName>
        <NumChannels>3</NumChannels>
        <SampleRate>100000</SampleRate>
    </DaqCard>
    """
    isReady = Event()
    daq = NIDAQmx(parseString(settings), isReady)

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
