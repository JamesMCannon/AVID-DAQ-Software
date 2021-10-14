
from serial import SerialException, SerialTimeoutException
from Queue import Full, Empty

__all__ = ['ClockError', 'ClockSkipError', 'ClockQueueFull', 'ClockMsgQueueFull', 'ClockNoDataError', 'ClockInternalError',  'Full', 'Empty']

class ClockError(Exception):
    pass
    
class ClockSkipError(ClockError):
    pass

class ClockQueueFull(ClockError):
    pass
    
class ClockMsgQueueFull(ClockError):
    pass
    
class ClockNoDataError(ClockError):
    pass
    
class ClockInternalError(ClockError):
    pass