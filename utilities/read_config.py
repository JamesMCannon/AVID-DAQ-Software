'''
Created on Apr 1, 2011

@author: Ryan

Functions to read parameters from xml config file
Assume config = parse(setting_file_string)

'''
def GetElemVal(config,tag,default,zero):

    elements = config.getElementsByTagName(tag)
    if not elements:
        if default is not None:
            return default
        return zero

    child = elements[0].firstChild
    if child is None:
        return zero
    else:
        return child.data  


def GetIntElemVal(config, tag, default = None):
    return int(GetElemVal(config,tag,default,0))

def GetStrElemVal(config, tag,default=None):
    return str(GetElemVal(config,tag,default,'.'))

def GetDblElemVal(config, tag,default=None):
    return float(GetElemVal(config,tag,default,0.0))
    

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
    
    c = parseString(settings)
    print GetStrElemVal(c,'station_id','X')
    print GetIntElemVal(c,'Duration')
    print GetDblElemVal(c,'random',1)
    print GetStrElemVal(c,'random')