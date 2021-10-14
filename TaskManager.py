from sys import stdout, exc_info
#from threading import Event, Thread, Lock
from threading import Thread

from multiprocessing import Queue, Process, get_logger
from Queue import Full, Empty
import psutil 
from time import sleep
import os
from xml.dom.minidom import parse
import random
#import logging, logging.config
import traceback
import Tasks
from Tasks.Task import TaskError

from utilities.DAQLogger import DAQLogClient
from utilities.DAQConfig import DAQConfig

__all__ = ['TaskManager']



class TaskManager:
    """
    Interface to separate TaskManager process
    """

    def __init__(self, settings, log_queue):
        self.Queue = Queue(20)  #process Queue  # 10 -> 20 5/18/2020 APS
        self.MessageQueue = Queue(2)
        self.logger = DAQLogClient(log_queue, "TASKMAN")
        
        tm_process = Process(target=TM_Process, args=(settings,self.Queue,self.MessageQueue, log_queue))
        tm_process.daemon=True

        # if os.name=='nt':
        #     self.logger.info("setting below-normal priority to TaskManager")
        #     psutil.Process(os.getpid()).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        tm_process.start()
        self.logger.info('Starting TaskManager on pid %d' % tm_process.pid)

    def Start(self):
        self.Queue.put('start')
        self.MessageQueue.get() #block until done

    def Stop(self):
        self.Queue.put('stop')
        self.MessageQueue.get() #block until done

    def Quit(self):
        self.Queue.put('quit')
        
        self.logger.info("Quitting Task Manager")
        
        self.MessageQueue.get() #block until done

        self.logger.info("Finished quitting Task Manager")


def TM_Process(settings,inQueue,outQueue, log_queue):

    # Lower the process priority
    psutil.Process(os.getpid()).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)

    TM = _TaskManager(settings, log_queue)

    while True:

        message = inQueue.get()     # Pull this second's timestamp from the GPS clock

        if message == 'start':
            TM.Start()
            outQueue.put('done')

        if message == 'stop':
            TM.Stop()
            outQueue.put('done')

        if message == 'quit':
            TM.Stop()
            outQueue.put('done')
            return





class _TaskManager:
    """
    This module is responsible for starting and controlling background processes
    such as automatic SFTP file transfers and data folder cleanup
    """

    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self, settings, log_queue):
        # Initialize data members
        self.running = False
        self.logger = None
        self.log_queue = log_queue
        self.thread = None

        self.tasks = []

##        self.logger = logging.getLogger('TaskManager')    #for thread
        #if separate process:
        #self.logger = get_logger()
        self.logger = DAQLogClient(self.log_queue, "TASKS")
        #formatter = logging.Formatter('TM: (%(levelname)s) %(message)s')
        #handler = logging.StreamHandler()
        #handler.setFormatter(formatter)
        #self.logger.addHandler(handler)
        #self.logger.setLevel(logging.INFO)

        # Parse the settings XML file
        #settings = parse(settings) #Settings already parsed
        self.settings = settings
        self.GenerateModules(settings)

    def GenerateModules(self,settings):
        #get a list of all Task entries
        task_settings_list = settings.GetSubTree("Task")

        tasknum = 0
        
        #iterate over the tasks and instantiate the modules
        for task_settings in task_settings_list:
        
            settings = DAQConfig(task_settings)
            
            module_name = str(task_settings.attributes['module'].value)
            
            self.logger.info("Instantiating module: %s" % module_name)
            
            #setup individual logger
            task_logger = DAQLogClient(self.log_queue,'T%s.%s' % (tasknum, module_name))
            
            try:
                task_module = __import__('Tasks',globals(),locals(),[module_name],-1)
                
                constructor = 'task_module.' + module_name + '.' + module_name + '(settings, task_logger, tasknum)'
                
                #construct the module and add it to the list of tasks
                self.tasks.append(eval(constructor))
                
            except Exception as e:
                self.logger.exception("Error while instantiating module \'%s\'" % module_name)
                
            tasknum += 1
            
        self.logger.info("Finished instantiating modules.")
        
    # =======
    # Methods
    # =======
    def Start(self):
        """
        Begins execution of the data acquisition in a thread.
        """
        #self.logger.info("Starting the VLF DAQ Engine.")
        # Launch the thread
        self.thread = Thread(target=self.MainLoop)
        self.thread.start()

    def Stop(self):
        """
        Terminates execution of the data acquisition.
        """
        
        if self.running:
            self.logger.debug("Stopping tasks.")
            
            for task in self.tasks:
                task.Stop()

            self.logger.debug("Stopping the Taskmanager thread.")
            
            # Shutdown the Engine properly
            if self.thread is not None:
                self.running = False            # Kill the thread
                self.thread.join()
                self.thread = None

##        exit()

    def Quit(self):
        self.Stop()

    #You have to create a new thread for the restart because you can't
    #.join() a currently running thread (deadlock)
    def SignalRestart(self, restart_args):
    
        self.logger.critical('Restart signal received.')
        
        self.restarting = True
        self.running = False
        RestartThread = Thread(target=self.Restart, args = restart_args)
        RestartThread.daemon=True
        RestartThread.start()


    def Restart(self, hardRestart = False, systemRestart = False, restartGPS=True):
        """
        Stops of the data acquisition, and re-creates/restarts modules in case of an error.
        I'm not sure about memory leaks, but restarting several times will probably lead to them;
        a hard restart (stopping the program and restarting using "python main.py --args"
        is probably a good thing to do after N soft restarts
        """
        self.restarts += 1
        self.logger.warning("Restart Thread Activated")

        if systemRestart:
            #in case of serious errors, execute a shell script to restart the entire system
            #This has to be platform-specific, for windows, linux, mac, etc
            pass

        # Stop the thread
        if self.thread is not None:
            self.isReady.set()
            self.thread.join()
            self.thread = None


        # Clear old modules
        for task in self.tasks:
            task.Stop()

        self.tasks=[]

        #Important Note: This doesn't actually work right now, it just stops everything in engine.py
        #I couldn't find a way to stop the main (CLI) thread from this one, so this is still WIP
        if hardRestart:
            #in case of certain classes of errors, quit the current python instance and launch another
            #from the shell
            #self.logger.critical("HARD RESTART")
            #subprocess.Popen("python main.py")
            if self.parent:
                self.parent.onecmd("quit")
                return

        settings = self.settings
        self.GenerateModules(settings)

        # Launch the thread
        self.thread = Thread(target=self.MainLoop)
        self.thread.start()


    # ==============
    # Helper Methods
    # ==============
    def MainLoop(self):
        self.running = True

        try:

            #start the tasks
            for task in self.tasks:
                task.Start()

            #wait until Stop() has been called
            while self.running:
                sleep(0.5)

            #stop the tasks
            for task in self.tasks:
                task.Stop()

        except Exception,inst:
            #(excType, excValue, excTb) = exc_info()
            #tb = traceback.extract_tb(excTb)[-1]
            #self.logger.error('EXCEPTION: %s'%str(excValue))
            #self.logger.error('\tFIle: %s'% tb[0])
            #self.logger.error('\tLine %s in function %s: %s'% (tb[1], tb[2], tb[3]))
            self.logger.exception("Exception encountered while running task.")
            
            #self.logger.critical('Restarting')
            self.SignalRestart(())

# =========
# Unit Test
# =========
if __name__ == "__main__":

    main_logger = DAQLogger(options)
    main_logger.start()
    
    logger = DAQLogClient(main_logger.log_queue, "MAIN")
    logger.debug("Main logger ready.")
    

    # Create the TaskManager object
    tm = TaskManager("DaqSettings.xml")
    try:
        tm.MainLoop()
    except KeyboardInterrupt:
        tm.Stop()
