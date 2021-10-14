## Exceptions for Post Processor Tree
##  


__all__ = ['PPTError', 'MatFileWriterError', 'MFWDiskFullError']

class PPTError(Exception):
    pass

# Base exceptions for MatFileWriter
class MatFileWriterError(PPTError):
    pass
    
class MFWDiskFullError(MatFileWriterError):
    pass
