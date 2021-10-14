import numpy
import time
from sys import stdout, exc_info
#import traceback
#import logging
from utilities.DAQLogger import DAQLogClient

__all__ = ['PostProcessorTree']

class PPTError(Exception):
    pass

class PostProcessorTree:
    """
    The PostProcessorTree is a container for Post Processor objects, each of
    which export a Process() methods.  The Post Processor objects are stored in
    a tree-like configuration as described in the XML passed to this
    constructor.  Data is passed by the PostProcessorTree to each Post Processor
    object for processing; the results are returned to the PostProcessorTree
    which then passes them in parallel to each of the Post Processor object's
    children.  Each subtree in the PostProcessorTree object is referred to in
    the code as a Post Processor sequence.
    """

    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self, config, stationSettings, parent):
        """
        Builds a PostProcessorTree object using the supplied XML description of
        the Post Processor tree structure.
        """
        
        # Logger
        #self.logger = logging.getLogger('Ppt')
        self.logger = parent.PPT_logger
        self.log_queue = parent.log_queue
        
        # Dynamically generate the post processor tree
        self.stationSettings = stationSettings  #append to postProcessor settings
        self.ppt = []
        
        sequencesSettings = config.childNodes
        
        def IsSequenceNode(x): return str(x.nodeName) == "PostProcessorSequence"
        
        sequencesSettings = filter(IsSequenceNode, sequencesSettings)
        
        for sequenceSettings in sequencesSettings:
            self.ppt.append(self.ConstructSequence(sequenceSettings))
            
        self.parent = parent #reference to Engine for error handling




    # =======
    # Methods
    # =======

    def Stop(self):
        # Stop each postprocessor gracefully
        for i in xrange(len(self.ppt)):
            # This gives us the postprocessors per channel
            
            ppt_ch = self.ppt[i]
            
            for j in xrange(len(ppt_ch)):
                # This gives us the postprocessor
                
                ppt_tree = ppt_ch[j]
                
                for k in xrange(len(ppt_tree)): 
                    # This gives us the ppt process
                    
                    ppt = ppt_tree[k]
                    
                    stop_op = getattr(ppt, "Stop", None)
                    
                    if callable(stop_op):
                        ppt.Stop()
       
        return True

    def Process(self, data):
        """
        Accepts data and passes it in parallel to each Post Processor sequence.
        The results of each Post Processor object's processing is then passed to
        the next Post Processor object in the sequence (in parallel, if the
        object has multiple children in the PostProcessorTree).
        
        data = [[ch0Data,ch1Data,ch2Data,...],[dt,[lat,lon,alt],[quality]],sampleRate]
        """
        
        gps_quality =  str(data[1][2][0])
        if gps_quality == '50':
            gps_quality = 'UNLOCKED'
        if gps_quality == '51':
            gps_quality = 'LOCKED'

        # For command line output
        #stdout.write("Processing %s channels (GPS quality: %s): %s >>              \r" % (len(data[0]),gps_quality,data[1][0]))
        self.logger.timestamping("Processing %sCH (Quality:%s): %s" % (len(data[0]),gps_quality,data[1][0]))
        
        for i in xrange(len(data[0])):
            self.ProcessSequence(self.ppt[i], [numpy.copy(data[0][i]), data[1], data[2]])
            
        self.logger.debug("Finished Processing.")

    # =========
    # Accessors
    # =========
    def GetNumSequences(self):
        """
        Returns the number of Post Processor sequences at the top level of the
        PostProcessorTree object.  This must be identical to the number of
        channels of data being returned by the DAQ card object.
        """
        return len(self.ppt)

    # ==============
    # Helper Methods
    # ==============
    def ConstructSequence(self, sequenceSettings):
        sequence = []
        for settings in sequenceSettings.childNodes:
            if str(settings.nodeName) == "PostProcessor":
            
                # Get module name
                module = str(settings.attributes["module"].value)
                
                # get channel number
                channel = str(settings.getElementsByTagName("adc_channel_number")[0].firstChild.data)
                
                # import python module
                processors = __import__("PostProcessors", globals(), locals(), [module], -1)
                
                # setup the logger with logger name
                logger = DAQLogClient(self.log_queue, "ENG.PPT.%s%s" % (module,channel) )
                
                #make station settings available to each post processor as a separate tree:
                settings.appendChild(self.stationSettings)
                
                #constructor = "processors." + module + "." + module + "(settings,logger)"
                constructor = "processors.%s.%s(settings,logger)" % (module,module)
                self.logger.debug("Contructing: %s" % constructor)
                
                try:
                    sequence.append(eval(constructor))
                except:
                    self.logger.exception("Exception while instantiating processor module: %s" % module)
                
                
            elif str(settings.nodeName) == "PostProcessorSequence":
                sequence.append(self.ConstructSequence(settings))
                
        return sequence

    def ProcessSequence(self, sequences, data):
        """
        data = [[chNData], [dt,[lat,lon,alt],[quality]], sampleRate]
        """
    
        try:
            if len(sequences)>1:
                # This makes backup copies
                originalData0 = numpy.copy(data[0])
                originalData1 = numpy.copy(data[1])
                originalData2 = numpy.copy(data[2])
                
            for i in xrange(len(sequences)):
                if (i>0):
                    data = [numpy.copy(originalData0), numpy.copy(originalData1), numpy.copy(originalData2)]
                for j in xrange(len(sequences[i])):
                    data = sequences[i][j].Process(data)
                    time.sleep(.01) #Force GIL release (expect << 100 sequences!)

        #except Exception,inst:
        except:
            #(excType, excValue, excTb) = exc_info()
            #tb = traceback.extract_tb(excTb)[-1]
            #self.logger.error('EXCEPTION: %s'% str(excValue))
            #self.logger.error('\tFile: %s'% tb[0])
            #self.logger.error('\tLine %s in function %s: %s'% (tb[1],tb[2],tb[3]))
            #self.logger.error("Exception Occurred in PostProcessing, Restarting...")
            self.logger.error("Exception in processing sequence.")

            raise
            
            #if self.parent:
            #    self.logger.error("Signaling Engine restart")
            #    self.parent.SignalEngineRestart()

# =========
# Unit Test
# =========
if __name__ == "__main__":
    from xml.dom.minidom import parseString
    import numpy
    from datetime import datetime

    # Create the Motorola GPS clock object
    settings = """\
    <PostProcessorTree>
        <PostProcessorSequence>
            <PostProcessor module="MatFileWriter">
                <Filename>../data/PostProcessorTreeUnitTest_Channel1.dat</Filename>
            </PostProcessor>
        </PostProcessorSequence>
        <PostProcessorSequence>
            <PostProcessor module="MatFileWriter">
                <Filename>../data/PostProcessorTreeUnitTest_Channel2.dat</Filename>
            </PostProcessor>
        </PostProcessorSequence>
        <PostProcessorSequence>
            <PostProcessorSequence>
                <PostProcessor module="Decimator">
                    <Factor>2</Factor>
                </PostProcessor>
                <PostProcessor module="MatFileWriter">
                    <Filename>../data/PostProcessorTreeUnitTest_Channel3a.dat</Filename>
                </PostProcessor>
            </PostProcessorSequence>
            <PostProcessorSequence>
                <PostProcessor module="Decimator">
                    <Factor>8</Factor>
                </PostProcessor>
                <PostProcessor module="MatFileWriter">
                    <Filename>../data/PostProcessorTreeUnitTest_Channel3b.dat</Filename>
                </PostProcessor>
            </PostProcessorSequence>
        </PostProcessorSequence>
        <PostProcessorSequence>
            <PostProcessor module="MatFileWriter">
                <Filename>../data/PostProcessorTreeUnitTest_Channel4.dat</Filename>
            </PostProcessor>
        </PostProcessorSequence>
    </PostProcessorTree>
    """
    settings = parseString(settings)
    ppt = PostProcessorTree(settings.getElementsByTagName("PostProcessorTree")[0],None)
    print ppt.ppt
    print ppt.GetNumSequences()

    # Generate some raw data
    sampleRate = 192
    rawBuffer = numpy.zeros((ppt.GetNumSequences()*sampleRate), dtype=numpy.int16)
    for i in range(ppt.GetNumSequences()):
        rawBuffer[(sampleRate*i):(sampleRate*(i+1))] = i*numpy.ones((sampleRate), dtype=numpy.int16)

    # Break the raw data up into channel data
    data = []
    for i in range(ppt.GetNumSequences()):
        data.append(numpy.frombuffer(rawBuffer, numpy.int16, sampleRate, sampleRate*i*2))

    # Process the channel data
    ppt.Process([data, [datetime.now(), [0, 0, 0], 'GPS Info']])
