from cmd import Cmd
from sys import exit,argv,stdin
import sys, os
from getopt import getopt
from multiprocessing import JoinableQueue
from time import sleep
import os.path
import psutil

# Custom Libraries
from Engine import Engine
from TaskManager import TaskManager
from utilities.DAQLogger import DAQLogger, DAQLogClient
from utilities.DAQConfig import DAQConfig
from __ver__ import __ver__

#TODO LIST
    #TODO: multiprocessing.queue.qsize() is not accurate, use empty()

# Create the command line interpreter class
class CLI(Cmd):
    def __init__(self, engine, task_manager, main_logger, logger):
        Cmd.__init__(self)
        self.engine = engine
        self.task_manager = task_manager
        self.prompt = ""
        #self.intro = "VLF DAQ Command Line Interpreter, version %s" % __ver__
        #self.intro = "VLF DAQ Command Line Interpreter, version %s" % __ver__
        self.logger = logger
        self.main_logger = main_logger
        self.logger.info("VLF DAQ Command Line Interpreter, version %s" % __ver__)

    def emptyline(self):
        return
        
    def do_start(self, args):
        self.logger.info("VLFDAQ Starting...")
        
        self.engine.Start()
        self.task_manager.Start()
        
    def help_start(self):
        print "syntax: start -- Starts the VLF DAQ Engine        "
        
    def do_stop(self, args):
        self.logger.info("VLFDAQ Stopping...")
        try:
            self.engine.Stop()
        except:
            self.logger.exception("Exception on engine.Stop()")
            
        try:
            self.task_manager.Stop()
        except:
            self.logger.exception("Exception on task_manager.Stop()")

        self.logger.info("VLFDAQ Stopped. Waiting further command.")
        
    def help_stop(self):
        print "syntax: stop -- Stops the VLF DAQ Engine          "
        
    def do_quit(self, args):
        self.logger.info("VLFDAQ Quitting...")

        try:
            self.engine.Quit()
        except:
            self.logger.exception("Exception on engine.Quit()")
          
        try:  
            self.task_manager.Quit()
        except:
            self.logger.exception("Exception on task_manager.Quit()")
            
##        raw_input('Press ENTER to exit  ')
        
        self.main_logger.stop()
        
        # print "\'So long, and thanks for all the fish.\'"
        # print "\nThe sun never sets on Stanford VLF."
        print "\n\t\tsee you space cowboy..."
        return True
        
    def help_quit(self):
        print "syntax: quit -- Stops the VLF DAQ Engine and exits"
        print "        q    -- Stops the VLF DAQ Engine and exits"
        print "        Q    -- Stops the VLF DAQ Engine and exits"

    def do_settings(self,args):
        print self.engine.GetSettingsFile()

    def do_location(self,args):
        print self.engine.GetLocation()

    def help_location(self):
        print "Print latest GPS location to the screen"

    def do_system_status(self):
        print "Prints System Status - for Line Receiver v3 and up."
        
    def do_version(self,args):
        print __ver__

    def do_status(self, args):
        print self.engine.GetStatus()

    do_q = do_quit
    help_q = help_quit
    do_Q = do_quit
    help_Q = help_quit


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()


    from optparse import OptionParser
    from xml.dom.minidom import parse
    
    if not os.path.isdir('log'):
        os.makedirs('log')

    # ========================
    # Setup options parser
    # ========================
    parser=OptionParser(version= __ver__,
                        description='VLF data acquisition program. ')
    parser.add_option("--settings",dest='settings_file', default='DaqSettings.xml', type="string",
                      help="Settings (.xml) filename.  Default: %default")
    parser.add_option('--autostart', dest="autostart", default=False, action="store_true",
                      help="Start daq acquisition without further input (default %default)")
    parser.add_option('--debug', dest="debug_on", default=False, action="store_true",
                      help="Start daq acquisition with debug mode turned on")
    (options,args) = parser.parse_args()

    #print options
    
    # ========================
    # Config and Settings checking
    # ========================
    if not os.path.isfile(options.settings_file):
        #raise '%s does not exist' % options.settings #Error: exceptions must be old-style classes... JCC 04/02/12  
        sys.exit('Error: %s does not exist' % options.settings) # quit program if setting file doesn't exist
        
    print 'VLF DAQ Software v%s' % __ver__
    print 'Settings file: %s' % options.settings_file
    print 'Autostart    : %s' % str(options.autostart)
    #print 'NOTE: DO NOT SCROLL CONSOLE WINDOW DURING ACQUISITON'
    
    print "Parsing Settings file..."
    try:
        options.settings = DAQConfig(parse(options.settings_file))
    except:
        sys.exit("Parsing of settings file \'%s\' failed.\n****Exiting****" % options.settings)
        

    # Give ourselves high system priority:
    psutil.Process(os.getpid()).nice(psutil.REALTIME_PRIORITY_CLASS)

    # ========================
    # Setup Logger
    # ========================
    #log_queue = JoinableQueue()
    main_logger = DAQLogger(options)
    main_logger.start()
    
    logger = DAQLogClient(main_logger.log_queue, "MAIN")
    logger.debug("Main logger ready.")
    sleep(1)
    


    # ========================
    # Setup Engine object
    # ========================
    try:
        engine = Engine(options.settings, main_logger.log_queue)
    except:
        #logger.exception("Error in initializing ENGINE.")
        
        # Use error instead of exception since any exception 
        #  should have been printed in the engine
        #logger.error("Error in initializing ENGINE.")
        sleep(2)
        main_logger.stop()

        sys.exit("****Exiting****")
        
    # ========================
    # Setup Task Manager
    # ========================
    try:
        task_manager = TaskManager(options.settings, main_logger.log_queue)
    except:
        
        #logger.error("Error in initializing tastk manager.")
        main_logger.stop()
        
        sys.exit("****Exiting****")    
        
    # ========================
    # Main Loop
    # ========================
    
    # Create and launch the command line interpreter
    cli = CLI(engine,task_manager, main_logger, logger)
    engine.SetParent(cli) #comment out if cli not parent
    
    if options.autostart:
        cli.do_start(())
        
    cli.cmdloop()

