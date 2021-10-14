"""
SFTP module
"""


from ftplib import FTP
from Task import *

import paramiko
from paramiko import SSHException, AuthenticationException
paramiko.util.log_to_file('ftplog.log',level=logging.WARNING)

__all__ = ['SFTP']

try:
    import wx
    from VLFPanel import VLFPanel

    class GUIPanel(VLFPanel):
        def __init__(self, parent):
            VLFPanel.__init__(self, parent, "SFTP")
            self.widgets = {
                'Directory':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'Period':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[Seconds]'),
                'Hostname':wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),
                'Port':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'(sftp only)'),
                'Username':wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),
                'RSA_Key_file':wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),
##                'Password':(wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),'(if no RSA key file)'),
                'TargetDirectory':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
##                'ftp':(wx.Choice(self, wx.ID_ANY, size= self.DROP_BOOL_SIZE,choices = ['0','1']),'0: sftp, 1: ftp'),
##                'SftpTimeout':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[Seconds] (sftp only)'),
                'StartTime':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[HH:MM], System UTC'),
                'EndTime':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[HH:MM], System UTC'),
            }
            self.addWidgets()
except:
    print "WARNING: CAN'T IMPORT WX AND/OR VLFPanel"


class myFTP():
    """
    Wrapper for both ftp and sftp
    """
    def __init__(self, target_directory, use_date_folder, logger, host, port=22, do_ftp=False, timeout=10.0):
        """
        Default to sftp, unles ftp is True
        """
        self.target_directory = target_directory
        self.use_date_folder = use_date_folder
        self.do_ftp = do_ftp
        self.timeout = timeout  #for sftp connections only
        self.ftp = None
        self.sftp = None
        self.t = None
        self.connected = False
        
        self.logger = logger
        
        if self.do_ftp:
            self.logger.debug("Setting up FTP")
            try:
                self.ftp = FTP(host=host)
            except:
                self.logger.error("Exception setting up FTP")
                raise
        else:
            self.logger.debug("Setting up Paramiko")
            try:
                self.t = paramiko.Transport((host, port))
            except:
                self.logger.error("Exception setting up paramiko")
                raise
                

    def connect(self,user,passwd=None,pkey_filename='.'):
        if self.do_ftp:
            self.logger.debug("FTP login")
            self.ftp.login(user=user,passwd=passwd)
        else:
            try:
                if os.path.isfile(pkey_filename):
                    self.logger.debug("SFTP login using key")
                    pkey = paramiko.RSAKey.from_private_key_file(pkey_filename)
                    self.t.connect(username=user, pkey=pkey)
                else:
                    self.logger.debug("SFTP login using pwd")
                    self.t.connect(username=user, password=passwd)
            except AuthenticationException:
                #self.logger.error("Failed to authenticate to server.") #Raise and catch in above module
                raise
            except:
                self.logger.warning("Exception logging in to server.")
                raise
                
            self.connected = True
            
            self.sftp = paramiko.SFTPClient.from_transport(self.t)
            channel = self.sftp.get_channel()
            channel.settimeout(self.timeout)

        #every path is w.r.t. the target_directory
        self.testAndMkDir(self.target_directory)
        self.root_dir = self.pwd()

    def chdir(self,directory):
        if self.connected:
            if self.do_ftp:
                self.ftp.cwd(directory)
            else:
                self.sftp.chdir(directory)

    def mkdir(self,directory):
        if self.connected:
            if self.do_ftp:
                self.ftp.mkd(directory)
            else:
                self.sftp.mkdir(directory)

    def pwd(self):
        if self.connected:
            if self.do_ftp:
                return self.ftp.pwd()
            else:
                return self.sftp.getcwd()

    def put(self,localpath,filename):
        if self.connected:
            #print 'writing file %s' % filename
            remotepath = self.getDateFolder(filename) + filename
            if self.do_ftp:
                f = open(localpath,'rb')
                self.ftp.storbinary('STOR %s' % remotepath,f)
                f.close()
            else:
                self.sftp.put(localpath, remotepath)

    def get(self,remotepath,localpath):
        if self.connected:
            if self.do_ftp:
                raise 'Get unsupported with ftp'
            else:
                self.sftp.get(remotepath,localpath)

    def listdir(self,request_dir):
        if self.connected:
            if self.do_ftp:
                raise 'listdir unsupported with ftp'
            else:
                return self.sftp.listdir(request_dir)

    def remove(self,remotepath):
        if self.connected:
            if self.do_ftp:
                raise 'remove unsupported with ftp'
            else:
                self.sftp.remove(remotepath)

    def close(self):
        if self.connected:
            if self.do_ftp:
                if self.ftp is not None:
                    self.ftp.quit()
            else:
                if self.t is not None:
                    self.t.close()


    def getDateFolder(self,filename):
        """
        if self.use_date_folder is True, try to save to a date folder using
        target_directory/yyyy/mm/dd

        Broadband files should have naming format: <anything>yymmddhhmmss_XXX.<anything>
        Narrowband files should have the naming format: <anything>yymmddhhmmssYYY_XXXZ.<anything>

        """

        if self.connected:
        
            if not self.use_date_folder:
                return ''

            r = re.compile('.+([0-9]{12,12})[0-9a-zA-Z]{0,5}_[0-9a-zA-Z]{3,5}\.[matMATjpegJPEGpnPN]{3,4}')
            m = r.match(filename)

            if m is None:
                return '' #does not conform to correct format

            year = '20' + m.group(1)[:2]
            month_day = m.group(1)[2:4] + '_' + m.group(1)[4:6]

            filesep = '/'   #should work with Windows and Unix
            datefolder = year + filesep + month_day
            self.testAndMkDir(datefolder)
            self.chdir(self.root_dir)
            return datefolder + filesep



    def testAndMkDir(self,dirname):
        """
        Test if dirname exists; make it if it does not
        Return True if exists or successfully made
        Return False if directory dne may not be made
        Navigates to last directory
        """
        dir_list = myFTP.get_dir_list(dirname,[])

        for adir in dir_list:
            try:
                self.chdir(adir)
            except Exception,err:
                try:
                    self.mkdir(adir)
                    self.chdir(adir)
                except Exception, err:
                    return False
        return True


    @staticmethod
    def get_dir_list(dirname,dirlist = []):
        """
        Return directory list in order
        """
        (head,tail) = os.path.split(dirname)
        dirlist.append(tail)
        if len(head)==0:
            dirlist.reverse()
            return dirlist
        else:
            return myFTP.get_dir_list(head,dirlist)


class SFTP(Task):

###############################################################################

    def __init__(self, config, logger, tasknum):

        Task.__init__(self, config, logger, tasknum)

        self.randInterval = 3

        self.taskname = 'T%d.SFTP' % tasknum

        self.directory = config.GetStrElemVal('Directory')
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)

        self.interval = config.GetIntElemVal('Period',3600)
        self.hostname = config.GetStrElemVal('Hostname')
        self.port = config.GetIntElemVal('Port',22)
        self.username = config.GetStrElemVal('Username')
        self.password = config.GetStrElemVal('Password','.')
        self.pkey = config.GetStrElemVal('RSA_Key_file','')

        self.target_directory = config.GetStrElemVal('TargetDirectory')
        self.ftp = config.GetIntElemVal('ftp',0)>0
        self.use_date_folder = config.GetIntElemVal("UseDateFolder",1)>0
        self.timeout = config.GetDblElemVal("SftpTimeout",10.0)

        self.exclude_list = ['.mau']

###############################################################################

    def DoTask(self):
        self.logger.debug('Scanning for new files...')

        #get a list of all files in the local directory
        file_list = os.listdir(self.directory)

        #we'll assume the local directory contains only files, so filter out all directories from the list
        #this simplifies things by removing the need to do recursive directory copies
        file_list = filter(lambda x: not os.path.isdir(os.path.join(self.directory, x)), file_list)

        #strip out certain extensions
        for extension in self.exclude_list:
            file_list = filter(lambda x: not x.endswith(extension), file_list)


        if len(file_list)==0:
            self.logger.debug('No new files')
            return

        #open the SFTP connection
        t = None
        try:
            self.logger.info('Opening (S)FTP connection to %s'%self.hostname)
            
            s_ftp = myFTP(self.target_directory, self.use_date_folder, self.logger, host=self.hostname,port=self.port,do_ftp=self.ftp,timeout=self.timeout)
            
            s_ftp.connect(self.username, self.password, pkey_filename=self.pkey)

            #transfer and then delete each file in the local FTP directory
            for filename in file_list:
                if not self.running:
                    break #don't wait for everything to copy when software called to exit
                file_path = os.path.join(self.directory, filename)
                self.logger.info('Sending %s' % file_path)
                s_ftp.put(file_path, filename)
                os.remove(file_path)

            #close the SSH transport
            self.logger.info('Closing (S)FTP connection')
            s_ftp.close()
            
        except AuthenticationException:
            self.logger.warning("Authentication exception trying to connect to %s." % self.hostname)
            return
        except SSHException:
            self.logger.warning('SSH Exception connecting to server: %s:%s' % (self.hostname, self.port))
            return
        except Exception:
            self.logger.exception("Some exception happened while SFTPing data.")
            return
            
            try:
                s_ftp.close()
            except Exception:
                self.logger.error("Exception closing SFTP.")
                pass





###############################################################################

#---------
#Unit Test
#---------
if __name__ == '__main__':

    from xml.dom.minidom import parseString
    import numpy
    from datetime import datetime, timedelta
    import time
    import os


    files = [open('../FTP/afile.txt','w'),open('../FTP/foo','w'),
             open('../FTP/SU091011221358_001.mat','w'),
             open('../FTP/SU091011221358ABC_001A.mat','w')]
    for f in files:
        f.write('%s: hello, world %s' % (f.name,str(datetime.now())))
        f.close()


    settings_sftp = """
        <Task module = "SFTP">
            <Directory>../FTP</Directory>
            <Period>10</Period>
            <Hostname>nova.stanford.edu</Hostname>
            <Port>22</Port>
            <Username>vlf</Username>
            <Password>simsek7!</Password>
            <UseDateFolder>0</UseDateFolder>
            <TargetDirectory>Ryan/ftp_test/Stanford</TargetDirectory>
            <SftpTimeout>10.0</SftpTimeout>
        </Task>
        """


    settings_ftp = """
        <Task module = "SFTP">
            <Directory>../FTP</Directory>
            <Period>10</Period>
            <Hostname>nova.stanford.edu</Hostname>
            <Username>vlf</Username>
            <ftp>1</ftp>
            <Password>simsek7</Password>
            <UseDateFolder>1</UseDateFolder>
            <TargetDirectory>Ryan/ftp_test/Stanford</TargetDirectory>
        </Task>
        """

    settings_hail = """
        <Task module = "SFTP">
            <Directory>../FTP</Directory>
            <Period>10</Period>
            <Hostname>hail.stanford.edu</Hostname>
            <Username>hail</Username>
            <ftp>1</ftp>
            <Password>ltwpcpbfc</Password>
            <UseDateFolder>1</UseDateFolder>
            <TargetDirectory>VLFData/Test</TargetDirectory>
        </Task>
        """

    settings_wrong = """
        <Task module = "SFTP">
            <Directory>../FTP</Directory>
            <Period>10</Period>
            <Hostname>nova.stanford.edu</Hostname>
            <Username>vlf</Username>
            <ftp>0</ftp>
            <Password>simsek7</Password>
            <UseDateFolder>1</UseDateFolder>
            <TargetDirectory>Ryan/ftp_test/Stanford</TargetDirectory>
        </Task>
        """

    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)

    # define a Handler which writes DEBUG messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter('%(name)-2s: %(levelname)s %(message)-60s'))
    logger.addHandler(console)

    sftp = SFTP(parseString(settings_sftp),logger)

    sftp.Start()
    sftp.Stop()
