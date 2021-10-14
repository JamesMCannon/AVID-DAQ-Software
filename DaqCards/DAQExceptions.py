## Contains all the exceptions used in this module
##  For easy import into parent modules

__all__ = ['DAQError', 'DAQNoDataError', 'DAQInitError', 'DAQStartError', 'DAQStopError', 'DAQSampleError', 'DAQInternalError', 'DAQNotFoundError']

# Exception Classes
class DAQError(Exception):
    pass
    
class DAQNoDataError(DAQError):
    pass

class DAQInitError(DAQError):
    pass
    
class DAQStartError(DAQError):
    pass
    
class DAQStopError(DAQError):
    pass
    
class DAQSampleError(DAQError):
    pass
  
class DAQInternalError(DAQError):
    pass
    
class DAQNotFoundError(DAQError):
    pass