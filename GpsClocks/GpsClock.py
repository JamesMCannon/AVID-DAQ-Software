import serial
from serial import SerialException
import os

from Clock import *

# Constants and constant dictionaries

kDataBits = {5: serial.FIVEBITS, 6: serial.SIXBITS, 7: serial.SEVENBITS, 8: serial.EIGHTBITS}
kParities = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
kStopBits = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO}

class GpsClock(Clock):
    """
    Specific to GPS clocks (serial port interface)
    """

    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self, config,parent):
        """
        Constructs a GPS clock object according to the supplied XML
        description.
        """
        Clock.__init__(self,parent)
        self.ser = None

        # Read serial port configuration
        #self.comPortNumber = self.GetIntElemVal(config, "ComPortNumber") - 1
        self.comPortNumber = self.GetStrElemVal(config, "ComPortNumber")
        #If number only, convert to integer:
        if self.comPortNumber.isdigit():
            self.comPortNumber = int(self.comPortNumber)
            if os.name=='nt':
                self.comPortNumber -= 1  #subtract 1 on windows

        self.baudRate = self.GetIntElemVal(config, "BaudRate")
        self.dataBits = kDataBits[self.GetIntElemVal(config, "DataBits")]
        self.parity = kParities[self.GetStrElemVal(config, "Parity")]
        self.stopBits = kStopBits[self.GetIntElemVal(config, "StopBits")]


    # =======
    # Methods
    # =======
    def Start(self):
        """
        Begins acquisition of GPS clock data.
        """
        
        self.logger.info("Starting GPS Thread.")
        
        # Open the serial port and launch the thread
        try:
            self.ser = serial.Serial(self.comPortNumber, baudrate=self.baudRate, bytesize=self.dataBits, parity=self.parity, stopbits=self.stopBits)
            self.ser.setTimeout(12.0)  #TODO: Why 12 seconds?
    ##        print 'Serial timeout: %2.2f sec ' % self.ser.getTimeout()
            self.thread = Thread(target=self.MainLoop)
            self.thread.start()
        except Exception, ecc:
            self.logger.exeption('Error in starting serial port.')
            raise Exception(ecc)
        return 0

    def Stop(self):
        """
        Stops acquisition of GPS clock data.
        """
        # Shutdown the GPS clock properly
        self.logger.info('Shutting down GPS ... ')
        if self.thread is not None:
        
            self.running = False                      # Kill the thread
            self.logger.info('Waiting for GPS thread to quit ...')
            self.thread.join()
            self.thread = None
            self.logger.info('Writing Stop Command to GPS ...')
            self.ser.write(self.GetStopCommand())       # Turn off the timestamps

        # Flush the queue
        self.Flush()

        self.logger.info('Closing the GPS serial port ...')
        self.ser.close()                              # Close the serial port
        self.logger.info('GPS shut down ')

    def GetStopCommand(self):
        return ''

    def writeToSerial(self,message):
        """
        Write message to the serial port
        """
        bytes_written = self.ser.write(message)
        if bytes_written != len(message):
            self.logger.warning('WARNING: only %d bytes written for message %s (len %d)' % (bytes_written,message,len(message)))

    def readFromSerial(self,numBytes,start='',max_discard = 1000):
        """
        Read total of numBytes, starting with start string (inclusive)
        """
        f_ord = lambda x: map(ord,list(x))
        try:
            L = len(start)
            output = ''
            count = 0
            
            firstError = True
            while output != start:
                new_byte = self.ser.read(1)
                output += new_byte
                count += 1
                if len(output)==0:
                    if firstError:
                        self.logger.error('Serial port unresponsive')
                        firstError = False
                    self.logger.warning('WARNING: serial port timed out; check to make sure line receiver turned on (waiting for %s)' % start)
                    count -= 1
                    
                if len(new_byte)==0:
                    raise SerialException("Nothing returned from serial port, waiting for %s" % start)
                    
                
                output = output[-L:]
                
                if count > L:
                    self.logger.info('Serial: need: %s (%s); current: %s; discard #: %d' % (f_ord(start),start,f_ord(output),count - L))
                if count-L > max_discard:
                    return None
                

            output += self.ser.read(numBytes-L)
            if len(output) == 0:
                raise SerialException("Nothing read from serial port")
            if len(output)!=numBytes:
                self.logger.error("Expected %d, but read %d from serial port" % (numBytes, len(output)))
                #raise SerialException("Incorrect number of bytes returned from serial port")
                return output
            else:
                return output
        except SerialException, se:
            #keep going in preamble, often just off by one byte in reading output at beginning
            #(so only throw error if in main loop)
            if self.running:
                self.logger.exception('Serial exception occurred: %s')
                raise SerialException("Serial Exception")
            else:
                self.logger.info('%s; not in main loop, so ignoring' % se)
