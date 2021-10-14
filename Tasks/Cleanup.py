"""
Removes Files after a given number of days
"""


__all__ = ['Cleanup']

from Task import *

try:
    import wx
    from VLFPanel import VLFPanel

    class GUIPanel(VLFPanel):
        def __init__(self, parent):
            VLFPanel.__init__(self, parent, "Cleanup")
            self.widgets = {
                'Directory':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'DataLifetime':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[Days]'),
                'Interval':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[Seconds]'),
                'StartTime':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[HH:MM], System UTC'),
                'EndTime':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[HH:MM], System UTC'),
            }
            self.addWidgets()

except:
    print "WARNING: CAN'T IMPORT WX AND/OR VLFPanel"

class Cleanup(Task):

###############################################################################

    def __init__(self, config, logger, tasknum):

        Task.__init__(self,config,logger, tasknum)

        self.taskname = 'T%d.Cleanup' % tasknum

        #parse the xml file
        self.directory = config.GetStrElemVal('Directory')
        
        if not os.path.isdir(self.directory):
            #os.makedirs(self.directory)
            self.logger.warning("Directory does not exist: %s" % self.directory)

        self.data_lifetime = config.GetDblElemVal('DataLifetime')
        
        # if self.data_lifetime < 1:
        #     self.logger.error("Data lifetime invalid (%d). Set to default %d" % (self.data_lifetime, 5))
        #     self.data_lifetime = 5      
        
        self.interval = config.GetIntElemVal('Interval')
        
        if self.interval < 1:
            self.logger.error("Cleanup interval invalid (%d). Set to default %d" % (self.interval, 3600))
            self.interval = 3600

        self.exclude_list = ['.mau']

###############################################################################

    def DoTask(self):

        #get a list of all files in the data directory
        file_list = os.listdir(self.directory)

        #strip out all directories from the list
        file_list = filter(lambda x: not os.path.isdir(os.path.join(self.directory, x)), file_list)

        #strip out certain extensions
        for extension in self.exclude_list:
            file_list = filter(lambda x: not x.endswith(extension), file_list)

        #strip out all files from the list that are less than self.data_lifetime days old
        file_list = filter(self.FileLifetimeFilter,file_list)

        #delete the old files
        for file in file_list:
            if not self.running:
                break #don't wait for everything to delete when software called to exit
                
            file_path = os.path.join(self.directory, file)

            self.logger.debug('%s is greater than %d days old. Deleting...'%(file_path, self.data_lifetime))
            
            try:
                os.remove(file_path)
            except:
                self.logger.exception("Error while cleaning up file: %s" % file_path)
                
                
###############################################################################

    def FileLifetimeFilter(self, file_name):
        #This function returns True if file_name is older than self.data_lifetime
        #and False otherwise

        #get the files modification timestamp
        file_mtime = datetime.fromtimestamp(os.path.getmtime(os.path.join(self.directory, file_name)))

        #current timestamp
        curr_time = datetime.now()

        dt = curr_time - file_mtime

        return dt.days*86400 + dt.seconds >= self.data_lifetime*86400
        # return dt.days*86400 + dt.seconds >= self.data_lifetime*3600  # data_lifetime in hours - 5.2018


###############################################################################

