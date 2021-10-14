from multiprocessing import Event, Lock

__all__ = ['STATE_STOP', 'STATE_INIT', 'STATE_RUN', 'STATE_ERR', 'STATE_RST', 'StateFlags']

"""
States defined:

stopped
init
running
error
restart
"""

STATE_STOP = 0
STATE_INIT = 10
STATE_RUN = 30
STATE_ERR = 40
STATE_RST = 50

_states = {
STATE_STOP: 'STATE_STOP',
STATE_INIT: 'STATE_INIT',
STATE_RUN: 'STATE_RUN',
STATE_ERR: 'STATE_ERR',
STATE_RST: 'STATE_RST',
'STATE_STOP': STATE_STOP,
'STATE_INIT': STATE_INIT,
'STATE_RUN': STATE_RUN,
'STATE_ERR': STATE_ERR,
'STATE_RST': STATE_RST
}
    
class StateFlags:



    def __init__(self):
        # Set of flags to denote state of module

        self.state = STATE_STOP
        
        self.num_restarts = 0
        self.num_errors = 0
        
        self.lock = Lock()
        
    def reset(self):
        self.lock.acquire()
        
        self.curr_state = STATE_STOP
        self.num_restarts = 0
        self.num_errors = 0   

        self.lock.release()
    
    def what_state(self):
        # Return string version of state
        return _states.get(self.state, "NaS")
    
    def add_state(self, state_num, state_name):
        _states[state_num] = state_name
        _states[state_name] = state_num 
    
    def is_stopped(self):
        return True if self.state == STATE_STOP else False
    
    def is_init(self):
        return True if self.state == STATE_INIT else False
    
    def is_running(self):
        return True if self.state == STATE_RUN else False
    
    def is_error(self):
        return True if self.state == STATE_ERR else False
    
    def is_resetting(self):
        return True if self.state == STATE_RST else False
    
    def change_state(self, new_state):
        """
        Should:
        Returns true if old state match and successfully changes over to new state
        Returns false if current state does not match old state.

        example
        if self.state() == old_state:
            self.lock.acquire()
            self.state = _states[new_state]
            self.lock.release()
            return True
        return False
        """
        raise NotImplementedError()
        
    def _change_state_to(self, new_state):
        self.lock.acquire()
        self.curr_state = new_state
        self.lock.release()
        
    def __repr__(self):
        return "State: %s" % self.what_state()
