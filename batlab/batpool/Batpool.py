import threading
import logging
import serial.tools.list_ports
from time import sleep

try:
    # Python 2.x
    import Queue as queue
except ImportError:
    # Python 3.x
    import queue as queue

from batlab import logger, settings, batlab

# Manage a pool of connected batlabs by maintaining a list of plugged-in systems
class Batpool:
    def __init__(self):
        self.msgqueue = queue.Queue()
        self.batpool = dict()
        self.batactive = ''
        self.quitevt = threading.Event()
        thread = threading.Thread(target=self.batpool_mgr)
        thread.daemon = True
        thread.start()
        self.logger = logger.Logger()
        self.settings = settings.Settings()

    def get_ports(self):
        portinfos = serial.tools.list_ports.comports()
        ports = []
        for portinfo in portinfos:
            logging.info(portinfo)
            logging.info(portinfo.device + ' ' + str(portinfo.vid) + ' ' + str(portinfo.pid))
            if(portinfo.vid == 0x04D8 and portinfo.pid == 0x000A):
                logging.info("found Batlab on "+portinfo.device)
                ports.append(portinfo.device)
        return ports
        
    def batpool_mgr(self):
        while(True):
            portlist = self.get_ports()
            for port in portlist:
                if port not in self.batpool:
                    self.batpool[port] = batlab.Batlab(port,self.logger,self.settings)
                    self.msgqueue.put('Batlab on ' + port + ' connected')
                    if self.batactive == '':
                        self.batactive = port
                        self.msgqueue.put('Batlab on ' + port + ' set as the Active Batlab')
            for port in list(self.batpool.keys()):
                if port not in portlist:
                    self.batpool[port].disconnect()
                    del self.batpool[port]
                    self.msgqueue.put('Batlab on ' + port + ' disconnected')
            if self.quitevt.is_set():
                for port in list(self.batpool.keys()):
                    self.batpool[port].disconnect()
                    del self.batpool[port]
                return
            sleep(0.5)
            
    def active_exists(self):
        if self.batactive == '':
            logging.info('No Batlab Currently Set As Active')
            return False
        if self.batactive in self.batpool:
            return True
        else:
            logging.info('Batlab on ' + self.batactive + ' not found')
            return False
            
    def quit(self):
        self.quitevt.set() #tries to tell all of the Batlabs to stop the tests
        sleep(0.5)