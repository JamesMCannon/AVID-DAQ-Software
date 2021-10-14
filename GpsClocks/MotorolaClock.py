# Motorola Clock
# Interface for Motorola GPS Clock.

from time import sleep
from datetime import datetime, timedelta

from SerialClock import *
from GPSExceptions import *

__all__ = ['MotorolaClock']

class MotorolaCommands(dict):

    #try: http://docs.python.org/2/library/collections.html#collections.namedtuple
    def __init__(self, command_name, command_str, command_header, command_size, command_callback):
        dict.__init__(self, **items)
        self.default = {}
        
    def __getitem__(self, key):
        if not self.has_key(key):
            self[key] = self.default()
        return dict.__getitem__(self, key) 
        #http://parand.com/say/index.php/2007/07/13/simple-multi-dimensional-dictionaries-in-python/
        #http://code.activestate.com/recipes/389639/
    
    
class MotorolaClock(SerialClock):
    """
    Motorola GPS
    
    Public Functions:
    
        MainLoop() 
        
    Private Functions:
    
        _WaitForMessage()
        _MatchMessageHeader()    
    
    Error Handling:
    
        MainLoop()      
        
        _WriteCMDandVerify()
        
        _WaitForMessage()       Empty
                                    Empty queue
                                        set flag, return false
                                Exception
                                    unknown error getting from message queue
                                        set flag, return false

        _MatchMessageHeader()   ClockMsgQueueFull, ClockQueueFull
                                    exception executing decode function, from queues being full. 
                                        noncritical, continue
                                Exception
                                    some other kind or error happened and engine needs to be notified
                                        set flag, continue        
        
        _DecodeTimeStamp()      ClockMsgQueueFull
                                    if message queue full
                                        raise error, handled by _MatchMessageHeader()
                                ClockQueueFull
                                    if timestamp queue full
                                        raise error, handled by _MatchMessageHeader()
                                Exception
                                    Unknown error putting or getting from queue
                                        raise error, handled by _MatchMessageHeader()
        _DecodeMode()       
        _Decode12ChPosData()
        _DecodeVisibleSat()     ClockMsgQueueFull
                                    message queue full
                                        raise error handled by _MatchMessageHeader()
                                Exception
                                    Unknown error putting or getting from queue
                                        raise error, handled by _MatchMessageHeader()                                        
    """


    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self, config,parent):
        """
        Constructs a Motorola GPS clock object according to the supplied XML
        description.
        """
        SerialClock.__init__(self, config, parent)
        
        # Add motorola GPS messages and hooks
        self.msg_hdr['@@Eq'] = (96, self._DecodeTimestamp) #@@Eq message is 96 bytes long
        self.msg_hdr['@@Bb'] = (92, self._DecodeVisibleSat)  #@@Bb message is 96 bytes long
        self.msg_hdr['@@Ha'] = (154, self._Decode12ChPosData)  #@@Ha message is 154 bytes long
        self.msg_hdr['@@Gd'] = (8, self._DecodeMode)  #@@Gd message is 8 bytes long
        
        # Add motorola GPS commands
        self.cmd["start"] = '@@Eq\x01\x35\x0d\x0a'
        self.cmd["stop"] = '@@Eq\x00\x34\x0d\x0a'
        self.cmd["getMode"] = '@@Gd\xff\xdc\x0d\x0a'
        self.cmd["setModeAuto"] = '@@Gd\x03\x20\x0d\x0a'
        self.cmd["stopBbmsg"] = '@@Bb\x00\x20\x0d\x0a'
        self.cmd["stopHamsg"] = '@@Ha\x00\x29\x0d\x0a'
        
        self.mode = 0
        
        self.logger.debug('Motorola GPS initialized.')
        
        self.flags.is_stopped.clear()
        self.flags.init.set()

    def MainLoop(self):
        
        self.logger.debug("Motorola Mainloop Starting...")
        
        self.ser.flushInput()
        self.ser.flushOutput()

        # Turn off all other possible timestamp generation
        self.logger.debug('Sending @@Eq')
        #self.ser.write(self.cmd["stop"])
        self.WriteToSerial(self.cmd["stop"])
        
        if not self._WaitForMessage('@@Eq',10):
            # This is usually the first indication if serial port is not working
            # we want to stop this current thread

            # Sending Stop command
            self.logger.info('Writing Stop Command to GPS ...')
            #self.ser.write(self.cmd["stop"])
            self.WriteToSerial(self.cmd["stop"])
            return False

        self.logger.debug('Sending @@Bb')
        #self.ser.write(self.cmd["stopBbmsg"])
        self.WriteToSerial(self.cmd["stopBbmsg"])
        if not self._WaitForMessage('@@Bb',10):
            return False
        
        self.logger.debug('Sending @@Ha')
        #self.ser.write(self.cmd["stopHamsg"])
        self.WriteToSerial(self.cmd["stopHamsg"])
        self._WaitForMessage('@@Ha',10)
        
        #self.running = True
        #self.flags.is_running.set()

        #query position control:
        #self.ser.write(self.cmd["getMode"])
        self.WriteToSerial(self.cmd["getMode"])
        self._WaitForMessage('@@Gd',10)

        #set to auto-survey mode:
        if self.mode == 3:
            self.logger.info('GPS timing mode already set to auto')
        else:
            #self.ser.write(self.cmd["setModeAuto"])
            self.WriteToSerial(self.cmd["setModeAuto"])
            self._WaitForMessage('@@Gd',10)

        # Check Housekeeping data
        self.logger.debug("Requesting housekeeping")
        #self.ser.write(self.cmd["HSKP"])
        self.WriteToSerial(self.cmd["HSKP"])
        
        # Turn on timestamp generation
        self.logger.debug("Starting GPS stream")
        #self.ser.write(self.cmd["start"])
        self.WriteToSerial(self.cmd["start"])

        #self.ENG_MSG.put('GPS_RUNNING')
        self.running = True
        self.flags.init.clear()
        self.flags.is_running.set()
        
        # Begin recording the GPS data
        while self.flags.is_running.is_set():
            
            sleep(0.1)
            
            #wait for next timestring
            if not self._WaitForMessage('@@Eq', 10):
                # Some error happened, break out of while loop
                self.logger.error("Did not receive response for @@Eq message after 10 seconds.")
                break
            
            # Check Housekeeping data
            #self.ser.write(self.cmd["HSKP"])
        
        self.logger.debug('Finished Mainloop.')
        
        # Sending Stop command
        self.logger.info('Writing Stop Command to GPS ...')
        self.WriteToSerial(self.cmd["stop"])
        
    def _WriteCMDandVerify(self, gps_cmd):
        # Write command to serial port then check response
        """
        try:
            self.WriteToSerial(self.cmd[gps_cmd])
        except:
            pass
        else:
            if not self._WaitForMessage('@@Bb',10):
                return False
        """

    def _WaitForMessage(self, msg_hdr, timeout=30):
        # Check for response from command and match header
    
        # wait for message, default timeout 30 seconds 
        try:
            msg = self.message_queue.get(True, timeout)
        except Empty:
            # Means either no data was sent 
            error_msg = "Serial port unresponsive. No messages for %d seconds." % timeout
            self.logger.error(error_msg)

            # Send error message up to Engine
            #self.ENG_MSG.put('GPS_NORESP')
            self.flags.error.set()
            
            # stop serial reading thread
            self.ser_running = False
            self.flags.is_running.clear()
            
            return False
            #raise ClockNoResponse(error_msg)
            
        except:
            #self.ENG_MSG.put('GPS_UNKNOWNERR')
            self.flags.error.set()
            
            # stop serial reading thread
            self.ser_running = False
            self.flags.is_running.clear()
            
            return False
            #raise ClockError("Unknown error while getting msg from queue.")
    
        # Got a message, now check header
        if msg == msg_hdr:
            return True
        else:
            # received some other reply
            return False

    def _MatchMessageHeader(self):
    
        message = ''
        
        self.ser_lock.acquire()
        
        buffer = self.buffer
        buffer_len = len(buffer)
        
        #self.logger.debug('Matching header')
        
        trim_buffer = False
        
        # iterate through self.msg_hdr to match headers, put match into self.message_queue
        for header in self.msg_hdr:
        
            message_len = self.msg_hdr[header][0]
            
            #self.logger.debug("msg_len=%d / buffer_len=%d" % (message_len, buffer_len))
            
            # Make sure buffer holds enough characters for full message
            if (buffer_len >= message_len):

                L = len(header)
                
                temp = buffer[:L]
                
                #self.logger.debug("%s =? %s" % (header, temp))
                
                if temp == header:
                    
                    #self.logger.debug("Message match: %s" % temp)
                    
                    # Grab message
                    message = buffer[:message_len]
                    
                    # remove message content from buffer
                    self.buffer = self.buffer[message_len:]
                    
                    # get decode function with header of message
                    message_proc_fcn = self.msg_hdr[header][1]
                    
                    # run decode function to handle message parsing
                    try:
                        message_proc_fcn(message)
                    except (ClockMsgQueueFull,ClockQueueFull):
                        # These are not real problems per-say -just queues not being read
                        self.logger.error('Non critical error encountered while decoding message.')
                        pass
                    except:
                        #self.logger.error('Exception while decoding message.')
                        self.logger.exception('Exception while decoding message.')
                        self.flags.error.set()
                        pass
                        
                    trim_buffer = False
            else:
                #self.logger.debug("Buffer doesn't contain enough chars for \"%s\"" % header)
                trim_buffer = False
                pass
            
        if trim_buffer:
            # No match of message with this starting character, dispose
            #self.logger.debug("No message starts with this char \"%s\"" % self.buffer[0])
            self.buffer = self.buffer[1:]
            
        self.ser_lock.release()   
        
    def _SerialProcessor(self):
        # connect up message processor
        self._MatchMessageHeader()
        
    def _DecodeTimestamp(self, timestamp):
    
        self.logger.debug("Decoding timestamp")
        
        timestamp = timestamp.strip().split(',')
        
        dt = datetime(year=2000+int(timestamp[3]), month=int(timestamp[1]),
            day=int(timestamp[2]), hour=int(timestamp[4]),
            minute=int(timestamp[5]), second=int(timestamp[6]), tzinfo=None)
            
        lat = int(timestamp[7]) + float(timestamp[8])/60.0
        
        if timestamp[9] == 'S': lat = -1.0*lat
        lon = int(timestamp[10]) + float(timestamp[11])/60.0
        
        if timestamp[12] == 'W': lon = -1.0*lon
        alt = float(timestamp[13])

        # Put the newest GPS information block into the queue
        quality = int(timestamp[19])
        
        # Put decoded message into the message queue
        try:
            self.message_queue.put("@@Eq", timeout=1)
        except Full:
            error_msg = 'GPS message queue full.'
            self.logger.error(error_msg)
            raise ClockMsgQueueFull(error_msg)
        except:
            self.logger.error("Unknown error putting to msg queue.")
            raise            
                
        try:
            self.logger.debug("Posting gps msg to queue: %s" % dt)
            self._PostToQueue(dt,lat,lon,alt,quality)
        except ClockQueueFull:
            #clear queue?
            self.logger.error("Error posting to queue. Queue full.")
            raise
        except:
            self.logger.error("Unknown error posting to queue.")
            raise
    
    def _DecodeMode(self, message):
        
        self.logger.debug("Decoding mode")
        
        # msg = @@GdcC<CR><LF>
        # c is current control mode: 0x00=normal 3D, 0x01=position hold, 0x02=2D position, 0x03=Auto-survey (Timing)

        self.mode = ord(message[4])
        self.logger.info("%s%s%s%s(mode: %d)(checksum: %d)" % (message[0],message[1],message[2],message[3],self.mode,ord(message[5])))
        
        # Put decoded message into the message queue
        try:
            self.message_queue.put("@@Gd", timeout=1)
        except Full:
            error_msg = 'GPS message queue full.'
            self.logger.error(error_msg)
            raise ClockMsgQueueFull(error_msg)
        except:
            self.logger.error("Unknown error putting to msg queue.")
            raise  
            
    def _Decode12ChPosData(self, message):
        self.logger.debug("Decoding 12 Channel Position/Status/Data message")
        
        # Put decoded message into the message queue
        try:
            self.message_queue.put("@@Ha", timeout=1)
        except Full:
            error_msg = 'GPS message queue full.'
            self.logger.error(error_msg)
            raise ClockMsgQueueFull(error_msg)    
        except:
            self.logger.error("Unknown error putting to msg queue.")
            raise  
            
    def _DecodeVisibleSat(self, message):
        self.logger.debug("Decoding Visible Satellite message")
        
        # Put decoded message into the message queue
        try:
            self.message_queue.put("@@Bb", timeout=1)
        except Full:
            error_msg = 'GPS message queue full.'
            self.logger.error(error_msg)
            raise ClockMsgQueueFull(error_msg)
        except:
            self.logger.error("Unknown error putting to msg queue.")
            raise  
            
    def _DecodeGPS(self, message):
        self.logger.debug("Decoding non-needed gps message")
        pass
    

            
            
# =========
# Unit Test
# =========
if __name__ == "__main__":
    from xml.dom.minidom import parseString
    from time import ctime
    import logging
    import sys, os
    
    CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    #print CURRENT_DIR
    sys.path.insert(0, CURRENT_DIR)

    from utilities.DAQLogger import DAQLogger, DAQLogClient
    from Engine import EngineFlags

    class tester:
    
        def __init__(self, config, main_logger, logger):
            # add ch to logger
            self.GPS_logger = DAQLogClient(main_logger.log_queue, "GPS")
            
            # Add flags
            self.GPS_flags = EngineFlags()

            self.logger = logger

            self.gps = MotorolaClock(config, self)
            
    # Create the Motorola GPS clock object
    settings = """\
    <Configuration>
    <GpsClock module="MotorolaClock">
        <ComPortNumber>6</ComPortNumber>
        <BaudRate>9600</BaudRate>
        <DataBits>8</DataBits>
        <Parity>N</Parity>
        <StopBits>1</StopBits>
    </GpsClock>
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
    </Configuration>
    """
    
    config = parseString(settings)
    main_logger = DAQLogger(config)
    main_logger.start()
    logger = DAQLogClient(main_logger.log_queue, "MAIN")
    
    logger.debug("Test debug statements")
    
    test = tester(config, main_logger, logger)

    # Start the GPS clock
    logger.info("Starting GPS clock at %s." % ctime())
    test.gps.Start()
    logger.info("Started GPS clock at %s." % ctime())

    sleep(20)

    # Restart the GPS clock
    logger.info("Restarting GPS clock at %s." % ctime())
    #test.gps.Stop()
    #sleep(10)
    #tese = None
    #test = tester(config, main_logger, logger)
    #test.gps.Start()
    test.gps.Restart()
    logger.info("Restarted GPS clock at %s." % ctime() )  
    
    sleep(20)    
    
    # Start the GPS clock
    logger.info("Stopping GPS clock at %s." % ctime())
    test.gps.Stop()
    logger.info("Stopped GPS clock at %s." % ctime())