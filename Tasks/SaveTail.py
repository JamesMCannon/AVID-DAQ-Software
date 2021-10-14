__all__ = ['SaveTail']

from Task import *


class SaveTail(Task):
    def __init__(self, config, logger, tasknum):    
        Task.__init__(self, config, logger, tasknum)

        self.taskname = 'T%d.SaveTail' % tasknum

        self.in_file = config.GetStrElemVal("in_file")
        self.out_file = config.GetStrElemVal("out_file")
        self.chars = config.GetIntElemVal("chars")

        self.interval = config.GetIntElemVal('Interval') #seconds

        self.logger.info("Initializing tail task")
        self.logger.info("in_file: %s"%self.in_file)
        self.logger.info("out_file: %s"%self.out_file)
        self.logger.info("Chars: %d"%self.chars)

    def DoTask(self):
        self.logger.info("Doing tail task")
        try:
            file_handle = open(self.in_file)

            file_handle.seek(0, 2) # Jump to end
            file_size = file_handle.tell() # get length in bytes
            lookback = min(file_size, self.chars) # how far to look back?

            file_handle.seek(file_size - lookback)
            dat = file_handle.read()
            file_handle.close()    

            # Write output to new file
            with open(self.out_file,'w') as file:
                file.write(dat)

        except:
            self.logger.exception('Failed to tail log file') 
            raise
                           