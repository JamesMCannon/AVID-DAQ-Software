import serial
from serial import SerialException, SerialTimeoutException
import os
from threading import Thread, Lock
from Queue import Queue, Full, Empty
from time import sleep

from Clock import *
from GPSExceptions import *

__all__ = ['SerialClock']
# Constants and constant dictionaries

kDataBits = {5: serial.FIVEBITS, 6: serial.SIXBITS, 7: serial.SEVENBITS, 8: serial.EIGHTBITS}
kParities = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
kStopBits = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO}

class SerialClock(Clock):
    """
    Specific to serial port based GPS clocks (serial port interface)
    
    Public Functions:
    
        Start()
        Start()
        WriteToSerial()
        ReadFromSerial()
    
    Private Functions:
    
        _decodeHousekeeping()
        _SerialReaderThread()
    
    Error Handling:
    
        Start()                 SerialException
                                    error instantiating serial class
                                        error raised and handled by parent class

        WriteToSerial()         SerialException?
                                    serial port error
                                        set flag, return false
                                SerialTimeoutException
                                    timeout reading from serial port
                                        set flag, return false?
        
        ReadFromSerial()        SerialException
                                    serial port error
                                        set flag, keeps looping
                                Exception
                                    unknown serial port error
                                        set flag, contin
                                        
        _SerialReaderThread     Same as ReadFromSerial()
                                    caught error while reading from serial port
                                        break loop and stop (error flag set in ReadFromSerial()

    """

    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self, config, parent):
        """
        Constructs a GPS clock object according to the supplied XML
        description.
        """
        Clock.__init__(self,parent)
        self.ser = None
        self.ser_lock = Lock()
        self.ser_thread = None

        # Read serial port configuration
        # self.comPortNumber = self.GetIntElemVal(config, "ComPortNumber") - 1

        # 4.22.2018 -- new pySerial module wants 'COM<int>' string. Storing integer, changing the start command.
        self.comPortNumber = int(config.GetStrElemVal("ComPortNumber"))
        # # If number only, convert to integer:
        # if self.comPortNumber.isdigit():
        #     self.comPortNumber = int(self.comPortNumber)
        #     if os.name=='nt':
        #         self.comPortNumber -= 1  #subtract 1 on windows
        self.logger.info("Serial COM Port: %d" % self.comPortNumber)
                
        self.baudRate = config.GetIntElemVal("BaudRate")
        self.dataBits = kDataBits[config.GetIntElemVal("DataBits")]
        self.parity = kParities[config.GetStrElemVal("Parity")]
        self.stopBits = kStopBits[config.GetIntElemVal("StopBits")]

        # Delay rate: based on baud rate - there would be at max buadRate/(8+1 bits per byte)
        self.delaytime = 0.001
        self.logger.debug("Serial check delay set to %s" % self.delaytime)
        
        # Serial message queue (raw returned from GPS)
        self.message_queue = Queue(60)
        
        #initialize variables to hold housekeeping data values
        self.clock_good = False
        self.clock_freq_error = 0
        self.clock_phase_error = 0
        self.dac_value = 0
        # voltage rails...

        # Serial Buffer
        self.buffer = ''
        
        # Message header definitions and hooks
        self.msg_hdr = {}
        self.msg_hdr["@@VLF"] = (34, self._decodeHousekeeping)
        
        # Command messages
        self.cmd = {}
        self.cmd["HSKP"] = '@@VLF\x0d\x0a'
        
        self.logger.debug('SerialClock initialized.')
        
    # =======
    # Methods
    # =======
    def Start(self):
        """
        Begins acquisition of GPS clock data.
        """
        
        self.logger.info("Starting Serial GPS")
        self.logger.debug("Opening Serial port on COM %d" % self.comPortNumber)
        
        if self.ser is not None and self.ser.isOpen():
            # Check if the serial port is somehow still open
            self.logger.warning("Serial port is already open. ser=%s" % self.ser)
        else:
        
            # Open the serial port and launch the thread
            try:
                # 4.22.2018 -- adapting to work with new version of pySerial
                self.ser = serial.Serial() # clear and close before opening
                self.ser.close()
                self.ser = serial.Serial('COM%d'%self.comPortNumber, 
                                        baudrate=self.baudRate, 
                                        bytesize=self.dataBits, 
                                        parity=self.parity, 
                                        stopbits=self.stopBits,
                                        timeout=12)
            except:
                self.logger.error('Error in starting serial port.')
                raise
            else:
                # self.ser.setTimeout(12.0)  #TODO: Why 12 seconds?
                #self.logger.debug("Serial port opened on COM %d with timeout of %d" % (self.comPortNumber, self.ser.getTimeout()))
                self.logger.debug("Ser=%s" % self.ser)                
 
                self.logger.debug("Opened Serial port on COM %d" % self.comPortNumber)
        
        self.logger.debug("Starting SerialGPS thread")
        self.ser_thread = Thread(target=self._SerialReaderThread)
        self.ser_thread.start()
        self.logger.status("Serial thread started.")
 
        self.logger.info("Starting GPS Mainloop")
        #self.MainLoop()
        self.thread = Thread(target=self.MainLoop)
        self.thread.start()
        self.logger.status("GPS Mainloop thread started.")

    def Stop(self):
        """
        Stops acquisition of GPS clock data.
        """
        
        if not self.flags.is_stopped.is_set():
            # Shutdown the GPS clock properly
            self.logger.info('Shutting down GPS ... ')

            # Sending Stop command
            #self.logger.info('Writing Stop Command to GPS ...')
            self.WriteToSerial(self.cmd["stop"])
                
            # Stop main loop first
            if self.thread is not None:
                self.running = False
                # Kill the thread
                self.logger.info('Waiting for Mainloop thread to quit ...')
                self.thread.join()
                self.thread = None

            # Stop serial port thread
            if self.ser_thread is not None:
                self.ser_running = False
                # Kill the thread
                self.logger.info('Waiting for serial thread to quit ...')
                self.ser_thread.join()
                self.ser_thread = None

            # Close these queues??
            #self.message_queue
            if not self.message_queue.empty():
                self.logger.debug("Message queue not empty yet")
                while not self.message_queue.empty():
                    self.message_queue.get()
                self.logger.info("Message queue emptied")
                
            #self.timestamp_queue    
            if self.timestamp_queue.empty():
                self.logger.debug("Timestamp queue not empty yet")
                while not self.timestamp_queue.empty():
                    self.timestamp_queue.get()
                self.logger.info("Timestamp queue emptied")
                
            # Flush the queue ?? Not sure what this actually will do...
            self.Flush()

            self.logger.info('Closing the GPS serial port ...')
            try:
                self.ser.close()                              # Close the serial port
            except AttributeError:
                # Typically, this happens when the serial port dies and is no longer 'open'
                # PySerial returns AttributeError. Since closed, continue
                self.logger.warning('Caught serial port AttributeError because GPS already closed down or missing')
                pass
            except:
                self.logger.exception('Some other exception happened while closing serial port.')
                pass
                
            self.logger.debug("Ser=%s" % self.ser)
            self.ser = None
            
            self.flags.is_running.clear()
            self.flags.is_stopped.set()
            
            self.logger.status('GPS shut down ')
            
        #return True
        
    def Restart(self):
        """ 
        Restarts the GPS module and all subprocesses
        
        returns True if ok
        """
        if not self.flags.is_stopped.is_set() and not self.flags.is_running.is_set():
            # already doing a restart
            return True
        
        self.flags.num_restarts += 1
        self.logger.warning('***This is GPS restart #%d!!!***' % self.flags.num_restarts)
        
        try:
            self.Stop()
        except:
            return False
        # Verify stopped
        if not self.flags.is_stopped.wait(60):
            self.logger.error('GPS stopping failed.')
            return False
        self.logger.info('GPS fully Stopped.')
        
        self.flags.is_stopped.clear()
        
        self.buffer = ''
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
        #sleep(10)
        
        try:
            self.Start()
        except:
            return False
            
        # Verify restarted
        if not self.flags.is_running.wait(60):
            self.logger.error('GPS restart failed.')
            return False
        
        self.logger.debug('GPS Started.')
        
        # Clear any error flags
        if self.flags.error.is_set():
            self.flags.error.clear()
        
        return True
        
    def WriteToSerial(self,message):
        """
        Write message to the serial port
        """
        if not self.ser is None:
            try:
                bytes_written = self.ser.write(message)
            except SerialException:
                #if not already resetting
                self.logger.error('Error while writing to serial port.')
                self.flags.error.set()
                
            except SerialTimeoutException:
                # if not already resetting
                self.logger.error('Timeout error while writing to serial port.')
                self.flags.error.set()
                
            except:
                self.logger.error('Unknown error while writing to serial port.')
                self.flags.error.set()
                
            else: 
                if bytes_written != len(message):
                    self.logger.warning('Only %d bytes written for message %s (len %d)' % (bytes_written,message,len(message)))
                
                #self.logger.debug('Wrote to ser: %s' % message)
            
    def ReadFromSerial(self):
        try:
            # Blocks until one byte is read, until timeout specified
            # Setting timeout to 2 second for this Motorola GPS because 
            #  every two hours, it skips slightly if there's no antenna connected
            return self.ser.read(2)
        except SerialException:
            self.logger.error('Serial port read error:')
            self.flags.error.set()
            raise
        except:
            self.logger.error('Unknown error while reading from serial port.')
            self.flags.error.set()
            raise

            
    def _decodeHousekeeping(self):
        """
        Read message from embedded controller.
        """
        self.logger.debug("Decoding Housekeeping message")
        self.clock_good = False
        self.clock_freq_error = 0
        self.clock_phase_error = 0
        self.dac_value = 0
        
        #figure some way to skip if hardware not right version
        
    def _SerialProcessor(self):
        raise NotImplementedError()
        pass        
       
    def _SerialReaderThread(self):
    
        self.logger.debug("Started Serial Reader")
        
        self.ser_running = True
        
        while self.ser_running:
        
            #self.logger.debug("Started readFromSerial")
            
            sleep(self.delaytime)
            try:
                # Blocks until one byte read
                new_byte = self.ReadFromSerial()
                #self.logger.debug('read: %s' % new_byte)
            except:
                # Caught some error - in this case we break the loop
                self.ser_running = False
                break
            else:
                self.ser_lock.acquire()
                
                self.buffer += new_byte
                #self.logger.debug("Buffer len: %d" % len(self.buffer))
                
                self.ser_lock.release()            

                self._SerialProcessor()
               
        
        self.logger.debug("Finished serial Reader")