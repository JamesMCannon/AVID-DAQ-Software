## Adaptation fo ConsoleHandler
##

import sys
from logging import Handler, Formatter ,addLevelName, CRITICAL, ERROR, WARNING

from LogLevels import EXCEPTION, STATUS, TIMESTAMP

import colorama 
from colorama import Fore, Style, Back
colorama.init(autoreset=True, strip=None)

from string import replace

try:
    unicode
    _unicode = True
except NameError:
    _unicode = False

addLevelName(EXCEPTION, 'EXCEPTION')
addLevelName(STATUS, 'STATUS')
addLevelName(TIMESTAMP, 'TIMESTAMP')
    
class ConsoleHandler(Handler):
    """
    A handler class which writes logging records, appropriately formatted,
    to a stream. Note that this class does not close the stream, as
    sys.stdout or sys.stderr may be used.
    Modified JCC 2013.01
    """

    def __init__(self):
        Handler.__init__(self)
        
        # Hard code sys.stdout for stream
        self.stream = sys.stdout
        
        self.prev = None

    def flush(self):
        """
        Flushes the stream.
        """
        if self.stream and hasattr(self.stream, "flush"):
            self.stream.flush()
    
    def cformat(self, record):
        """
        Format the specified record with colored version.

        If a formatter is set, use it. Otherwise, use the default formatter
        for the module.
        """
        return self.formatter.cformat(record)
        
    def emit(self, record):
        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline.  If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream.  If the stream
        has an 'encoding' attribute, it is used to determine how to do the
        output to the stream.
        """
        #print self.formatter
        
        #print "got here"
        try:
            msg = self.cformat(record)
            #print msg
            
            stream = self.stream
            
            if record.levelno is TIMESTAMP:
            
                # for timestamps, only want to do a \r
                fs = "%s\r"
                self.prev = "time"
                
            elif record.levelno is STATUS:
            
                # Add in date/time for status messages
                msg = msg.replace(']', '-%s]' % self.formatter.formatTime(record, "%Y-%m-%d %H:%M:%S"), 1)
                
                fs = "%s\n"
                self.prev = None
                
            elif record.levelno is ERROR :
            
                # Add in coloring for exception messages
                msg = msg.replace('\n  ', '\n  %s%s' % (Fore.MAGENTA, Style.BRIGHT), 1).replace(':', ':%s' % Style.RESET_ALL, 1)

                fs = "%s\n"
                self.prev = None
                
            elif record.levelno is EXCEPTION or record.levelno is ERROR :
            
                # Add in coloring for exception messages
                msg = msg.replace('\n  ', '\n  %s%s' % (Fore.RED, Style.BRIGHT), 1).replace(':', ':%s' % Style.RESET_ALL, 1)

                fs = "%s\n"
                self.prev = None

            else:
            
                if self.prev == "time":
                    fs = "\n%s\n"
                else:
                    fs = "%s\n"
                
                self.prev = None
            
            if not _unicode: #if no unicode support...
                stream.write(fs % msg)
            else:
                try:
                    if (isinstance(msg, unicode) and
                        getattr(stream, 'encoding', None)):
                        ufs = fs.decode(stream.encoding)
                        try:
                            stream.write(ufs % msg)
                        except UnicodeEncodeError:
                            #Printing to terminals sometimes fails. For example,
                            #with an encoding of 'cp1251', the above write will
                            #work if written to a stream opened or wrapped by
                            #the codecs module, but fail when writing to a
                            #terminal even when the codepage is set to cp1251.
                            #An extra encoding step seems to be needed.
                            stream.write((ufs % msg).encode(stream.encoding))
                    else:
                        stream.write(fs % msg)
                except UnicodeError:
                    stream.write(fs % msg.encode("UTF-8"))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
            
        #print "finished"
        
        
class ColoredFormatter(Formatter):
    # Layer over Formatter to print color on 
    
    def __init__(self, fmt=None, datefmt=None):
     
        #print 'format: %s' % fmt
        Formatter.__init__(self, fmt, datefmt)
        
    def cformat(self, record):
        # setup coloring scheme

        TextRed = '%s%s' % (Fore.RED, Style.BRIGHT)
        TextMagenta = '%s%s' % (Fore.MAGENTA, Style.BRIGHT)
        TextYellow = '%s%s' % (Fore.YELLOW, Style.BRIGHT)
        TextGreen = '%s%s' % (Fore.GREEN, Style.BRIGHT)
        TextReset = '%s' % Style.RESET_ALL
        
        # hack color over 
        if record.levelno >= CRITICAL:
            clevelname = TextRed
        elif record.levelno >= EXCEPTION:     
            clevelname = TextRed        
        elif record.levelno >= ERROR:    
            clevelname = TextMagenta   
        elif record.levelno == STATUS:
            clevelname = TextGreen
        elif record.levelno >= WARNING:  
            clevelname = TextYellow      
        else:
            clevelname = ''
            TextReset = ''
        
        # adding level name coloing
        #record.levelname = '%s%s%s' % (clevelname, record.levelname, TextReset)
        
        # coloring module name
        record.name = '%s%s%s' % (clevelname, record.name, TextReset)
        
        #sys.stdout.write('ln: %s\n' % record.levelname) 
        #print record
        
        prepped_msg = self.format(record)
        #print temp
        
        return prepped_msg 
            
