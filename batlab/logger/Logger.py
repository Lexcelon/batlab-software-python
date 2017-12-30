import threading
from time import sleep

try:
    # Python 2.x
    import Queue as queue
except ImportError:
    # Python 3.x
    import queue as queue

class Logger:
    """Manages access to files for writing test log information."""
    
    # cell name,batlab name,channel,timestamp,voltage,current,temperature,impedance,energy,charge
    def __init__(self):
        self.msgqueue = queue.Queue()
        thread = threading.Thread(target=self.thd_logger)
        thread.daemon = True
        thread.start()
        #print("logger:",thread.getName())

    def log(self,logstring,filename):
        """Writes entry 'logstring' into file 'filename'."""
        self.msgqueue.put([logstring,filename])

    def thd_logger(self):
        while(True):
            while(self.msgqueue.qsize() > 0):
                q = self.msgqueue.get()
                logfile = open(q[1],'a+')
                logfile.write(q[0] + '\n')
                logfile.close()
            sleep(0.1)
