"""
Copy files to a directory
"""
import shutil
import ctypes
import platform

__all__ = ['CopyFiles']

from Task import *

try:

    import wx
    from VLFPanel import VLFPanel


    class GUIPanel(VLFPanel):
        def __init__(self, parent):
            VLFPanel.__init__(self, parent, "CopyFiles")
            self.widgets = {
                'WriteDirectory':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'Interval':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[Seconds]'),
                'Delete':wx.Choice(self, wx.ID_ANY, size= self.DROP_BOOL_SIZE,choices = ['0','1']),
                'Filename':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'Filename1':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'Filename2':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'Filename3':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'Filename4':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'Swap':wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),
                'Directory':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'Directory1':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'Directory2':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'StartTime':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[HH:MM], System UTC'),
                'EndTime':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[HH:MM], System UTC'),
            }
            self.addWidgets()
except:
    print "WARNING: CAN'T IMPORT WX AND/OR VLFPanel"

class CopyFiles(Task):

###############################################################################

    def __init__(self, config, logger, tasknum):
    
        Task.__init__(self, config, logger, tasknum)

        #broadband, jpeg, and most narrowband files:
        self.datetime_re = re.compile('.*(\d{2})(\d{2})(\d{2})\d{6}[A-Za-z]{0,3}_\d{3}[A-Fa-f]{0,1}\..+')

        self.taskname = 'T%d.CopyFiles' % tasknum

        self.exclude_list = ['.mau']

        #parse the xml file
        # self.writeDirectory = config.GetStrElemVal('WriteDirectory')
        # A list of possible write directories:
        self.writeDirectories = []
        no_dir_default = 'X3@X-+#@!3blablabla'
        for ii in ['','0','1','2','3','4','5','6','7','8','9']:
            writeDirectory = config.GetStrElemVal('WriteDirectory%s'%ii, no_dir_default)
            if writeDirectory != no_dir_default:
                if not os.path.isdir(writeDirectory):
                    try:
                        os.makedirs(writeDirectory)
                    except:
                        self.logger.error('Cannot create folder %s for copying--drive may be missing or full' % writeDirectory)
                self.writeDirectories.append(writeDirectory)
        self.logger.info('Available write directories:')
        for wd in self.writeDirectories:
            self.logger.info("writeDirectory: %s"%wd)
        self.interval = config.GetIntElemVal('Interval') #seconds
        self.delete_after_copy = config.GetIntElemVal("Delete",0)>0

        self.filenames = []
        no_file_default = 'X3@X-+#@!3blablabla'
        for ii in ['','0','1','2','3','4','5','6','7','8','9']:
            read_file = config.GetStrElemVal("Filename%s" % ii,no_file_default)
            if read_file != no_file_default:
                self.filenames.append(read_file)


        self.directories = []
        no_dir_default = 'X3@X-+#@!3blablabla'
        for ii in ['','0','1','2','3','4','5','6','7','8','9']:
            read_dir = config.GetStrElemVal("Directory%s" % ii,no_dir_default)
            if read_dir != no_dir_default:
                if os.path.isdir(read_dir):
                    self.directories.append(read_dir)
                else:
                    print 'Directory %s does not exist; skipping' % read_dir



###############################################################################

    def DoTask(self):
        self.logger.info("Doing copy task")
        for writeDirectory in filter(lambda x: os.path.exists(os.path.splitdrive(x)[0]),self.writeDirectories):
            self.logger.info("Checking %s"%writeDirectory)
            # Check disk space at target directory:
            free_bytes = self.checkDisk(writeDirectory)
            reqd_bytes = 5*1024*2024*1024  # 5 GB (arbitrary stop point. Could calculate a bit more intelligently)
            # self.logger.info("free bytes = %d, reqd_bytes = %d"%(free_bytes, reqd_bytes))
            if (free_bytes > reqd_bytes):
                #check write directory:
                if not os.path.isdir(writeDirectory):
                    try:
                        os.makedirs(writeDirectory)
                    except:
                        self.logger.error('Cannot create write directory %s' % writeDirectory)
                        return

                self.CopyFiles(self.filenames, writeDirectory)

                for directory in self.directories:
                    if not self.running:
                        break   #don't wait for everything to copy when software called to exit

                    if not os.path.isdir(directory):
                        continue

                    #get a list of all files in the data directory
                    file_list = os.listdir(directory)

                    #prepend directory
                    file_list = [os.path.join(directory,fname) for fname in file_list]

                    #strip out all directories from the list
                    file_list = filter(lambda x: not os.path.isdir(x), file_list)

                    #strip out certain extensions
                    for extension in self.exclude_list:
                        file_list = filter(lambda x: not x.endswith(extension), file_list)

                    try:
                        self.CopyFiles(file_list, writeDirectory)
                        self.logger.info("Finished copying files.")
                    except:
                        # Would be nice to differentiate between different file errors (ie disc full, etc) and handle accordingly
                        continue
                break # Success -- don't copy to any other drives


    def CopyFiles(self,file_list, writeDirectory):
        # Passing the write directory as a parameter, since it may change in doTask based on disk availability
        for filename in file_list:
            if not self.running:
                break   #don't wait for everything to copy when software called to exit
            try:
                if os.path.isfile(filename):
                    (head,tail) = os.path.split(filename)

                    #check for regular expression: date string in file
                    """
                    m = self.datetime_re.match(tail)
                    if m is not None:
                        new_dir = os.path.join(self.writeDirectory,"20%s" % m.group(1),"%s" % m.group(2),"%s" % m.group(3))
                        if not os.path.isdir(new_dir):
                            os.makedirs(new_dir)
                        new_filename = os.path.join(new_dir,tail)
                    else:
                        new_filename = os.path.join(self.writeDirectory,tail)
                    """
                    ### changed 4/21/13 by JCC to make copy destination directory flat
                    new_filename = os.path.join(writeDirectory,tail)

                    shutil.copyfile(filename,new_filename)
                    self.logger.debug("Copied %s to %s." % (filename,new_filename))
                    
                    if self.delete_after_copy:
                        os.remove(filename)
                        self.logger.debug("Removed %s." % filename) 
                        
            except Exception:
                self.logger.exception('Filename: %s' % filename)
                #break   #usually write drive dne; exit out of loop
                raise

    
    def checkDisk(self, fname):
    
        dname = os.path.dirname(fname)
        """ 
        Return folder/drive free space (in bytes)
        """
        if os.name == 'nt':
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(dname), None, None, ctypes.pointer(free_bytes))
            return free_bytes.value
        else:
              
            s = os.statvfs(dname)
            
            # f_bsize = system block size
            # f_frsize = fundamental system block size (some recipies uses this)
            # f_bavail = blocks available
            
            return s.f_bsize * s.f_bavail


###############################################################################

if __name__ == '__main__':
    from xml.dom.minidom import parseString
    import time as timemod
    import logging
    logger = logging.getLogger('')

    f = open('hi.txt','w')
    f.close()

    f = open('hi1.txt','w')
    f.write('phase 1')
    f.close()

    timemod.sleep(2)

    # Create the Motorola GPS clock object
    settings = """\
    <Task module="CopyFiles">
        <WriteDirectory>hi</WriteDirectory>
        <Interval>5</Interval>
        <Filename>hi.txt</Filename>
        <Filename1>hi1.txt</Filename1>
        <Filename2>hi2.txt</Filename2>
        <Directory>dir1</Directory>
        <Directory1>dir2</Directory1>


        <Delete>1</Delete>
    </Task>
    """
    copy = CopyFiles(parseString(settings),logger)
    copy.Start()
    timemod.sleep(8)
    f = open('hi1.txt','w')
    f.write('phase 2')
    f.close()
    timemod.sleep(6)
    copy.Stop()

