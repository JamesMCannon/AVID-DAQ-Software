## A Thread safe logging mechanism
## Modified JCC 4/18/12
## Rev 2012.04.18 - Initial Version
## Rec 2012.05.29 - Modification to use in VLFDAQ, add client for use in modules
## Rec 2013.01.22 - Adding color to highlight problems quickly


import sys, socket
import os
from os.path import basename
import cStringIO, traceback
import multiprocessing
from multiprocessing import Process, JoinableQueue
import threading
import logging
from logging import handlers, LogRecord, addLevelName, getLevelName
from time import sleep, strftime, gmtime, time, clock
from datetime import datetime

if os.name != 'nt':
    clock = time

# Homegrown Handlers
from LogHandlers.EmailHandler import EmailHandler
from LogHandlers.ConsoleHandler import ConsoleHandler, ColoredFormatter
from LogHandlers.LogLevels import EXCEPTION, STATUS, TIMESTAMP
from colorama import Fore, Style, Back

from DAQConfig import DAQConfig
              
addLevelName(EXCEPTION, 'EXCEPTION')
addLevelName(STATUS, 'STATUS')
addLevelName(TIMESTAMP, 'TIMESTAMP')

"""
For Reference
CRITICAL = 50
FATAL = CRITICAL
ERROR = 40
WARNING = 30
WARN = WARNING
INFO = 20
DEBUG = 10
NOTSET = 0
"""

         
class DAQLogger():

    def __init__(self, options):

        self.process = None
        self.listener = None
        
        #self.log_queue = BufferedReadQueue()
        self.log_queue = JoinableQueue()
        self.raw_queue = JoinableQueue()
        
        settings = options.settings
        
        self.settings = {}  
        
        if os.name == 'nt':
            self.od = "%s\\" % settings.GetStrElemVal("LogDir", 'log') 
        elif os.name =='posix':
            self.od = "%s/" % settings.GetStrElemVal("LogDir", 'log') 
        if not os.path.exists(self.od):
            os.makedirs(self.od)
  
        self.settings['od'] = self.od
            
        self.settings['name'] = settings.GetStrElemVal("station_name",'station_name')
        print "Station Name: %s" % self.settings['name']
        
        self.settings['email'] = settings.GetIntElemVal("ErrorEmail",1) 
        print "Error email: ON" if self.settings['email']==1 else "Error email: OFF"
        if self.settings['email']==1:
            self.settings['ErrorEmailFrom'] = settings.GetStrElemVal("ErrorEmailFrom","ErrorEmailFrom")
            self.settings['ErrorEmailTo'] = settings.GetStrElemVal("ErrorEmailTo","ErrorEmailTo")
            self.settings['ErrorEmailPw'] = settings.GetStrElemVal("ErrorEmailPw","ErrorEmailPw")

            print "Sending log emails from: %s"%self.settings['ErrorEmailFrom']
            print "Sending log emails to: %s"%self.settings["ErrorEmailTo"]
        self.settings['post'] = settings.GetIntElemVal("ErrorPost",1) 
        print "Error POST: ON" if self.settings['post']==1 else "Error POST: OFF"
        
        # this is main logger level
        self.settings['loggerlevel'] = self._process_log_level("DEBUG") # Hard code to debug to allow max flexibility
        
        #self.settings['consolelevel'] = self._process_log_level(settings.GetStrElemVal("ConsoleLevel", "TIMESTAMP"))
        
        if options.debug_on:
            #print "Setting console display level to 'DEBUG'"
            #self.settings['consolelevel'] = self._process_log_level("DEBUG")
            self.settings['consolelevel'] = self._process_log_level("DEBUG")
        else:
            self.settings['consolelevel'] = self._process_log_level(settings.GetStrElemVal("ConsoleLevel", "TIMESTAMP"))
            #print "Setting console display level to 'TIMESTAMP'"
            #self.settings['consolelevel'] = self._process_log_level("TIMESTAMP")
            #self.settings['consolelevel'] = TIMESTAMP
        print "Setting console display level: %s" % self._process_log_level(self.settings['consolelevel'])
        
        self.settings['logfilelevel'] = self._process_log_level(settings.GetStrElemVal("LogFileLevel", "WARNING"))
        print "Setting logfile level: %s" % self._process_log_level(self.settings['logfilelevel'])
        
        self.settings['postfilelevel'] = self._process_log_level(settings.GetStrElemVal("PostLevel","WARNING"))
        print "Setting POST level: %s" % self._process_log_level(self.settings['postfilelevel'])
        
        self.settings['posturl'] = settings.GetStrElemVal("LogPostUrl","/field_sites_logs/logging.php")
        self.settings['postserver'] = settings.GetStrElemVal("LogPostServer","vlf-engineering.stanford.edu:80")
        
        # Setup basic logger. Will overwrite
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)

        
        #print "Logger level set."
        
        self.listener = Process(target = _log_listener, args=(self.log_queue, self.raw_queue))
        self.listener.daemon = True
        self.listener.start()
        self.lpid = self.listener.pid
        self._log("Starting Logger Listener: %d" % self.lpid)

        
    def start(self):
        self.process = Process(target = _log_processing, args=(self.settings, self.raw_queue))
        self.process.daemon = True
        self.process.start()
        self.pid = self.process.pid
        self._log("Starting Logging Thread: %d" % self.pid)
    
    def stop(self):
        self._log("Closing down logging queue.")       
        self.log_queue.put(None)

        self.raw_queue.join()
        self.log_queue.join()
        
        self.process.terminate()
        logging.shutdown()
        
        #print "Logger finished."
        
    def _process_log_level(self, level):
        
        """
        if level == "DEBUG":
            return logging.DEBUG
        elif level == "INFO":
            return logging.INFO
        elif level == "WARNING":
            return logging.WARNING
        elif level == "CRITICAL":
            return logging.CRITICAL
        else:
            return logging.INFO
        """
        return getLevelName(level)
           
            
    def _log(self, message):
        # Log messages within logger
        #print "got into log"
        #Add timestamp
        
        log_entry = LogRecord("LOG", logging.INFO, "", 0, message, (), None, None)
        
        self.log_queue.put(log_entry)

        
def _log_listener(log_queue, raw_queue):
    # based on code and explanation here: http://petersobot.com/blog/introducing-forever-fm/
    
    #print "Listening"
    
    try:
        while True:
            #time_stamp, mod_name, level, msg = log_queue.get()
            log_record = log_queue.get()
            #print "pulled out: %s" % log_record

            #raw_queue.put((time_stamp, mod_name, level, msg))
            raw_queue.put(log_record)
            #print "pushed out something"
            
            log_queue.task_done()

            if log_record == None:
                return
    except:
        pass

def _log_processing(settings, raw_queue):

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
        
    # Logfile Handler
    rotating_formatter = logging.Formatter('%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s', "%Y-%m-%d %H:%M:%S") 
    rotating_formatter.converter = gmtime
    rotating_handler = logging.handlers.RotatingFileHandler('%sVLFDAQ.log' % settings['od'], maxBytes=1000000)
    #rotating_handler = myHandlers.MyRotatingFileHandler('%sVLFDAQ.log' % self.od, maxBytes="1000000") #shutil based rotating handler
    rotating_handler.setLevel(settings['logfilelevel']) # Set default to WARNING
    rotating_handler.setFormatter(rotating_formatter)
    logger.addHandler(rotating_handler)

    # Console Handler
    #stream_formatter = ColoredFormatter('%(asctime)s [%(name)s-%(levelname)s] %(message)s', "%Y-%m-%d %H:%M:%S")
    #stream_formatter = ColoredFormatter('[%(name)s-%(levelname)s] %(message)s')
    if settings['consolelevel'] == logging.DEBUG:
        #stream_formatter = ColoredFormatter('%(asctime)s [%(name)s] %(message)s', "%Y-%m-%d %H:%M:%S:")
        stream_formatter = ColoredFormatter('%(asctime)s [%(name)s] %(message)s')
        stream_formatter.converter = gmtime
    else:
        stream_formatter = ColoredFormatter('[%(name)s] %(message)s')
    #stream_handler = ConsoleHandler(sys.stdout)
    stream_handler = ConsoleHandler()
    stream_handler.setLevel(settings['consolelevel'])
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)
    
    # Optional Handlers
    
    # Email handler            
    if settings['email'] == 1:
        print "Setting up Email Handler"
        hostname = socket.gethostname() # Get site name HERE
        hostip = socket.gethostbyname(hostname)
        
        dash = '-'*25
        footer_msg = 'You have been notified. For the good of the VLF Empire, ACT NOW!'
        footer = '\nMessage sent from: %s (IP: %s)\n\n%s\n%s\n%s\n' % (settings['name'], hostip, dash, footer_msg, dash)
        
        email_formatter = logging.Formatter('%(message)s' + footer)
        email_handler = EmailHandler(settings['name'],
                        ('smtp.gmail.com',587),
                        settings['ErrorEmailFrom'],
                        [settings['ErrorEmailTo']],
                        'PythonDAQ Experienced an Error.',
                        (settings['ErrorEmailFrom'],settings['ErrorEmailPw']),
                        (), '%sVLFDAQ.log' % settings['od']) 
        email_handler.setLevel(logging.CRITICAL) # email will always be critical
        email_handler.setFormatter(email_formatter)
        logger.addHandler(email_handler)
        
    # HTTP POST Handler
    if settings['post'] == 1:
        print "Setting up POST Handler"
        POST_formatter = logging.Formatter('%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s')
        POST_handler = logging.handlers.HTTPHandler(settings['postserver'], settings['posturl'], "POST")
        POST_handler.setLevel(settings['postfilelevel'])
        POST_handler.setFormatter(POST_formatter)
        logger.addHandler(POST_handler)

    q = raw_queue

    # Start loop
    while True:

        #self.log("No more logs. %s" % self.log_queue.qsize())
        # Pull out each item in the queue, if any
        while (q.qsize() > 0):

            #time_stamp, mod_name, level, msg = q.get()
            log_record = q.get()
            
            if log_record is None:
                q.task_done()
                return
                
            q.task_done()
            
            #print strftime("%Y-%m-%d %H:%M:%S.%f", time_stamp)
            #print mod_name
            #print level_name
            #print msg
            
            #level_name = logging.getLevelName(level)
            #msg = "%s [%s-%s]: %s" % (time_stamp.strftime("%Y-%m-%d %H:%M:%S.%f"), mod_name, level_name, msg)
            #msg = "%s [%s-%s]: %s" % (time_stamp.strftime("%Y-%m-%d %H:%M:%S"), mod_name, level_name, msg)
            #logger.log(level, msg) 
            
            #print "rcvd: %s" % log_record 
            
            #logger.callHandlers(log_record)
            logger.handle(log_record)
            
        # wait a second - this minimizes cpu when not running
        else:
            sleep(0.001)
            #print "sleeping"
        
    return

"""
class DAQRecord(LogRecord):
    
    def __init__(self, name, level, pathname, lineno, msg, args, exc_info, func=None):
        
        LogRecord.__init__(self, name, level, pathname, lineno, msg, args, exc_info, func=None):
        
        self.DAQ_ts = datetime.utcnow()
"""
    
class DAQLogClient():

    def __init__(self, log_queue, module_name):
        self.n = module_name
        self.log_queue = log_queue
    
    def _log(self, level, msg):
        
        #print "logging something"
        #level_name = logging.getLevelName(level)
    
        #self.log_queue.put((level, "%s [%s-%s]: %s" %(strftime("%Y-%m-%d %H:%M:%S", gmtime()), self.n, level_name, msg)))
        
        
        """
        def makeRecord  (self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None):
                        (self, name, level, pathname, lineno, msg, args, exc_info, func=None):
        rv = LogRecord(None, None, "", 0, "", (), None, None)
        """
        
        log_entry = LogRecord(self.n, level, "", 0, msg, (), None, None)
        
        #print "putting: %s" % log_entry
        
        self.log_queue.put(log_entry) 

        
    def debug(self, msg):
        self._log(logging.DEBUG, msg)
        
    def status(self, msg):
        self._log(STATUS, msg)
        
    def timestamping(self, msg):
        self._log(TIMESTAMP, msg)
        
    def info(self, msg):
        self._log(logging.INFO, msg)
        
    def warning(self, msg):
        self._log(logging.WARNING, msg)     
        
    def error(self, msg):
        self._log(logging.ERROR, msg)     
        
    def critical(self, msg):
        self._log(logging.CRITICAL, msg)
        
    def exception(self, msg):
        
        # Grab current exception info
        exc_type, exc_value, exc_tb = sys.exc_info()
        #exc_type, exc_value = sys.exc_info()[:2]
        
        #print "Exection Type: %s" % exc_type
        #print "Exception Value: %s" % exc_value
        #print "Exception Traceback: %s" % exc_tb
        
        # Modified from logging.formatter.formatException
        #traceback.print_exception(ei[0], ei[1], ei[2], None, sio)
        
        # Get traceback information 
        # type: gets the exception type of the exception being handled (a class object); 
        # value: gets the exception parameter (its associated value or the second argument to raise, which is always a class instance if the exception type is a class object); 
        # traceback: gets a traceback object (see the Reference Manual) which encapsulates the call stack at the point where the exception originally occurred.

        # hacked way to pretty print stuff based on format_exception usage
        #ex = traceback.format_exception(exc_type, exc_value, exc_tb)
        #print ex

        printout = ''
        
        #for line in ex[1:-1]:
        #    printout += "  " + line.replace('File ', '', 1 ).replace('\n', ':', 1).rstrip('\n') + "\n"
        #print printout

        for exc in traceback.format_exception_only(exc_type, exc_value):
            #printout += '  %s%s%s\n' % (Fore.RED, Style.BRIGHT, exc.rstrip('\n').replace(':', ':%s' % Style.RESET_ALL, 1))
            printout += '  %s\n' % exc.rstrip('\n')
        
        for filename, line_no, name, line in traceback.extract_tb(exc_tb):
            printout += '    %s (%d):%s\t\t%s\n' % (basename(filename), line_no, name, line )
        
        #print printout
        
        self._log(EXCEPTION, "%s\n%s" % (msg, printout.rstrip('\n')))

    
if __name__ == '__main__':

    import os
    from xml.dom.minidom import parseString
    from xml.dom.minidom import parse
    from optparse import OptionParser
    
    from DAQConfig import DAQConfig

    if os.name == 'nt':
        output_dir = ''
    elif os.name =='posix':
        output_dir = 'outputs/'
        
    #log_queue = JoinableQueue()
    settings = """\
    <DaqConfiguration>
        <StationSettings>
            <contact_info>JC</contact_info>
            <hardware_description>Intel i5</hardware_description>
            <install_date>4/2012</install_date>
            <adc_type>PCI-6050</adc_type>
            <station_id>SUA</station_id>
            <antenna_bearings>None</antenna_bearings>
            <antenna_description>None</antenna_description>
            <station_name>ATB0</station_name>
            <station_description>AWESOME Testbench #0</station_description>
        </StationSettings>
        <Logger>
            <PostLevel>WARNING</PostLevel>
            <LogFileLevel>WARNING</LogFileLevel>
            <LogPostUrl>/field_sites_logs/logging.php</LogPostUrl>
            <LogLevel>DEBUG</LogLevel>
            <LogPostServer>vlf-engineering.stanford.edu:80</LogPostServer>
            <ErrorPost>0</ErrorPost>
            <LogDir>log</LogDir>
            <ConsoleLevel>INFO</ConsoleLevel>
            <ErrorEmail>0</ErrorEmail>
        </Logger>
    </DaqConfiguration>    
    """
    
    parser=OptionParser(version= '1', description='Test')
    parser.add_option('--debug', dest="debug_on", default=False, action="store_true",
                      help="Start daq acquisition with debug mode turned on")
                      
    (options,args) = parser.parse_args()
    options.settings = DAQConfig(parseString(settings))
    
    main_logger = DAQLogger(options)
    
    main_logger.start()
    
    test_the_logger = DAQLogClient(main_logger.log_queue, "Tester")
    test_the_logger.debug("Started testing this logger.")
    test_the_logger.info("test info")
    test_the_logger.warning("test warning")
    test_the_logger.error("test error")
    test_the_logger.critical("Testing critical error")
    
    sleep(5)
    
    test_the_logger.info("woken after 5 sec")
    
    try:
        1/0
    except:
        test_the_logger.exception("Trying an exception")
    
    main_logger.stop()
    