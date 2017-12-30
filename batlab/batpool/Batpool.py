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

import batlab.logger
import batlab.settings
import batlab.batlabclass
import traceback

# Manage a pool of connected batlabs by maintaining a list of plugged-in systems
class Batpool:
    """Manage a pool of connected batlabs by maintaining a list of plugged-in systems.

    The ``batpool`` class spins up a thread that manages connections to Batlab devices connected over USB. It monitors the USB ports and maintains a dict of connected Batlabs called the ``batpool``. The contents of this variable are Batlab class instances and they are looked up in the dict by their Serial Port addresses. Pyserial is used in the batlab to manage connections to the computer's serial interface.

    A second variable, ``batactive`` is used to store the serial port name of the currently active Batlab, that is, the Batlab to which commands are currently directed.

    Attributes:
        msgqueue: Queue of string messages describing plug-unplug events
        batpool: Dictionary of Batlab instances by Serial Port Addresses (e.g. COM5)
        batactive: Serial port of active Batlab
        logger: A Logger object that manages access to a log filename
        settings: A Settings object that contains test settings imported from a JSON file
    """
    def __init__(self):
        self.msgqueue = queue.Queue()
        self.batpool = dict()
        self.batlocks = dict()
        self.batactive = ''
        self.quitevt = threading.Event()
        thread = threading.Thread(target=self.batpool_mgr)
        thread.daemon = True
        thread.start()
        logging.info("batpool:",thread.getName())
        self.logger = batlab.logger.Logger()
        self.settings = batlab.settings.Settings()

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
            try:
                portlist = self.get_ports()
                for port in portlist:
                    if port not in self.batpool:
                        self.batlocks[port] = threading.Lock()
                        self.batpool[port] = batlab.batlabclass.Batlab(port,self.logger,self.settings)
                        while(self.batpool[port].initialized == False):
                            sleep(0.01)
                        if self.batpool[port].error == True: #something went wrong. delete this instance and try again later
                            self.batpool[port].disconnect()
                            del self.batpool[port]
                            del self.batlocks[port]
                            print("Batpool - Batlab init error. Deleting instance")
                            continue
                        self.msgqueue.put('Batlab on ' + port + ' connected')
                        if self.batactive == '':
                            self.batactive = port
                            self.msgqueue.put('Batlab on ' + port + ' set as the Active Batlab')
                for port in list(self.batpool.keys()):
                    if port not in portlist:
                        self.batpool[port].disconnect()
                        with self.batlocks[port]:
                            del self.batpool[port]
                        del self.batlocks[port]
                        self.msgqueue.put('Batlab on ' + port + ' disconnected')
                if self.quitevt.is_set():
                    for port in list(self.batpool.keys()):
                        with self.batlocks[port]:
                            self.batpool[port].disconnect()
                            del self.batpool[port]
                        del self.batlocks[port]
                    return
                sleep(0.5)
            except:
                logging.info('Exception on Batpool...Continuing')
                traceback.print_exc()
                continue

    def active_exists(self):
        """Returns True if the Batlab described by the ``batactive`` port is connected."""
        if self.batactive == '':
            logging.info('No Batlab Currently Set As Active')
            return False
        if self.batactive in self.batpool:
            return True
        else:
            logging.info('Batlab on ' + self.batactive + ' not found')
            return False

    def quit(self):
        self.quitevt.set() # tries to tell all of the Batlabs to stop the tests
        sleep(0.5)
