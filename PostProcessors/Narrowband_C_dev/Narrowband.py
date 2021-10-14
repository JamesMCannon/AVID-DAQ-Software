"""
Demodulates NB channels to track the amplitude and phase
"""

from datetime import datetime, timedelta
import os.path
import os
from time import sleep, clock, time
if os.name != 'nt':
    clock=time
from shutil import copyfile
import sys
#import scipy.io as sio
from xml.dom.minidom import parseString
from ConfigParser import ConfigParser

#Using either threading or processing module:
use_processing = True

if(use_processing):
    from multiprocessing import Queue, Process
else:
    from Queue import Queue
    from threading import Thread as Process


from Queue import Full, Empty
import numpy as np
import nbmodule as nb
import MatFileWriter as matf

__all__ = ['Narrowband']

try:
    import wx
    from VLFPanel import VLFPanel

    from main import __ver__

    class GUIPanel(VLFPanel):
        def __init__(self, parent):
            VLFPanel.__init__(self, parent, "Narrowband")
            self.widgets = {
                'adc_channel_number':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'0-999'),
                'DirectoryRoot':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'DirectoryRoot1':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'DirectoryRoot2':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'Duration':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[Seconds]'),
                'do_low_res':(wx.Choice(self, wx.ID_ANY, size= self.DROP_BOOL_SIZE,choices = ['0','1']),''),
                'do_sph_chan':(wx.Choice(self, wx.ID_ANY, size= self.DROP_BOOL_SIZE,choices = ['0','1']),''),
                'call_sign_file':(wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),'conf file (./nb.conf)'),
                'call_sign':(wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),"List of call signs (use ',')"),
                'filter_taps':(wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),'filter tap file (./filter_taps.txt)'),
##                'filter_length':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'number of filter taps to use (1000)'),
            }
            self.addWidgets()
except:
    __ver__ = 'TEST'



class Narrowband:
    """
	Demodulates NB channels to track the amplitude and phase
	"""

    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self, config, logger):
        """
		Constructs the Narrowband object according to the supplied XML
		description.
		"""
        # Initialize data members
        self.filename = None
        self.fileStart = None
        self.startTime = None
        self.logger = logger

        self.already_saved = True

        self.x = None
        self.start_index = None
        self.num_samples = None




        #Filter Properties:
        #DemodDec                = self._GetIntElemVal(config, "Demod_Decimate_Factor",100) #Default: 100kHz -> 1kHz : A,B
        #DemodBufLen       = self._GetIntElemVal(config, "Demod_Buffer_Length",100000) #Default: buffers 1 sec. of 100 kHz data
        #FilteredLen       = self._GetIntElemVal(config, "Filtered_Length",1000) #Default: buffers 1 sec. of 100 kHz data
        #OutputLen       = self._GetIntElemVal(config, "Output_Buffer_Length",50) #Default: 50  Note: changing does not seem to matter...
        #DemodTimeInt       = self._GetDblElemVal(config, "Demod_Time_Interval",10e-6) #Default: 10 ms resolution for 100kHz.

        do_low_res              = self._GetIntElemVal(config, "do_low_res",1) #1 yes, 0 no
        do_sph_chan             = self._GetIntElemVal(config, "do_sph_chan",1)
        sampleFrequency         = self._GetIntElemVal(config, "Sample_Frequency",50) # Sampling rate [Hz]
        calibrationFactor		= self._GetDblElemVal(config, "Calibration_Factor",1) #Default: 1
##        FilterLength            = self._GetIntElemVal(config, "filter_length",1000) #[Number of Filter Taps to use]
        filter_tap_file         = self._GetStrElemVal(config, "filter_taps",'./filter_taps.txt') #[Path to txt Filter File]
        call_signs               = self._GetStrElemVal(config, "call_sign", 'XXX')
        conf_file               = self._GetStrElemVal(config, "call_sign_file", './nb.conf')


        call_sign_config = ConfigParser()
        fp = open(conf_file)
        call_sign_config.readfp(fp)
        fp.close()

##        ftaps = sio.loadmat(filter_tap_file)
##        FilterTaps = np.array(ftaps['filter_taps'].take(np.arange(FilterLength)), dtype='float32')
        FilterTaps = np.loadtxt(filter_tap_file,unpack=True,dtype='float32')
        FilterLength = len(FilterTaps)

        #print FilterTaps
        #(change to be defined by callsign)

        call_sign = []
        TransFreq = []
        is_msk = []

        #use call_sign_config to find frequencies, msk flags:
        avail_transmitters = call_sign_config.items('NB_Transmitters')
        call_signs = call_signs.split(',')

        for callSign in call_signs:
            callSign = callSign.strip()
            for avail_sign in avail_transmitters:
                if callSign.lower()==avail_sign[0].strip().lower():
                    call_sign.append(callSign)
                    freq_msk = avail_sign[1].split(',')
                    TransFreq.append(int(freq_msk[0].strip())) #[Hz]
                    is_msk.append(int(freq_msk[1].strip())) #[0 (no) or 1 (yes)]


        nb_input = [FilterTaps,FilterLength,TransFreq, sampleFrequency, calibrationFactor, is_msk, do_low_res, call_sign,do_sph_chan]; #0-7

        self.queue = Queue(500)
        asyncSave = Process(target=_AsyncSave,args = (self.queue, nb_input, config))

        asyncSave.daemon = True

        asyncSave.start()

    # =======
    # Methods
    # =======
    def Process(self, data):
        """
        Writes the received data to file as a Level-4 MAT File.
        bb data: data[0]

        """

        try:
            #self.queue.put([data[0].copy(),self.fileprefixs],block=False)
            self.queue.put(data,block=False)
        except Full:
            self.logger.warning('NarrowbandProcessor: Queue full  ')
        except Exception, exc:
            self.logger.error('NarrowbandProcessor: Unexpected error encountered when posting data to queue: %s' % exc)
            self.logger.warning('Slow to process, try increasing Queue length?')

        return 0


    def _GetIntElemVal(self, config, tag,default=None):
        if default is not None:
            if len(config.getElementsByTagName(tag))==0:
                return default
        child = config.getElementsByTagName(tag)[0].firstChild
        if child is None:
            return 0
        else:
##			print 'converting an int'
            return int(child.data)

    def _GetStrElemVal(self, config, tag,default=None):
        if default is not None:
            if len(config.getElementsByTagName(tag))==0:
                return default
        child = config.getElementsByTagName(tag)[0].firstChild
        if child is None:
            return '.'
        else:
##			print 'converting an str'
            return str(child.data)

    def _GetDblElemVal(self, config, tag,default=None):
        if default is not None:
            if len(config.getElementsByTagName(tag))==0:
                return default
        child = config.getElementsByTagName(tag)[0].firstChild
        if child is None:
            return 0.0
        else:
##			print 'converting an float'
            return float(child.data)


    def _parseDirectory(self,dir_string):
        index_comma = dir_string.rfind(',')
        if index_comma==-1: #just a directory
            return(dir_string,None)
        else:
            return (dir_string[:index_comma],dir_string[index_comma+1:])



class dummyLogger():
    def __init__(self,name=''):
        self.name = name
    def debug(self,a=''):
        print '%s: DEBUG: %s' % (self.name,a)
    def info(self,a=''):
        print '%s: INFO: %s' % (self.name,a)
    def warning(self,a=''):
        print '%s: WARNING: %s' % (self.name,a)
    def error(self,a=''):
        print '%s: ERROR: %s' % (self.name,a)
    def critical(self,a=''):
        print '%s: CRITICAL: %s' % (self.name,a)

##class AsyncSave(Thread):
def _AsyncSave(queue,nb_input,config):


    #nb_input = [FilterTaps,FilterLength,TransFreq, sampleFrequency, calibrationFactor, is_msk, do_low_res, call_sign,do_sph_channel]
    #Create Filter:
    do_sph_channel = nb_input[8]
    do_low_res = nb_input[6] #[1 yes, 0 no]
    num_nb_channels = len(nb_input[2])

    nb_filter = []

    for jj in range(num_nb_channels):

        nb_filter.append(nb.CreateNBFilter(nb_input[0],nb_input[1],nb_input[2][jj],
                                  nb_input[3],nb_input[4],nb_input[5][jj],
                                  do_low_res)
                                  )

    logger = dummyLogger()



    #Create FileWriters:
    amp_config = []
    phase_config = []
    ampMat = []
    phaseMat =[]

    for jj in range(num_nb_channels):
        amp_config.append((1,nb_input[5][jj], 'C', nb_input[0], nb_input[2][jj],nb_input[7][jj])) #parseString("<amp> <is_amp>%d</is_amp> <is_msk>%d</is_msk> <T>%s</T> </amp>" % (1, 0, 'A'))
        phase_config.append((0,nb_input[5][jj],'D',nb_input[0], nb_input[2][jj],nb_input[7][jj])) #parseString("<phase> <is_amp>%d</is_amp> <is_msk>%d</is_msk> <T>%s</T> </phase>" % (1, 1, 'B'))

        ampMat.append(matf.MatFileWriter(config, logger, amp_config[jj]))
        #config.getElementsByTagName("is_msk")[0].firstChild.nodeValue = 1
        phaseMat.append(matf.MatFileWriter(config, logger, phase_config[jj]))


    if do_low_res == 1:

        amp_low_config = []
        phase_low_config = []
        ampMat_low = []
        phaseMat_low =[]

        for jj in range(num_nb_channels):
            amp_low_config.append((1,nb_input[5][jj], 'A', nb_input[0], nb_input[2][jj],nb_input[7][jj]))
            phase_low_config.append((0,nb_input[5][jj],'B',nb_input[0], nb_input[2][jj],nb_input[7][jj]))
            ampMat_low.append(matf.MatFileWriter(config, logger, amp_low_config[jj]))
            phaseMat_low.append(matf.MatFileWriter(config, logger, phase_low_config[jj]))


    if do_sph_channel:
        sph_config = (1,0,'C',np.array([0.0]),0,'SPH')
        sphMat = matf.MatFileWriter(config,logger,sph_config)



    last_queue_size = 0
    prev_time = None

    wait_time = 3600*36    #wait a day and a half for activity, then quit

    block_num = -1

    elapsed_time = 0

    while True:
        try:
            data = queue.get(timeout=wait_time)     # Pull this second's timestamp from the GPS clock
            block_num += 1
            #print 'Got queue element %d' % block_num
        except Empty:
            logger.warning('Waiting for %d seconds, quitting NarrowBand AsyncSave process ' % wait_time)
            break

        except Exception, exc:
            loger.error('Unexpected error when reading from Narrowband Queue: %s' % exc)

        #Verify datastream is contiguous -- commented out by RKS (handled in GPS module)
##        if prev_time is not None:
##            td = data[1][0] - prev_time
##            td = td.days*86400+td.seconds + td.microseconds*1e-6
##            if int(round(td)) is not 1:
##                logger.error('Resetting filter, timedelta = %f' % td)
##                for jj in range(num_nb_channels):
##                    nb.ResetNBFilter(nb_filter[jj])
##                    ampMat[jj].StartNewFile()
##                    phaseMat[jj].StartNewFile()
##                    if do_low_res:
##                        ampMat_low[jj].StartNewFile()
##                        phaseMat_low[jj].StartNewFile()
##                if do_sph_channel:
##                    sphMat.StartNewFile()

        prev_time = data[1][0]

        ttt = clock()
        for jj in range(num_nb_channels):
            #Process this second of data through the filter:
            if do_low_res == 1:
                #print "low_res"
                #print data[0]
                amp,phase,amp_low,phase_low = nb.ProcessNB(nb_filter[jj],data[0])
            else:
                amp,phase = nb.ProcessNB(nb_filter[jj],data[0])

            #print "Grabbing for timestamp %s." % data[1][0]
            samplingRate = amp.size
            ampMat[jj].Process([amp, data[1] ,samplingRate],dtype='float32')
            phaseMat[jj].Process([phase, data[1] ,samplingRate],dtype='float32')


            if do_low_res == 1:
                samplingRate = amp_low.size
                ampMat_low[jj].Process([amp_low, data[1] ,samplingRate],dtype='float32')
                phaseMat_low[jj].Process([phase_low, data[1] ,samplingRate],dtype='float32')


        if do_sph_channel:
            sph = nb.ProcessSPH(50,data[0])
            sphMat.Process([sph,data[1],sph.size],dtype='float32')

        data[0] = np.array([])
        elapsed_time_temp = clock()-ttt
        if elapsed_time_temp > elapsed_time:
            elapsed_time = elapsed_time_temp
            if elapsed_time > .7:
                logger.warning('Time for last second of narrowband processing: %3.2f' % elapsed_time)
##        print 'Time per nb channel: %2.4f (%d channels)' % ((clock()-ttt)/num_nb_channels,num_nb_channels)

    #print "RealMixed[0] = %f" % amp[0]


# =========
# Unit Test
#=========
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    from xml.dom.minidom import parseString
    import numpy
    from datetime import datetime, timedelta
    import time as timemod
    import os
    import logging
    import scipy.io as sio


    # Create log
    logging.basicConfig()
    logger = logging.getLogger("Unit Test")
    logger.setLevel(logging.DEBUG)




    # Create the Motorola GPS clock object
    settings = """
    <PostProcessor module="Narrowband">
        <DirectoryRoot>./narrowband_source/Data</DirectoryRoot>
        <DirectoryRoot1>./Data</DirectoryRoot1>
        <station_id>PH</station_id>
        <station_name>Philmont</station_name>
        <adc_card>0</adc_card>
        <adc_channel_number>002</adc_channel_number>
		<Duration>3600</Duration>
        <call_sign_file>./nb.conf</call_sign_file>
        <call_sign>NAA,NPM,NML,NLK</call_sign>
		<do_low_res>1</do_low_res>
        <do_sph_chan>1</do_sph_chan>
        <filter_taps>./filter_taps2.txt</filter_taps>
        <filter_length>1</filter_length>
    </PostProcessor>
    """

    config = parseString(settings)
    #config.getElementsByTagName("Fc").setAttribute("Fc", 200)
    #config.getElementsByTagName("Fc")[0].firstChild.nodeValue = 1
    #print config.toxml()

    nbproc = Narrowband(parseString(settings),logger)

    # Read matlab file
##    mat_data = sio.loadmat(r"Z:\awesome\broadband\palmer\2009\09_23\PA090923000000_000.mat")#("./Data/DAQ_Data/TestNAA.mat")#("./LatestNS.mat")#
    mat_data = sio.loadmat(r"Z:\awesome\broadband\taylor\2008\07_21\TA080721000500_002.mat")
    ##print mat_data['adc_type'].data
    ##print "%d" %mat_data['Fs']
    ##print mat_data['data'].transpose()

    L = 1   #[seconds]
    fs = mat_data['Fs']
    #print fs
    t = np.arange(L*fs)/fs

    time = datetime(year=mat_data['start_year'], month=mat_data['start_month'], day=mat_data['start_day'], hour=mat_data['start_hour'], minute=mat_data['start_minute'], second=mat_data['start_second'])


    for i in range(60):

##        rawBuffer = np.array(mat_data['data'].take(np.arange(t.size)+i*t.size), dtype='float64')
        rawBuffer = mat_data['data'][i*t.size:(i+1)*t.size]
        #print rawBuffer
        data = [rawBuffer, [time, [0, 0, 0], [8]],fs]
        if(i >= 0):
            print "Processing for timestamp %s." % data[1][0]
            nbproc.Process(data)
            timemod.sleep(.1)
        time += timedelta(seconds=1)
        t += L

    timemod.sleep(45)
##    spec.queue.join()
