from sys import stdout, stderr
from threading import Condition, Timer

__all__ = ['OnePPSSignal']

class OnePPSSignal:
    """
    The OnePPSSignal class implements a software 1 PPS (pulse per second) signal
    that other objects (namely software GPS clocks and DAQ cards) can use for
    synchronization.  This is largely a debug tool.  Normal hardware GPS clock
    and DAQ card classes will not need (and not work with) a OnePPSSignal
    object.
    """

    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self):
        """
        Creates and starts a 1 PPS signal object.
        """
        self.condition = Condition()
        self.running = True
        self.timer = Timer(1.0, self.MainLoop)
        self.timer.start()

    # =======
    # Methods
    # =======
    def Wait(self):
        """
        Blocks until a 1 PPS signal "edge" has occured.
        """
        self.condition.acquire()
        self.condition.wait()
        self.condition.release()

    def Stop(self):
        """
        Stops the 1 PPS signal.
        """
        self.running = False
        stdout.write("1PPS signal stopped, restart program to start again.\r\n")

    def clear(self):
        """
        Resets the 1PPS Signal. There's no actual way to do this, so just do nothing.
        """
        print "Resetting virtual 1PPS clk. Just Kidding."
        
    # ==============
    # Helper Methods
    # ==============
    def MainLoop(self):
        self.condition.acquire()
        self.condition.notifyAll()
        self.condition.release()
        if self.running:
            self.timer = Timer(1.0, self.MainLoop)
            self.timer.start()

# =========
# Unit Test
# =========
if __name__ == "__main__":
    PFI0 = OnePPSSignal()
    for i in range(10):
        PFI0.Wait()
        print "Edge %d asserted." % i
    PFI0.Stop()
