import ctypes
import ctypes.util
import numpy
from Queue import Queue, Full
from threading import Thread
import random
import time, sys, os
if os.name != 'nt':
    time.clock = time.time

from NIDAQmx import NIDAQmx


__all__ = ['NIDAQmxBase']

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


class NIDAQmxBase(NIDAQmx):
    """
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
        NIDAQmx.__init__(self,config,parent,Base=True)


        #load the shared library
        try:
            sys.getwindowsversion()
        except: #unix
##            self.driver = ctypes.cdll.LoadLibrary('libnidaqmxbase.so')
            self.driver = ctypes.CDLL(ctypes.util.find_library("nidaqmxbase"),ctypes.RTLD_GLOBAL)
        else:   #windows
            raise Exception('NiDAQmx base current not supported on windows')
            self.driver = ctypes.windll.nicaiu

        self._name = "NIDAQmxBase.py"

        #make definitions to re-use NIDAQmx code:
        self.driver.DAQmxClearTask = self.driver.DAQmxBaseClearTask
        self.driver.DAQmxGetExtendedErrorInfo = self.driver.DAQmxBaseGetExtendedErrorInfo

        self.driver.DAQmxCreateTask = self.driver.DAQmxBaseCreateTask
        self.driver.DAQmxCreateAIVoltageChan = self.driver.DAQmxBaseCreateAIVoltageChan
        self.driver.DAQmxCfgSampClkTiming = self.driver.DAQmxBaseCfgSampClkTiming
        self.driver.DAQmxCfgInputBuffer = self.driver.DAQmxBaseCfgInputBuffer
        self.driver.DAQmxCfgDigEdgeStartTrig = self.driver.DAQmxBaseCfgDigEdgeStartTrig

        self.driver.DAQmxReadBinaryI16 = self.driver.DAQmxBaseReadBinaryI16
        self.driver.DAQmxStartTask = self.driver.DAQmxBaseStartTask
        self.driver.DAQmxStopTask = self.driver.DAQmxBaseStopTask



# =========
# Unit Test
# =========
if __name__ == "__main__":
    from xml.dom.minidom import parseString
    from time import ctime
    from threading import Event

    # Create the NIDAQmx DAQ card object
    settings = """\
    <DaqCard module="NIDAQmxBase">
        <DevName>Dev1</DevName>
        <NumChannels>3</NumChannels>
        <SampleRate>100000</SampleRate>
        <SampleClockName>PFI2</SampleClockName>
        <StartTriggerName>PFI0</StartTriggerName>
    </DaqCard>
    """
    daq = NIDAQmxBase(parseString(settings))

    print "Starting DAQ card at %s." % ctime()
    daq.Start()
    print "Started DAQ card at %s." % ctime()
    for i in range(10):
        data = daq.Get()
        print "Received data at %s." % ctime()

    print "Stopping DAQ card at %s." % ctime()
    daq.Stop()
    print "Stopped DAQ card at %s." % ctime()
