from cmd import Cmd
from sys import exit,argv,stdin
import sys, os
from getopt import getopt
from multiprocessing import JoinableQueue
from time import sleep
import os.path

import argparse

from serial import Serial, SerialException, SerialTimeoutException

"""
        # Add motorola GPS commands
        self.cmd["start"] = '@@Eq\x01\x35\x0d\x0a'
        self.cmd["stop"] = '@@Eq\x00\x34\x0d\x0a'
        self.cmd["getMode"] = '@@Gd\xff\xdc\x0d\x0a'
        self.cmd["setModeAuto"] = '@@Gd\x03\x20\x0d\x0a'
        self.cmd["stopBbmsg"] = '@@Bb\x00\x20\x0d\x0a'
        self.cmd["stopHamsg"] = '@@Ha\x00\x29\x0d\x0a'
        
        self.msg_hdr['@@Eq'] = (96, self._DecodeTimestamp) #@@Eq message is 96 bytes long
        self.msg_hdr['@@Bb'] = (92, self._DecodeVisibleSat)  #@@Bb message is 96 bytes long
        self.msg_hdr['@@Ha'] = (154, self._Decode12ChPosData)  #@@Ha message is 154 bytes long
        self.msg_hdr['@@Gd'] = (8, self._DecodeMode)  #@@Gd message is 8 bytes long        
"""

if __name__ == '__main__':

    ser = None
    
    # ========================
    # Setup options parser
    # ========================
    parser = argparse.ArgumentParser(description='Check for Serial GPS')
    parser.add_argument("--search", default=False, action="store_true", help="Automatically search for Serial GPS.")
    parser.add_argument('--port',  help="Test port #")
    args = parser.parse_args()

    #print args
    
    if not args.search and args.port is None:
        sys.exit("No argmuents provided. Please run with -h flag for help.")
    
    if args.search:
        comPortNumber = range(30)
    else:
        comPortNumber = [int(args.port)]
            
    comPorts = []
    
    # Loop through all the port numbers in the range and check each one
    for comPort in comPortNumber:
           
        print "Checking serial COM Port: %d" % comPort        
            
        if ser is not None:
            # Check if the serial port is somehow still open
            ser.close()
            #print "Closed serial port. ser=%s" % ser

        # Open the serial port and launch the thread
        try:
            if os.name=='nt':
                ser = Serial('COM%d'%(comPort), baudrate=9600, bytesize=8, parity='N', stopbits=1)
            else:
                ser = Serial(comPort, baudrate=9600, bytesize=8, parity='N', stopbits=1)
        except:
            print 'Serial port does not exist or already in use.'
            continue
        else:
            # ser.setTimeout(2.0)
            ser.timeout = 2.0
            #self.logger.debug("Serial port opened on COM %d with timeout of %d" % (self.comPortNumber, self.ser.getTimeout()))
            #print "Ser=%s" % ser               

            print "Opened Serial port on COM %d" % comPort

        ser.flushInput()
        ser.flushOutput()
                
        print "Writing START msg..."
        try:
            bytes_written = ser.write('@@Eq\x01\x35\x0d\x0a')
        except SerialTimeoutException:
            print "Serial timeout. Could not write START msg to serial GPS."
            continue
        except:
            print "Some other exception happened."
            continue
        else:
            if bytes_written < 8:
                print "Serial port did not transmit full message to GPS."
                continue
        
        print "Reading data..."
        
        for i in range(5):
            try:
                bytes_read = ser.read(96)
            except SerialTimeoutException:
                print "Serial timeout. Could not read full message (%d/96) from serial GPS." % bytes_read
                continue
            except:
                print "Some other exception happened."
                continue
            if len(bytes_read) < 96:
                print "Unexpected data read."
                break
                       
            print bytes_read[:-1]
                
        if len(bytes_read) < 96:
            continue
            
        try:
            bytes_written = ser.write('@@Eq\x00\x34\x0d\x0a')
        except SerialTimeoutException:
            print "Serial timeout. Could not write STOP msg to serial GPS."
            continue
        except:
            print "Some other exception happened."
            continue
        else:
            if bytes_written < 8:
                print "Serial port did not transmit full message to GPS."
                continue
        
        print "Serial GPS found on port: %d" % comPort
                
        comPorts.append(comPort)
                
        ser.close()
        
    msg = "\n\n***  Serial GPS found on port(s):"
    if len(comPorts) == 0:
        print "\n\n***  No Serial GPS found.  ***"
    else:
        for i in comPorts:
            msg = "%s %d" % (msg, i)
        print "%s ***" % msg