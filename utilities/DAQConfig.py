'''
Created: 4/9/13 JCC: Create class around read_config operations 

Functions to read parameters from xml config file
Assume config = parse(setting_file_string)

'''

from xml.dom.minidom import parse

class DAQConfig:
    
    """
        requires a valid, parsed xml doc
    """
    def __init__(self, settings):

        self.settings = settings
        
    def GetSubTree(self, tag):
        return self.settings.getElementsByTagName(tag)
        
    def GetFirstSubTree(self,tag):
        
        return self.GetSubTree(tag)[0]
        
    def GetSubTreeStrElem(self, tag, elem):
    
        return str(self.GetFirstSubTree(tag).attributes[elem].value)
    
    def GetElemVal(self, tag, default, zero):

        elements = self.settings.getElementsByTagName(tag)
        
        if not elements:
            if default is not None:
                return default
            return zero

        child = elements[0].firstChild
        if child is None:
            return zero
        else:
            return child.data  


    def GetIntElemVal(self, tag, default = None):
        return int(self.GetElemVal(tag, default, 0))

    def GetStrElemVal(self, tag, default=None):
        return str(self.GetElemVal(tag, default, '.'))

    def GetDblElemVal(self, tag, default=None):
        return float(self.GetElemVal(tag, default, 0.0))
    

if __name__ == '__main__':
    
    from xml.dom.minidom import parseString

    # Create the Motorola GPS clock object
    settings = """\
    <PostProcessor module="MatFileWriter">
        <station_id>Test</station_id>
        <DirectoryRoot>.</DirectoryRoot>
        <adc_channel_number>0</adc_channel_number>
        <system_call>Spectrogram\\CreateSpecgramJPG.exe @ .\\latestNS.mat 1 100</system_call>
        <Duration>10</Duration>
    </PostProcessor>
    """
    
    c = DAQConfig(parseString(settings))
    
    print c.GetStrElemVal('station_id','X')
    print c.GetIntElemVal('Duration')
    print c.GetDblElemVal('random',1)
    print c.GetStrElemVal('random')