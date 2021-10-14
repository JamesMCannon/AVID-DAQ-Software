from xml.dom.minidom import parseString
from time import ctime, sleep
import multiprocessing
from multiprocessing import Event
import sys, os

CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#print CURRENT_DIR
sys.path.insert(0, CURRENT_DIR)

from utilities.DAQLogger import DAQLogger, DAQLogClient
from Engine import EngineFlags

from NIDAQmx import NIDAQmx

# class to mimic parent process
class test_engine:

    def __init__(self, main_logger, logger):

        # add ch to logger
        self.DAQ_logger = DAQLogClient(main_logger.log_queue, "DAQ")
        
        # Add flags
        self.DAQ_flags = EngineFlags()

        self.logger = logger
        
        self.daq = NIDAQmx(config, self, have_gps = False)
        self.DAQ_flags.init.wait()
        self.logger.info("DAQ initialized at %s" % ctime())

    def StartTest(self):
        self.logger.info( "Starting DAQ card at %s." % ctime())
        self.daq.Start()
        self.DAQ_flags.is_running.wait()
        self.logger.info( "Started DAQ card at %s." % ctime())   

    def StopTest(self):
        self.logger.info( "Stopping DAQ card at %s." % ctime())
        self.daq.Stop()
        self.logger.info( "Stopped DAQ card at %s." % ctime())
            
    def Restart(self):
        self.logger.info( "Restarting DAQ at %s." % ctime())
        
        if not self.daq.Restart():
            raise Exception
        
        self.daq.Start()
        self.DAQ_flags.is_running.wait()
        
        self.logger.info( "Restarted DAQ at at %s." % ctime())    
        
    def RestartLR(self):
        self.logger.info( "Restarting LR at %s." % ctime())
        
        if not self.daq.RestartLineReceiver():
            raise Exception
            
        self.daq.Start()
        self.DAQ_flags.is_running.wait()
        
        self.logger.info( "Restarted LR at at %s." % ctime())        
            
    def RestartAnalog(self):
        self.logger.info( "Restarting DAQ Analog at %s." % ctime())
        
        if not self.daq.RestartAnalog():
            raise Exception
        
        self.daq.Start()
        self.DAQ_flags.is_running.wait()
        
        self.logger.info( "Restarted DAQ Analog at at %s." % ctime())        
        
    def GetData(self):
        self.logger.info("Getting data")
        try:
            self.daq.Get()
        except:
            self.logger.exception("Error while getting data")
            pass
        self.logger.info("Got Data")
            
# =========
# Unit Test
# =========
if __name__ == "__main__":

    

    
    # Create the NIDAQmx DAQ card object
    settings = """\
    <DaqConfiguration>
    <StationSettings>
        <station_id>SUA</station_id>
        <station_name>ATB0</station_name>
        <station_description>.</station_description>
        <hardware_description>LF</hardware_description>
        <antenna_bearings>.</antenna_bearings>
        <antenna_description>.</antenna_description>
        <install_date>.</install_date>
        <contact_info>.</contact_info>
        <adc_type>.</adc_type>
        <computer_sn>.</computer_sn>
        <adc_sn>.</adc_sn>
        <gps_sn>.</gps_sn>
    </StationSettings>
    <DaqCard module="NIDAQmx">
        <SampleClockName>PFI2</SampleClockName>
        <StartTriggerName>PFI0</StartTriggerName>
        <SampleClockPolarity>1</SampleClockPolarity>
        <StartTriggerPolarity>1</StartTriggerPolarity>
        <SampleRate>1000000</SampleRate>
        <DevName>Dev3</DevName>
        <NumChannels>2</NumChannels>
    </DaqCard>
    <Logger>
        <LogDir>log/</LogDir>
        <ErrorEmail>0</ErrorEmail>
        <ErrorPost>0</ErrorPost>
        <LogPostUrl>/field_sites_logs/logging.php</LogPostUrl>
        <LogPostServer>vlf-engineering.stanford.edu:80</LogPostServer>
        <LogLevel>DEBUG</LogLevel>
        <ConsoleLevel>DEBUG</ConsoleLevel>
        <LogFileLevel>WARNING</LogFileLevel>
        <PostLevel>WARNING</PostLevel>
    </Logger>
    </DaqConfiguration>
    """

    config = parseString(settings)
    main_logger = DAQLogger(config)
    main_logger.start()
    logger = DAQLogClient(main_logger.log_queue, "MAIN")
    
    logger.debug("Test debug statements")
    
    test = test_engine(main_logger, logger)
    
    test.StartTest()
    
    for i in range(10):
        data = test.GetData()
        logger.info( "Received data at %s." % ctime())

    logger.info('************************* Full Restart Test*************************')
    test.Restart()

    for i in range(10):
        data = test.GetData()
        logger.info( "Received data at %s." % ctime())
        
    logger.info('*************************Restart Line Receiver*************************')
    test.RestartLR()

    for i in range(10):
        data = test.GetData()
        logger.info( "Received data at %s." % ctime())
    
    logger.info('*************************Restart Analogs*************************')
    test.RestartAnalog()

    for i in range(10):
        data = test.GetData()
        logger.info( "Received data at %s." % ctime())
 
    test.StopTest()
    
    # need to wait stopped??
    
    # Clear test and reinitialize
    logger.info('******************************************************************')
    logger.info('**********************Clear and restart***************************')
   
    test = None
    
    test = test_engine(main_logger, logger)

    test.StartTest()
    
    for i in range(10):
        data = test.GetData()
        logger.info( "Received data at %s." % ctime())

    test.StopTest()
    
    sleep(2)