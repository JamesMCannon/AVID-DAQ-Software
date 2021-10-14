from ConfigParser import ConfigParser
import re, os
from datetime import datetime
from StringIO import StringIO

class _xml:
    def __init__(self, name, value, modifier=None):
        self.name = name
        if modifier is not None:
            mod = ' ' + modifier
        else:
            mod = ''

        if value=='':
            value = '\n'

        self.string = '<' + name + mod + '>'
        self.string += str(value)


    def __str__(self):
        return self.string + '</' + self.name + '>\n'


    def add_entry(self, xml):
        self.string += "\t" + str(xml).replace("\n","\n\t")
        self.string = self.string[:-1]

class ConfigWrapper:
    def __init__(self, conf_file):
        #read defaults
        #self.defaults = ConfigParser()
        #self.defaults.optionxform = lambda x: x
        #fp = StringIO(default_conf_file)
        #self.defaults.readfp(fp)
        #fp.close()

        #read conf file
        self.config = ConfigParser()
        self.config.optionxform = lambda x: x    #Otherwise, name is forced to lower case
        fp = open(conf_file)
        self.config.readfp(fp)
        fp.close()

    def get(self,section,varname):
        """
        Allow for default
        """
        try:
            return self.config.get(section,varname)
        except:
            return self.defaults.get(section,varname)

class MakeSettingsFile:

    def __init__(self, conf_file, settings_name='DaqSettings.xml'):

        self.config = ConfigWrapper(conf_file)

        self.settings_name=settings_name

        self.checked_rsa_key = False



    def add_ssh_settings(self,xml):
        xml.add_entry(_xml('Username',self.config.get('SSH','ssh_username')))
        xml.add_entry(_xml('Hostname',self.config.get('SSH','ssh_server')))
        xml.add_entry(_xml('RSA_Key_file',self.config.get('SSH','rsa_key_name')))
        xml.add_entry(_xml('Port',self.config.get('SSH','ssh_port')))
##        xml.add_entry(_xml('SftpTimeout',10.0))
##        xml.add_entry(_xml('ftp',0))
##        xml.add_entry(_xml('StartTime',self.config.get('SSH','start_time')))
##        xml.add_entry(_xml('EndTime',self.config.get('SSH','end_time')))
        xml.add_entry(_xml('StartTime','00:00'))
        xml.add_entry(_xml('EndTime','23:59'))

    def add_ssh_settings_schedule(self,xml):
        xml.add_entry(_xml('Username',self.config.get('SSH','ssh_username')))
        xml.add_entry(_xml('Hostname',self.config.get('SSH','ssh_server')))
        xml.add_entry(_xml('RSA_Key_file',self.config.get('SSH','rsa_key_name')))
        xml.add_entry(_xml('Port',self.config.get('SSH','ssh_port')))
        xml.add_entry(_xml('StartTime',self.config.get('SSH','start_time')))
        xml.add_entry(_xml('EndTime',self.config.get('SSH','end_time')))



    def check_rsa_key(self):
        if not os.path.isfile(self.config.get('SSH','rsa_key_name')) and not self.checked_rsa_key:
            print 'WARNING: rsa key %s does not exist' % self.config.get('SSH','rsa_key_name')
            self.checked_rsa_key = True


    def make_settings(self):
        daq = _xml('DaqConfiguration','')

        self.station_name = self.config.get('Basics','station_name')
        self.station_id = self.config.get('Basics','station_id')

        DataRootFolder = self.config.get('Basics','DataRootFolder')

        #Station settings
        settings = _xml('StationSettings','')
        settings.add_entry(_xml('station_id',self.station_id))
        settings.add_entry(_xml('station_name',self.station_name))
        settings.add_entry(_xml('IsLF',self.config.get('Basics','IsLF'))) 
        settings.add_entry(_xml('IsResettable',self.config.get('Basics','IsResettable'))) 
        
        notes = ['station_description','hardware_description','antenna_bearings',
                'antenna_description','install_date','contact_info','adc_type',
                'computer_sn','adc_sn','gps_sn']
        for note in notes:
            settings.add_entry(_xml(note,self.config.get('Station_Notes',note)))

        daq.add_entry(settings)

        #DaqCard
        self.num_channels = int(self.config.get('Basics','NumChannels'))
        card = _xml('DaqCard','','module="NIDAQmx"')
        card.add_entry(_xml('SampleClockName','PFI2'))
        card.add_entry(_xml('StartTriggerName','PFI0'))
        card.add_entry(_xml('SampleClockPolarity',self.config.get('Basics','SampleClockPolarity')))
        card.add_entry(_xml('StartTriggerPolarity',self.config.get('Basics','StartTriggerPolarity')))
        card.add_entry(_xml('SampleRate',self.config.get('Basics','SampleRate')))
        card.add_entry(_xml('DevName',self.config.get('Basics','DevName')))
        card.add_entry(_xml('NumChannels',self.config.get('Basics','NumChannels')))
        card.add_entry(_xml('SingleEndedInput',self.config.get('Basics','SingleEndedInput')))
        daq.add_entry(card)

        #GPS Clock
        if self.config.get('Basics','GPSType').lower()[0]=='t':
            clock = _xml('GpsClock','','module="TrueTimeClock"')
            clock.add_entry(_xml('DataBits',7))
            clock.add_entry(_xml('Parity','E'))
        else:
            clock = _xml('GpsClock','','module="MotorolaClock"')
            clock.add_entry(_xml('DataBits',8))
            clock.add_entry(_xml('Parity','N'))
        clock.add_entry(_xml('StopBits',1))
        clock.add_entry(_xml('BaudRate',9600))
        clock.add_entry(_xml('ComPortNumber',self.config.get('Basics','COM_port')))
        daq.add_entry(clock)

        #-----
        #Tasks
        #-----
        tasks = _xml('TaskManagerSettings','')

        #ssh_Broadband
        if self.config.get('SSH','ssh_Broadband')=='1':
            self.check_rsa_key()
            ssh = _xml('Task','','module="SFTP"')
            ssh.add_entry(_xml('Directory',os.path.join(DataRootFolder,'ssh_Broadband')))
            ssh.add_entry(_xml('TargetDirectory','broadband/%s' % self.station_name.lower()))
            ssh.add_entry(_xml('Period',5))
            self.add_ssh_settings(ssh)
            tasks.add_entry(ssh)

        #ssh_Narrowband
        if self.config.get('SSH','ssh_Narrowband')=='1':
            self.check_rsa_key()
            ssh = _xml('Task','','module="SFTP"')
            ssh.add_entry(_xml('Directory',os.path.join(DataRootFolder,'ssh_Narrowband')))
            ssh.add_entry(_xml('TargetDirectory','narrowband/%s' % self.station_name.lower()))
            ssh.add_entry(_xml('Period',60))
            self.add_ssh_settings_schedule(ssh)
            tasks.add_entry(ssh)

        #ssh_Latest
        if self.config.get('SSH','ssh_Latest')=='1':
            self.check_rsa_key()
            ssh = _xml('Task','','module="SFTP"')
            ssh.add_entry(_xml('Directory',os.path.join(DataRootFolder,'ssh_Latest')))
            ssh.add_entry(_xml('TargetDirectory','live_spectrograms/%s' % self.station_name.lower()))
            ssh.add_entry(_xml('Period',15))
            self.add_ssh_settings(ssh)
            tasks.add_entry(ssh)

        #ssh_Log
        if self.config.get('SSH','ssh_Log')=='1':
            self.check_rsa_key()
            ssh = _xml('Task','','module="SFTP"')
            ssh.add_entry(_xml('Directory',os.path.join(DataRootFolder,'ssh_Log')))
            ssh.add_entry(_xml('TargetDirectory','other/%s' % self.station_name.lower()))
            ssh.add_entry(_xml('Period',3600))
            self.add_ssh_settings(ssh)
            tasks.add_entry(ssh)

        #remote_retrieval
        if self.config.get('SSH','remote_retrieval')=='1':
            rrt = _xml('Task','','module="RemoteRetrieval"')
            rrt.add_entry(_xml('DataDirectory',os.path.join(DataRootFolder,'Continuous')))
            rrt.add_entry(_xml('LocalSaveDirectory',os.path.join(DataRootFolder,'ssh_Broadband')))
            rrt.add_entry(_xml('RemoteRequestDirectory','data_requests/%s' % self.station_id))
            rrt.add_entry(_xml('Period',30))
            rrt.add_entry(_xml('Username',self.config.get('SSH','ssh_username')))
            rrt.add_entry(_xml('Hostname',self.config.get('SSH','ssh_server')))
            rrt.add_entry(_xml('RSA_Key_file',self.config.get('SSH','rsa_key_name')))
            rrt.add_entry(_xml('Port',self.config.get('SSH','ssh_port')))
            tasks.add_entry(rrt)
            
        #local_retrieval
        if self.config.get('Basics','local_retrieval')=='1':
            extdriveroot = self.config.get('Copy_To_External','external_drive')
            if not os.path.isdir(extdriveroot):
                print 'WARNING: Save Folder %s does not exist' % extdriveroot
            lrt = _xml('Task','','module="LocalRetrieval"')
            lrt.add_entry(_xml('DataDirectory',os.path.join(DataRootFolder,'Continuous')))
            lrt.add_entry(_xml('SaveDirectory',os.path.join(extdriveroot,'SavedBroadband')))
            lrt.add_entry(_xml('RequestDirectory',os.path.join(DataRootFolder,'Requests')))
            lrt.add_entry(_xml('Period',30))
            tasks.add_entry(lrt)

        #post
        if self.config.get('POST','active')=='1':
            post = _xml('Task','','module="HTTP_POST"')
            post.add_entry(_xml('Directory',os.path.join(DataRootFolder,'POST')))
            post.add_entry(_xml('Period',120))
            post.add_entry(_xml('Hostname',self.config.get('POST','post_server')))
            tasks.add_entry(post)

        #cleanup
        if self.config.get('Cleanup','active')=='1':
            if self.config.get('BBFileWriters','Continuous')=='1':
                clean = _xml('Task','','module="Cleanup"')
                clean.add_entry(_xml('Directory',os.path.join(DataRootFolder,'Continuous')))
                clean.add_entry(_xml('Interval',3600))
                clean.add_entry(_xml('StartTime','00:00'))
                clean.add_entry(_xml('EndTime','23:59'))
                clean.add_entry(_xml('DataLifetime',self.config.get('Cleanup','cleanup_cont_days')))
                tasks.add_entry(clean)

            if self.config.get('BBFileWriters','Synoptic')=='1':
                clean = _xml('Task','','module="Cleanup"')
                clean.add_entry(_xml('Directory',os.path.join(DataRootFolder,'Synoptic')))
                clean.add_entry(_xml('Interval',3600))
                clean.add_entry(_xml('StartTime','00:00'))
                clean.add_entry(_xml('EndTime','23:59'))
                # clean.add_entry(_xml('DataLifetime',str(24*int(self.config.get('Cleanup','cleanup_synoptic_days')))))
                clean.add_entry(_xml('DataLifetime',self.config.get('Cleanup','cleanup_synoptic_days')))

                tasks.add_entry(clean)

            if self.config.get('Spectrogram','active')=='1':
                clean = _xml('Task','','module="Cleanup"')
                clean.add_entry(_xml('Directory',os.path.join(DataRootFolder,'Spectrogram')))
                clean.add_entry(_xml('Interval',3600))
                clean.add_entry(_xml('StartTime','00:00'))
                clean.add_entry(_xml('EndTime','23:59'))
                clean.add_entry(_xml('DataLifetime',self.config.get('Cleanup','cleanup_spec_days')))
                tasks.add_entry(clean)

            if (self.config.get('Narrowband','active')=='1') and \
                ((self.config.get('SSH','ssh_Narrowband')=='0') or (self.config.get('SSH','KeepLocalCopyNB')=='1')):
                clean = _xml('Task','','module="Cleanup"')
                clean.add_entry(_xml('Directory',os.path.join(DataRootFolder,'Narrowband')))
                clean.add_entry(_xml('Interval',3600))
                clean.add_entry(_xml('StartTime','00:00'))
                clean.add_entry(_xml('EndTime','23:59'))
                clean.add_entry(_xml('DataLifetime',self.config.get('Cleanup','cleanup_narrowband_days')))
                tasks.add_entry(clean)


        #copy to external
        if self.config.get('Copy_To_External','active')=='1':
            # List of drive roots to copy to
            driveroots = self.config.get('Copy_To_External','external_drive').split(',')
            for driveroot in driveroots:
                if not os.path.isdir(driveroot):
                    print 'WARNING: Save Folder %s does not exist' % driveroot

            if self.config.get('BBFileWriters','Continuous')=='1':
                copy = _xml('Task','','module="CopyFiles"')

                # if not os.path.isdir('ContinuousToKeep'):
                #     os.mkdir('ContinuousToKeep')

                # copy.add_entry(_xml('Directory',os.path.join(DataRootFolder,'ContinuousToKeep')))
                # copy.add_entry(_xml('Interval',3600))
                # copy.add_entry(_xml('Delete',1))
                # copy.add_entry(_xml('StartTime','00:00'))
                # copy.add_entry(_xml('EndTime','23:59'))
                # for ii, driveroot in enumerate(driveroots):
                #     copy.add_entry(_xml('WriteDirectory%d'%ii,os.path.join(driveroot,'Continuous')))
                # tasks.add_entry(copy)

                copy = _xml('Task','','module="CopyFiles"')
                # Copy from the "continous" directory as well. This will override the 'cleanup' task.
                copy.add_entry(_xml('Directory',os.path.join(DataRootFolder,'Continuous')))
                copy.add_entry(_xml('Interval',1800))
                copy.add_entry(_xml('Delete',1))
                copy.add_entry(_xml('StartTime','00:00'))
                copy.add_entry(_xml('EndTime','23:59'))
                for ii, driveroot in enumerate(driveroots):
                    copy.add_entry(_xml('WriteDirectory%d'%ii,os.path.join(driveroot,'Continuous')))
                tasks.add_entry(copy)


            if self.config.get('BBFileWriters','Synoptic')=='1':
                copy = _xml('Task','','module="CopyFiles"')
                copy.add_entry(_xml('Directory',os.path.join(DataRootFolder,'Synoptic')))
                copy.add_entry(_xml('Interval',1800))
                copy.add_entry(_xml('Delete',1))
                copy.add_entry(_xml('StartTime','00:00'))
                copy.add_entry(_xml('EndTime','23:59'))
                for ii, driveroot in enumerate(driveroots):
                    copy.add_entry(_xml('WriteDirectory%d'%ii,os.path.join(driveroot,'Synoptic')))
                tasks.add_entry(copy)

            if (self.config.get('Spectrogram','active')=='1') and \
                (self.config.get('Spectrogram','copy_to_external')=='1'):
                copy = _xml('Task','','module="CopyFiles"')
                copy.add_entry(_xml('Directory',os.path.join(DataRootFolder,'Spectrogram')))
                copy.add_entry(_xml('Interval',1800))
                copy.add_entry(_xml('Delete',1))
                copy.add_entry(_xml('StartTime','00:00'))
                copy.add_entry(_xml('EndTime','23:59'))
                for ii, driveroot in enumerate(driveroots):
                    copy.add_entry(_xml('WriteDirectory%d'%ii,os.path.join(driveroot,'Spectrogram')))
                tasks.add_entry(copy)

            if (self.config.get('Narrowband','active')=='1') and \
                ((self.config.get('SSH','ssh_Narrowband')=='0') or (self.config.get('SSH','KeepLocalCopyNB')=='1')):
                copy = _xml('Task','','module="CopyFiles"')
                copy.add_entry(_xml('Directory',os.path.join(DataRootFolder,'Narrowband')))
                copy.add_entry(_xml('Interval',1800))
                copy.add_entry(_xml('Delete',1))
                copy.add_entry(_xml('StartTime','00:00'))
                copy.add_entry(_xml('EndTime','23:59'))
                for ii, driveroot in enumerate(driveroots):
                    copy.add_entry(_xml('WriteDirectory%d'%ii,os.path.join(driveroot,'Narrowband')))
                tasks.add_entry(copy)


        #copy settings/log files:
        copy = _xml('Task','','module="CopyFiles"')
        copy.add_entry(_xml('Filename','DaqSettings.xml'))
        copy.add_entry(_xml('Filename0','default_LF_settings.txt'))
        copy.add_entry(_xml('Filename1','default_VLF_settings.txt'))
        #copy.add_entry(_xml('Filename2','Engine.log'))
        #copy.add_entry(_xml('Filename3','TaskManager.log'))
        #copy.add_entry(_xml('Filename4','PostProcessors.log'))
        copy.add_entry(_xml('Filename4','log/VLFDAQ.log'))
        copy.add_entry(_xml('Interval',43200))
        copy.add_entry(_xml('Delete',0))
        copy.add_entry(_xml('StartTime','00:00'))
        copy.add_entry(_xml('EndTime','23:59'))
        copy.add_entry(_xml('WriteDirectory',os.path.join(DataRootFolder,'ssh_Log')))
        tasks.add_entry(copy)

        
        #copy log files to Dropbox
        if self.config.get('Copy_To_Dropbox','active')=='1':
            copy = _xml('Task','','module="CopyFiles"')
            if self.config.get('Copy_To_Dropbox','tail_only') =='0':
                copy.add_entry(_xml('Filename','log/VLFDAQ.log'))
            copy.add_entry(_xml('Filename1','DaqSettings.xml'))
            # copy.add_entry(_xml('Filename2','default_LF_settings.txt'))
        
            copy.add_entry(_xml('Interval',self.config.get('Copy_To_Dropbox','copy_period')))
            copy.add_entry(_xml('Delete',0))
            copy.add_entry(_xml('StartTime','00:00'))
            copy.add_entry(_xml('EndTime','23:59'))
            copy.add_entry(_xml('WriteDirectory',self.config.get('Copy_To_Dropbox','dropbox_dir')))
            tasks.add_entry(copy)

            if self.config.get('Copy_To_Dropbox','tail_only') == '1':
                tail = _xml('Task','','module="SaveTail"')
                tail.add_entry(_xml('in_file','log/VLFDAQ.log'))
                tail.add_entry(_xml('out_file',os.path.join(self.config.get('Copy_To_Dropbox','dropbox_dir'),'VLFDAQ.log')))
                tail.add_entry(_xml('chars',4096))
                tail.add_entry(_xml('StartTime','00:00'))
                tail.add_entry(_xml('EndTime','23:59'))
                tail.add_entry(_xml('Interval',self.config.get('Copy_To_Dropbox','copy_period')))
                tasks.add_entry(tail)

        daq.add_entry(tasks)

        #--------------------
        #Post processor tree
        #-------------------
        ppt = _xml('PostProcessorTree','')

        ch_name = ['NS','EW','AUX','AUX2','AUX3','AUX4']
        for ii in range(self.num_channels):
            pps = _xml('PostProcessorSequence','')

            #Continuous
            if self.config.get('BBFileWriters','Continuous')=='1':
                ppst = _xml('PostProcessorSequence','')
                pp = _xml('PostProcessor','','module="MatFileWriter"')
                pp.add_entry(_xml('adc_channel_number',ii))
                pp.add_entry(_xml('DirectoryRoot',os.path.join(DataRootFolder,'Continuous')))
                pp.add_entry(_xml('IsSynoptic',0))
                pp.add_entry(_xml('Duration',self.config.get('BBFileWriters','ContinuousDuration')))
                ppst.add_entry(pp)
                pps.add_entry(ppst)

            #Synoptic
            if self.config.get('BBFileWriters','Synoptic')=='1':
                ppst = _xml('PostProcessorSequence','')
                pp = _xml('PostProcessor','','module="MatFileWriter"')
                pp.add_entry(_xml('adc_channel_number',ii))
                pp.add_entry(_xml('DirectoryRoot',os.path.join(DataRootFolder,'Synoptic')))
                pp.add_entry(_xml('IsSynoptic',1))
                pp.add_entry(_xml('SynopticPeriod',self.config.get('BBFileWriters','SynopticPeriod')))
                pp.add_entry(_xml('Duration',self.config.get('BBFileWriters','SynopticDuration')))
                ppst.add_entry(pp)
                pps.add_entry(ppst)

            #Snapshot
            if self.config.get('BBFileWriters','Snapshot')=='1':
                ppst = _xml('PostProcessorSequence','')
                pp = _xml('PostProcessor','','module="MatFileWriter"')
                pp.add_entry(_xml('adc_channel_number',ii))
                pp.add_entry(_xml('DirectoryRoot',os.path.join(DataRootFolder,'ssh_Broadband')))
                pp.add_entry(_xml('IsSynoptic',1))
                pp.add_entry(_xml('SynopticPeriod',43200))
                pp.add_entry(_xml('Duration',1))
                ppst.add_entry(pp)
                pps.add_entry(ppst)

            #Post
            if self.config.get('POST','active')=='1':
                ppst = _xml('PostProcessorSequence','')
                pp = _xml('PostProcessor','','module="MatFileWriter"')
                pp.add_entry(_xml('adc_channel_number',ii))
                pp.add_entry(_xml('DirectoryRoot',os.path.join(DataRootFolder,'POST')))
                pp.add_entry(_xml('IsSynoptic',1))
                pp.add_entry(_xml('SynopticPeriod',3600))
                pp.add_entry(_xml('Duration',1))
                ppst.add_entry(pp)
                pps.add_entry(ppst)

            #Narrowband
            if self.config.get('Narrowband','active')=='1':
                ppst = _xml('PostProcessorSequence','')
                pp = _xml('PostProcessor','','module="Narrowband"')
                pp.add_entry(_xml('adc_channel_number',ii))
                if self.config.get('SSH','ssh_Narrowband')=='1':
                    pp.add_entry(_xml('DirectoryRoot',os.path.join(DataRootFolder,'ssh_Narrowband')))
                    if self.config.get('SSH','KeepLocalCopyNB')=='1':
                        pp.add_entry(_xml('DirectoryRoot1','Narrowband'))
                else:
                    pp.add_entry(_xml('DirectoryRoot',os.path.join(DataRootFolder,'Narrowband')))
                pp.add_entry(_xml('do_sph_chan',1))
                pp.add_entry(_xml('do_low_res',1))
                pp.add_entry(_xml('Duration',86400))
                pp.add_entry(_xml('call_sign',self.config.get('Narrowband','call_signs')))
                pp.add_entry(_xml('call_sign_file','nb.conf'))
                pp.add_entry(_xml('filter_taps','filter_taps.txt'))
                ppst.add_entry(pp)
                pps.add_entry(ppst)

            #Spectrogram
            if self.config.get('Spectrogram','active')=='1':
                ppst = _xml('PostProcessorSequence','')
                pp = _xml('PostProcessor','','module="Specgram"')
                pp.add_entry(_xml('adc_channel_number',ii))
                pp.add_entry(_xml('DirectoryRoot',os.path.join(DataRootFolder,'Spectrogram')))
                # If we plan on SSH'ing to our own server, write spectrograms into the SSH directory:
                if self.config.get('SSH','ssh_Latest')=='1':
                    pp.add_entry(_xml('DirectoryRoot1','ssh_Latest,latest%s.jpg' % ch_name[ii]))
                # If we're copying to the dropbox directory, write the spectrograms there:
                if self.config.get('Copy_To_Dropbox','active')=='1':
                    pp.add_entry(_xml('DirectoryRoot2','%s,latest%s.jpg' %(self.config.get('Copy_To_Dropbox','dropbox_dir'),ch_name[ii])))
                pp.add_entry(_xml('Duration',self.config.get('Spectrogram','duration')))
                pp.add_entry(_xml('Period',self.config.get('Spectrogram','period')))
                pp.add_entry(_xml('NFFT',self.config.get('Spectrogram','NFFT')))
                pp.add_entry(_xml('fmax',self.config.get('Spectrogram','fmax')))
                pp.add_entry(_xml('cmin',self.config.get('Spectrogram','cmin')))
                pp.add_entry(_xml('cmax',self.config.get('Spectrogram','cmax')))
                pp.add_entry(_xml('remove_hum',self.config.get('Spectrogram','remove_hum')))
                pp.add_entry(_xml('f0',self.config.get('Spectrogram','f0')))
                pp.add_entry(_xml('hum_fc',self.config.get('Spectrogram','hum_fc')))
                pp.add_entry(_xml('psd',self.config.get('Spectrogram','psd')))
                pp.add_entry(_xml('quality',self.config.get('Spectrogram','quality')))
                ppst.add_entry(pp)
                pps.add_entry(ppst)

            ppt.add_entry(pps)

        daq.add_entry(ppt)


        #schedule
        schedule = _xml('Schedule','')
        entry = _xml('Entry','')
        entry.add_entry(_xml('Duration',86400))
        entry.add_entry(_xml('Start','00:00'))
        schedule.add_entry(entry)
        daq.add_entry(schedule)


        #Logger
        logger = _xml('Logger','')
        logger.add_entry(_xml('LogDir',self.config.get('Logger','LogDir')))
        logger.add_entry(_xml('ErrorEmail',self.config.get('Logger','ErrorEmail')))
        logger.add_entry(_xml('ErrorEmailFrom',self.config.get('Logger','ErrorEmailFrom')))
        logger.add_entry(_xml('ErrorEmailTo',self.config.get('Logger','ErrorEmailTo')))
        logger.add_entry(_xml('ErrorEmailPw',self.config.get('Logger','ErrorEmailPw')))
        logger.add_entry(_xml('ErrorPost',self.config.get('Logger','ErrorPost')))
        logger.add_entry(_xml('LogPostUrl',self.config.get('Logger','LogPostUrl')))
        logger.add_entry(_xml('LogPostServer',self.config.get('Logger','LogPostServer')))
        #logger.add_entry(_xml('LogLevel',self.config.get('Logger','LogLevel')))
        logger.add_entry(_xml('ConsoleLevel',self.config.get('Logger','ConsoleLevel')))
        logger.add_entry(_xml('LogFileLevel',self.config.get('Logger','LogFileLevel')))
        logger.add_entry(_xml('PostLevel',self.config.get('Logger','PostLevel')))
        daq.add_entry(logger)
        
        #Tdiff threshold values:
        timing_limits = _xml('timing_limits','')
        timing_limits.add_entry(_xml('td_upper', self.config.get('timing_limits','upper')))
        timing_limits.add_entry(_xml('td_lower', self.config.get('timing_limits','lower')))
        daq.add_entry(timing_limits)

        # Closing File
        fid = open(self.settings_name,'w')
        fid.write("<!-- Settings generated at %s [UTC] by settings_generator -->\n\n" % datetime.utcnow())
        fid.write(str(daq))
        fid.close()
        
defaults = {}
if os.name=='nt':
    defaults['external'] = 'E:/'
    defaults['COM'] = '1'
    defaults['rsa'] = 'site_name'
    defaults['DataRootFolder'] = ''
else:
    defaults['external'] = '/dev/media'
    defaults['COM'] = '/dev/ttyUSB0'
    defaults['rsa'] = '/home/vlf/.ssh/site_name'
    defaults['DataRootFolder'] = '/home/vlf/Data/'

## Default LF Configuration
default_LF_conf_file = """
#------
[Basics]
#------
station_id=XX
station_name=site_name
NumChannels=2

#DAQ card
DevName=Dev1
SampleRate=1000000
SampleClockPolarity=1
StartTriggerPolarity=1
SingleEndedInput=0

#GPS type: M (Motorola) or T (Truetime)
GPSType=M
COM_port=1

#Data root folder
DataRootFolder=

#Distinguish Receiver Style
IsLF=1
IsResettable=0

#Local Retrieval
local_retrieval=0

#----
[SSH]
#----
#set to 1 to enable
ssh_Broadband=0
ssh_Narrowband=0
KeepLocalCopyNB=0
ssh_Latest=1
ssh_Log=1
remote_retrieval=1

#ssh settings:
ssh_server=vlf-alexandria.stanford.edu
ssh_username=vlf-sftp
rsa_key_name=site_name
ssh_port=22
start_time=00:00
end_time=23:59

#------
[POST]
#------
active=1
post_server=http://vlf-engineering.stanford.edu/field_sites_uploads/upload_file.php

#--------
[Cleanup]
#--------
active=1

#Pacman days (if active)
cleanup_cont_days=5

#Synoptic/ narrowband/ spectrogram pacman days (if active)
#(useful if external hard drive removed, for example):
cleanup_synoptic_days=14
cleanup_narrowband_days=14
cleanup_spec_days=5

#-----------------
[Copy_To_External]
#-----------------
active=0

#External drive path (if active)
external_drive=E:/

#--------------
[BBFileWriters]
#--------------
Continuous=1
ContinuousDuration=600
Synoptic=1
SynopticPeriod=300
SynopticDuration=60
Snapshot=1

#------------
[Narrowband]
#------------
active=0
call_signs=NWC,NPM,NLK,NAA,NML,DHO,JJI

#------------
[Spectrogram]
#------------
active=1
copy_to_external=0
duration=10
period=3600
NFFT=16384
fmax=400
cmin=-10
cmax=50
remove_hum=0
f0=60
hum_fc=4000
psd=0
quality=75


#---------------
[Station_Notes]
#---------------
#Filler stuff (not required)
station_description=.
hardware_description=LF Receiver
antenna_bearings=.
antenna_description=.
install_date=.
contact_info=.
adc_type=.
computer_sn=.
adc_sn=.
gps_sn=.

#------
[Logger]
#------
LogDir=log/
ErrorEmail=1
ErrorPost=0
LogPostUrl=/field_sites_logs/logging.php
LogPostServer=vlf-engineering.stanford.edu:80
ConsoleLevel=TIMESTAMP
LogFileLevel=WARNING
PostLevel=WARNING
""" % defaults


## Default VLF Configuration
default_VLF_conf_file = """
#------
[Basics]
#------
station_id=XX
station_name=site_name
NumChannels=2

#DAQ card
DevName=Dev1
SampleRate=100000
SampleClockPolarity=1
StartTriggerPolarity=0
SingleEndedInput=0

#GPS type: M (Motorola) or T (Truetime)
GPSType=M
COM_port=1

#Data root folder
DataRootFolder=

#Distinguish Receiver Style
IsLF=0
IsResettable=0

#Local Retrieval
local_retrieval=0

#----
[SSH]
#----
#set to 1 to enable
ssh_Broadband=0
ssh_Narrowband=0
KeepLocalCopyNB=0
ssh_Latest=1
ssh_Log=1
remote_retrieval=1

#ssh settings:
ssh_server=vlf-alexandria.stanford.edu
ssh_username=vlf-sftp
rsa_key_name=site_name
ssh_port=22
start_time=00:00
end_time=23:59

#------
[POST]
#------
active=1
post_server=http://vlf-engineering.stanford.edu/field_sites_uploads/upload_file.php

#--------
[Cleanup]
#--------
active=1

#Pacman days (if active)
cleanup_cont_days=5

#Synoptic/ narrowband/ spectrogram pacman days (if active)
#(useful if external hard drive removed, for example):
cleanup_synoptic_days=14
cleanup_narrowband_days=14
cleanup_spec_days=5

#-----------------
[Copy_To_External]
#-----------------
active=0

#External drive path (if active)
external_drive=E:/

#--------------
[BBFileWriters]
#--------------
Continuous=1
ContinuousDuration=600
Synoptic=1
SynopticPeriod=300
SynopticDuration=60
Snapshot=1

#------------
[Narrowband]
#------------
active=0
call_signs=NWC,NPM,NLK,NAA,NML,DHO,JJI

#------------
[Spectrogram]
#------------
active=1
copy_to_external=0
duration=10
period=300
NFFT=1024
fmax=50
cmin=-15
cmax=50
remove_hum=0
f0=60
hum_fc=3000
psd=0
quality=75

#---------------
[Station_Notes]
#---------------
#Filler stuff (not required)
station_description=.
hardware_description=LF Receiver
antenna_bearings=.
antenna_description=.
install_date=.
contact_info=.
adc_type=.
computer_sn=.
adc_sn=.
gps_sn=.

#------
[Logger]
#------
LogDir=log/
ErrorEmail=1
ErrorPost=0
LogPostUrl=/field_sites_logs/logging.php
LogPostServer=vlf-engineering.stanford.edu:80
ConsoleLevel=TIMESTAMP
LogFileLevel=WARNING
PostLevel=WARNING
""" % defaults

if __name__=='__main__':

    from optparse import OptionParser

    parser=OptionParser(version= '2013.01.24',
                        description='Settings generator.')
    parser.add_option('--defaultLF', dest="defaultLF", default=False, action="store_true",
                      help="Generate default_LF_settings.txt file (default %default)")    
    parser.add_option('--defaultVLF', dest="defaultVLF", default=False, action="store_true",
                      help="Generate default_VLF_settings.txt file (default %default)")
    parser.add_option("--config", dest='config', default='generate_settings.txt', type="string",
                      help="configuration file to generate xml settings.  Default: %default")
    parser.add_option("--file", dest='filename', default='DaqSettings.xml', type="string",
                      help="Settings xml file name. Default: %default")


    (options,args) = parser.parse_args()

    if options.defaultLF:
        print "Generating default.xml from internal LF defaults"
        fid = open(options.config,'w')
        fid.write(default_LF_conf_file)
        fid.close()
    elif options.defaultVLF:
        print "Generating default.xml from internal VLF defaults"
        fid = open(options.config,'w')
        fid.write(default_VLF_conf_file)
        fid.close()
    else:
        print "Generating %s from %s." % (options.filename, options.config)
        m = MakeSettingsFile(options.config, options.filename)
        m.make_settings()





