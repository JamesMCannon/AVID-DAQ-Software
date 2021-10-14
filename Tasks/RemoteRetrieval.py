"""
remote retrieval module
"""

#from xml.dom.minidom import parse
import xml.dom.minidom

from Task import *
from utilities.loadMATdata import *
from SFTP import myFTP
from paramiko import SSHException, AuthenticationException

CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#print CURRENT_DIR
sys.path.insert(0, CURRENT_DIR)

#from scipy.io.numpyio import fwrite, fread #deprecated JCC 04/02/12
from numpyio.numpyIO import fread, fwrite
__all__ = ['RemoteRetrieval']

try:
    import wx
    from VLFPanel import VLFPanel
    class GUIPanel(VLFPanel):
        def __init__(self, parent):
            VLFPanel.__init__(self, parent, "RemoteRetrieval")
            self.widgets = {
                'DataDirectory':(wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),'Local'),
                'Hostname':wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),
                'Port':wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),
                'Username':wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),
                'RSA_Key_file':wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),
    ##                'Password':(wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),'(if no RSA key file)'),
                'RemoteRequestDirectory':(wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),'Query xml files'),
                'LocalSaveDirectory':(wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),'Requested mat files'),
                'Period':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[Seconds]'),
            }
            self.addWidgets()

except:
    print "WARNING: CAN'T IMPORT WX AND/OR VLFPanel"


class RemoteRetrieval(Task):

    def __init__(self, config, logger, tasknum):

        Task.__init__(self, config, logger, tasknum)

        self.randInterval = 3

        self.taskname = 'T%d.RemoteRetrieval' % tasknum

        self.init = False

        self.tmp_request_folder = 'tmp_requests.%d' % tasknum

        self.data_directory = config.GetStrElemVal('DataDirectory')
        self.hostname = config.GetStrElemVal('Hostname')
        self.port = config.GetIntElemVal('Port',22)
        self.username = config.GetStrElemVal('Username','.')
        self.pkey = config.GetStrElemVal('RSA_Key_file','.')
        self.passwd = config.GetStrElemVal('Password','.')
        self.request_dir = config.GetStrElemVal('RemoteRequestDirectory')
        self.save_dir = config.GetStrElemVal('LocalSaveDirectory')

        self.interval = config.GetIntElemVal('Period',3600)

        try:
            if not os.path.isdir(self.tmp_request_folder):
                os.makedirs(self.tmp_request_folder)

            if not os.path.isdir(self.save_dir):
                os.makedirs(self.save_dir)
        except:
            self.logger.exception("Error while making directories.")
            return
        
        if not os.path.isdir(self.data_directory):
            self.logger.error("Data directory does not exist: %s" % self.data_directory)


    def DoTask(self):


        if self.hostname.lower() != 'local':    #if Hostname is 'local', assume xml params pushed
            try:
                sftp = myFTP(self.request_dir, None , self.logger, host=self.hostname,port=self.port,do_ftp=False,timeout=10.0)
                sftp.connect(self.username, self.passwd, pkey_filename=self.pkey)

            except AuthenticationException:
                #self.logger.exception('Authentication exception connecting to server: %s:%s' % (self.hostname, self.port))
                self.logger.warning('Authentication exception connecting to server: %s:%s' % (self.hostname, self.port))
                return
            except SSHException:
                #self.logger.exception('SSH Exception connecting to server: %s:%s' % (self.hostname, self.port))
                # Should pull out the exception message somehow
                self.logger.warning('SSH Exception connecting to server: %s:%s' % (self.hostname, self.port))
                return
            except Exception:
                self.logger.exception('Unknown exception connecting to server: %s:%s' % (self.hostname, self.port))
                return

            #get the files in the remote requests directory
            try:
                request_files = sftp.listdir('.')
            except:
                self.logger.exception('Unknown exception listing directory.')
                return
                
            try:
                for r in request_files:
                
                    if not self.running:
                        break #don't wait for everything to delete when software called to exit
                
                    sftp.get(r,os.path.join(self.tmp_request_folder,r))
                    sftp.remove(r)
            except:
                self.logger.exception('Unknown exception getting file: %s' % (r))
                return

            #close the connection
            self.logger.debug('Closing SFTP connection')
            sftp.close()

            
        #open the request files and search through data
        local_request_files = os.listdir(self.tmp_request_folder)
        local_request_files = filter(lambda x: x.endswith('.xml'), local_request_files)

        for file in local_request_files:
        
            if not self.running:
                break #don't wait for everything to delete when software called to exit
        
            self.logger.debug('Processing request %s' % file)
            request_file = os.path.join(self.tmp_request_folder,file)

            try:
                req = xml.dom.minidom.parse(request_file)
            except:
                self.logger.exception('Bad request file: %s' % file)
                return
                
            try:
                """
                year = self._GetIntElemVal(req, 'Year')
                month = self._GetIntElemVal(req, 'Month')
                day = self._GetIntElemVal(req, 'Day')
                hour = self._GetIntElemVal(req, 'Hour')
                minute = self._GetIntElemVal(req, 'Minute')
                second = self._GetDblElemVal(req, 'Second')
                duration = self._GetDblElemVal(req, 'Duration')
                channel = self._GetIntElemVal(req, 'Channel')
                station_id = self._GetStrElemVal(req,'Station_ID')
                """
                
                year = int(req.getElementsByTagName('Year')[0].firstChild.data)
                month = int(req.getElementsByTagName('Month')[0].firstChild.data)
                day = int(req.getElementsByTagName('Day')[0].firstChild.data)
                hour = int(req.getElementsByTagName('Hour')[0].firstChild.data)
                minute = int(req.getElementsByTagName('Minute')[0].firstChild.data)
                second = float(req.getElementsByTagName('Second')[0].firstChild.data)
                duration = float(req.getElementsByTagName('Duration')[0].firstChild.data)
                channel = int(req.getElementsByTagName('Channel')[0].firstChild.data)
                station_id = str(req.getElementsByTagName('Station_ID')[0].firstChild.data)
                                
            except:
                self.logger.exception('Error in request file: %s' % file)
                return            
            else:
                start_time = datetime(year=year,
                                      month=month,
                                      day=day,
                                      hour=hour,
                                      minute=minute,
                                      second=int(second),
                                      microsecond = int((second-int(second))*1e6))

                end_time = start_time + timedelta(seconds=int(duration),microseconds=int((duration-int(duration))*1e6))
                time_now = datetime.utcnow()
                
                # skip current XML file if start or end times in the future
                if (start_time < time_now) and (end_time < time_now):
                    filename = self.parse_data(station_id,channel,start_time,end_time)

                    if filename is not None:
                        new_filename = list(filename)
                        new_filename[-1] = 't'
                        os.rename(filename,"".join(new_filename))
                        
                        # All finished
                        try:
                            os.remove(request_file)
                            self.logger.info('Finished processinge "%s"' % request_file) 
                        except:
                            self.logger.warning('Could not remove "%s"' % request_file)
                            return
                else:
                    self.logger.info('"Come with me if you want to live..." "%s" starts or ends in the future.' % file)
                    
###############################################################################
    def parse_data(self, station_id, channel_num, start_time, end_time):

        #get the list of all files with data in the time window
        data_file_list = self.get_data_file_list(self.data_directory, channel_num, start_time, end_time)

        if len(data_file_list)>0:
            #concatenate all of the matlab file data into one numpy array
            data, start_time =  self.data_concatonate(data_file_list, start_time, end_time)
        else:
            return None
            
        #matlab filename
##        filename = os.path.join(self.tmp_data_folder,'%s_%s_%03d_%03d.mat'% \
##                                (station_id,start_time.strftime('%y%m%d_%H%M%S'),\
##                                 int(start_time.microsecond/1e3),channel_num))
        #RKS--2010-1-26
        filename = os.path.join(self.save_dir,'%s%s_%03d.mau'% \
                                (station_id,start_time.strftime('%y%m%d%H%M%S'),\
                                 channel_num))

        #if no data exists in the window, return
        if (len(data_file_list)==0) or data is None:
            #create null file:
            fid = open(filename,'w')
            fid.close()
            return filename

        self.WriteVector(filename, 'start_year',         start_time.year,                                'int32')
        self.WriteVector(filename, 'start_month',        start_time.month,                               'int32')
        self.WriteVector(filename, 'start_day',          start_time.day,                                 'int32')
        self.WriteVector(filename, 'start_hour',         start_time.hour,                                'int32')
        self.WriteVector(filename, 'start_minute',       start_time.minute,                              'int32')
        self.WriteVector(filename, 'start_second',       start_time.second + start_time.microsecond/1e6, 'float64')

        header = data_file_list[0][1]
        ld = data_file_list[0][2]
        for field in header:
            if field not in ['start_year','start_month','start_day','start_hour','start_minute','start_second']:
                if header[field] is not None:
##                    print field, header[field], type(header[field])
                    self.WriteVector(filename,field,header[field],MOPT=ld.get_var_MOPT(field))

        self.WriteData(filename, data)

        return filename



    #####################################################################################################
    #This function returns a list of data files which have data that falls between start_time and end_time
    def get_data_file_list(self, data_dir, channel_num, start_time, end_time):

        try:
            #get a list of all files in the data directory
            directory_list = os.listdir(data_dir)
        except:
            self.logger.exception('Error accessing data directory: %s' % data_dir)
            return []

        #filter out all non-Matlab files
        directory_list = filter(lambda x: x.endswith('%03d.mat' % channel_num), directory_list)

        #iterate through the list and find the ones which lie between start_time and end_time
        data_file_list = []

        for file in directory_list:
            full_filename = os.path.join(data_dir,file)
            try:
                ld = loadMATdata(full_filename)
                varsize = ld.get_var_size('data') #ensure ability to read
                header = ld.loadAllData(exclude_list = ['data'])
                fs = header['Fs']       #ensure ability to read
            except: #Cleanup may have deleted
                self.logger.error('Looks like %s was deleted' % full_filename)
                continue
            else:
                #build up datetime object for the file's start time
                start_year = header['start_year']
                start_month = header['start_month']
                start_day = header['start_day']
                start_hour = header['start_hour']
                start_minute = header['start_minute']
                start_second = header['start_second']

                file_start_time = datetime(year=int(start_year),
                                           month=int(start_month),
                                           day=int(start_day),
                                           hour=int(start_hour),
                                           minute=int(start_minute),
                                           second=int(start_second),
                                           microsecond=int((start_second-int(start_second))*1e6))

                #calculate the file's end time based on the data vector lenght and the sample rate
                file_end_time = file_start_time + timedelta(seconds=(int(ld.get_var_size('data')/header['Fs'])))

                if (start_time >= file_start_time and start_time <= file_end_time) or (end_time >= file_start_time and end_time <= file_end_time):
                    data_file_list.append([file_start_time,header,ld,full_filename])

        data_file_list.sort(lambda a,b: cmp(a[0],b[0])) #chronological order

        return data_file_list

    #####################################################################################################
    #takes a list of matlab data files and concatonates them into one long numpy array
    def data_concatonate(self, data_file_list, start_time, end_time):
        """
        Assumes no break between files (no error checking)
        """

        data = None

        for data_file in data_file_list:
            file_start_time = data_file[0]
            fs = data_file[1]['Fs']
            file_size = data_file[2].get_var_size('data')
##            print cmp(start_time,file_start_time), start_time, file_start_time, (start_time - file_start_time).seconds
            if cmp(start_time,file_start_time)<0:
                start_index = 0
                if data is None:    #no previous segment
                    start_time = file_start_time
            else:
                start_index = int(((start_time - file_start_time).seconds + (start_time - file_start_time).microseconds/1e6)*fs)

            end_index = int(((end_time - file_start_time).seconds + (end_time - file_start_time).microseconds/1e6)*fs+.1)
            if end_index > file_size:
                end_index = file_size

            try:
                if data is None:
    ##                print start_index, end_index
                    data = data_file[2].loadData('data',end_index-start_index,start_index)['data']
                else:
                    data=np.concatenate((data, data_file[2].loadData('data',end_index-start_index,start_index)['data']))
            except:
                self.logger.error('Could not load data from %s' % data_file[3])
        return data, start_time


    #####################################################################################################
    #The following two functions are borrowed from the Python VLFDAQ code in MatFileWriter.py
    def WriteVector(self, filename, name, data, type=None, text=False,MOPT=None):


        if MOPT is not None:
            ld = loadMATdata()
            packtype,bytes = ld.get_unpack_type_format(MOPT)
        else:
            MOPToffset = 0
            MOPT = MOPToffset + types[type][0]
            packtype = types[type][1]

        if MOPT == 50:
            data_convert = lambda x: ord(x)
        else:
            data_convert = lambda x: x

        f = open(filename, 'a+b')

        if text: MOPT += 1
        f.write(pack('l', MOPT))							# MOPT
        try:	
            f.write(pack('l', len(data)))				# Number of rows
        except:	
            f.write(pack('l', 1))
        f.write(pack('l', 1))								# Number of columns
        f.write(pack('l', 0))								# Imaginary, should be 0
        f.write(pack('l', len(name)+1))						# Length of name+1
        f.write(pack("%is" % len(name), name) + chr(0))		# Entry name ending with a \0 character
        try:    
            lenData = len(data)
        except: 
            lenData = 1
            
        if lenData > 1:
            for i in range(lenData):
                f.write(pack(packtype, data_convert(data[i])))
        else:
            f.write(pack(packtype, data_convert(data)))

        f.close()

    #####################################################################################################
    def WriteData(self, filename, data):    #NOTE: only int16 compatible!!!
        MOPToffset = 0
        f = open(filename, 'a+b')
        name = "data"										# Name of the matfile entry
        f.write(pack('<l', 30+MOPToffset))					# MOPT
        f.write(pack('<l', len(data)))						# Number of rows
        f.write(pack('<l', 1))								# Number of columns
        f.write(pack('<l', 0))								# Imaginary, should be 0
        f.write(pack('<l', len("data")+1))					# Length of name+1
        f.write(pack("%is" % len("data"), "data") + chr(0))	# Entry name ending with a \0 character
        fwrite(f, data.size, data) 							#write the data vector to disk
        f.close()

    ####################################################################################################
    

##########
#Unit Test
##########

if __name__ == '__main__':

    from xml.dom.minidom import parseString

    settings = """
        <Task module = "RemoteRetrieval">
            <DataDirectory>../Data</DataDirectory>

            <Hostname>vlf-alexandria.stanford.edu</Hostname>
            <Port>22</Port>
            <Username>vlf-sftp</Username>
            <Password>FamswttF!</Password>
            <RemoteRequestDirectory>data_requests/CH</RemoteRequestDirectory>
            <LocalSaveDirectory>tmp_save</LocalSaveDirectory>

            <Period>10</Period>

        </Task>
        """

    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter('%(name)-2s: %(levelname)s %(message)-60s'))
    logger.addHandler(console)

    remote_retrieval = RemoteRetrieval(parseString(settings),logger)

    remote_retrieval.Start()
    time.sleep(25)
    remote_retrieval.Stop()
