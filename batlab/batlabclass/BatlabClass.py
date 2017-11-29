from batlab.constants import *
import batlab.channel
import batlab.packet

import serial
from time import sleep
import datetime
import os
import re
import logging
import threading

try:
    # Python 2.x
    import Queue as queue
    from urllib2 import urlopen
except ImportError:
    # Python 3.x
    import queue as queue
    from urllib.request import urlopen

class Batlab:
    """Holds an instance of one Batlab.

    The class represents one 'Batlab' unit connected over the USB serial port. The batpool class automatically creates the ``batlab`` instances when a Batlab is plugged in, and destroyed once unplugged. If a Batlab instance is supplied with a port name on creation, it will automatically connect to the port. Otherwise, the user will need to call the ``connect`` method.

    Attributes:
        port: Holds serial port name
        is_open: Corresponds to pyserial ``is_open``
        B: List of 'B' temperature calibration constants for each cell
        R: List of 'R' temperature calibration constants for each cell
        logger: Logger object that handles file IO
        settings: Settings object that contains test settings loaded from a JSON file
        channel[4]: 4-list of ``Channel`` objects. Each channel can manage a test run on it.
    """
    def __init__(self,port=None,logger=None,settings=None):
        self.sn = ''
        self.ver = ''
        self.port = port
        self.is_open = False
        self.qstream = queue.Queue() # Queue of stream packets
        self.qresponse = queue.Queue() # Queue of response packets
        self.killevt = threading.Event()
        self.B = [3380,3380,3380,3380]
        self.R = [10000,10000,10000,10000]
        self.setpoints = [256,256,256,256]
        self.logger = logger
        self.settings = settings
        self.critical_write = threading.Lock()
        self.critical_read = threading.Lock()
        self.critical_section = threading.Lock()
        self.connect()
        self.channel = [batlab.channel.Channel(self,0), batlab.channel.Channel(self,1), batlab.channel.Channel(self,2), batlab.channel.Channel(self,3)]

    def connect(self):
        """Connects to serial port in ``port`` variable. Spins off a receiver thread to receive incoming packets and add them to a message queue."""
        while True:
            try:
                self.ser = serial.Serial(None,38400,timeout=2,writeTimeout=0)
                self.ser.port = self.port
                self.ser.close()
                self.ser.open()
            except:
                logging.warning("Could not connect to port")
                return -1
            break
        self.is_open = self.ser.is_open
        thread = threading.Thread(target=self.thd_read) #start receiver thread
        thread.daemon = True
        thread.start()
        if self.read(0x05,0x01).value() == 257: #then we're not in the bootloader
            # self.write(UNIT,SETTINGS,SET_TRIM_OUTPUT)  -- no longer do this because it is buggy in V3 Firmware.
            self.write(UNIT,SETTINGS,0)
            self.R[0] = self.read(0x00,0x16).data
            self.R[1] = self.read(0x01,0x16).data
            self.R[2] = self.read(0x02,0x16).data
            self.R[3] = self.read(0x03,0x16).data
            self.B[0] = self.read(0x00,0x17).data
            self.B[1] = self.read(0x01,0x17).data
            self.B[2] = self.read(0x02,0x17).data
            self.B[3] = self.read(0x03,0x17).data
            self.setpoints[0] = self.read(0x00,CURRENT_SETPOINT).data
            self.setpoints[1] = self.read(0x01,CURRENT_SETPOINT).data
            self.setpoints[2] = self.read(0x02,CURRENT_SETPOINT).data
            self.setpoints[3] = self.read(0x03,CURRENT_SETPOINT).data
            a = self.read(0x04,0x00).data
            b = self.read(0x04,0x01).data
            self.sn = str(a + b*65536)
            self.ver = str(self.read(0x04,0x02).data)
        else:
            logging.info("The Batlab is in the bootloader")

    def disconnect(self):
        """Gracefully closes serial port and kills reader thread."""
        self.killevt.set()
        self.ser.close()

    def set_port(self,port):
        try:
            self.ser.port = port
            self.connect()
            return 1
        except:
            return 0

    def read(self,namespace,addr):
        """Queries a Batlab register specified by the given namespace and register address. The communication architecture spec with all of the namespace and register names, functions, and values can be found in the Batlab Programmer's User Manual.

        Returns:
            A ``packet`` instance containing the read data.
        """
        if not (namespace in NAMESPACE_LIST):
            print("Namespace Invalid")
            return None
        try:
            with self.critical_read:
                q = batlab.packet.Packet()
                outctr = 0
                while(True):
                    try:
                        self.ser.write((0xAA).to_bytes(1,byteorder='big'))
                        self.ser.write(namespace.to_bytes(1,byteorder='big'))
                        self.ser.write(addr.to_bytes(1,byteorder='big'))
                        self.ser.write((0x00).to_bytes(1,byteorder='big'))
                        self.ser.write((0x00).to_bytes(1,byteorder='big'))
                        self.ser.flush()
                        ctr = 0
                        while(self.qresponse.qsize() == 0 and ctr < 50):
                            sleep(0.001)
                            ctr = ctr + 1
                        while(self.qresponse.qsize() > 0):
                            q = self.qresponse.get()
                        if( (q.addr == addr and q.namespace == namespace) ): #or outctr > 20 ):
                            return q
                        if outctr > 50:
                            q.valid = False
                            return q
                        outctr = outctr + 1
                    except:
                        continue
        except:
            return None

    def write(self,namespace,addr,value):
        """Writes the value ``value`` to the register address ``addr`` in namespace ``namespace``. This is the general register write function for the Batlab.

        Returns:
            A 'write' packet.
        """
        if not (namespace in NAMESPACE_LIST):
            print("Namespace Invalid")
            return None
        if value > 65535 or value < -65535:
            print("Invalid value: 16 bit value expected")
            return None
        if(value & 0x8000): #convert large numbers into negative numbers because the to_bytes call is expecting an int16
            value = -0x10000 + value
        # patch for firmware < 3 ... current compensation bug in firmware, so moving the control loop to software.
        # we do this by now keeping track of the setpoint in software, and then the control loop tweaks the firmware setpoint
        if addr == CURRENT_SETPOINT and namespace < 4:
            if value > 575: #maximum value to write to this register
                value = 575
            if value < 0:
                value = 0
            self.setpoints[namespace] = value
        # make sure we cant turn on the current compensation control loop in firmware
        if addr == SETTINGS and namespace == UNIT:
            value &= ~0x0003

        try:
            with self.critical_write:
                q = None
                outctr = 0
                namespace = int(namespace)
                addr = int(addr)
                value = int(value)
                while(True):
                    try:
                        self.ser.write((0xAA).to_bytes(1,byteorder='big'))
                        self.ser.write(namespace.to_bytes(1,byteorder='big'))
                        self.ser.write((addr | 0x80).to_bytes(1,byteorder='big'))
                        self.ser.write(value.to_bytes(2, byteorder='little',signed=True))
                        self.ser.flush()
                        ctr = 0
                        while(self.qresponse.qsize() == 0 and ctr < 50):
                            sleep(0.001)
                            ctr = ctr + 1
                        while(self.qresponse.qsize() > 0):
                            q = self.qresponse.get()
                        if( q.addr == addr and q.namespace == namespace ):
                            return q
                        if( outctr > 20 ):
                            q.valid = False
                            return q
                        outctr = outctr + 1
                    except:
                        continue
        except:
            return None

    def get_stream(self):
        """Retrieve stream packet from queue."""
        q = None
        while self.qstream.qsize() > 0:
            q = self.qstream.get()
        return q

    # Macros
    def set_current(self,cell,current):
        """A macro for setting the CURRENT_SETPOINT to a certain current for a given cell."""
        self.write(cell,CURRENT_SETPOINT,int((current/5.0)*640))
        
    def sn(self):
        a = self.read(UNIT,0x00).data
        b = self.read(UNIT,0x01).data
        return a + b*65536
    
    def ver(self):
        return self.read(0x04,0x02).data
    
    def impedance(self,cell):
        """A macro for taking an impedance measurement on a particular cell."""
        mode = self.read(cell,MODE).data #get previous state
        # start impedance measurment
        self.write(cell,MODE,MODE_IMPEDANCE)
        sleep(2)
        # collect results
        self.write(UNIT,LOCK,LOCK_LOCKED)
        imag = self.read(cell,CURRENT_PP).ascurrent()
        vmag = self.read(cell,VOLTAGE_PP).asvoltage()
        self.write(UNIT,LOCK,LOCK_UNLOCKED)
        z = vmag / imag
        if mode == MODE_DISCHARGE or mode == MODE_CHARGE or mode == MODE_IDLE or mode == MODE_IMPEDANCE or mode == MODE_STOPPED or mode == MODE_NO_CELL or mode == MODE_BACKWARDS:
            self.write(cell,MODE,mode) #restore previous state
            nowmode = self.read(cell,MODE)
            while nowmode == MODE_IMPEDANCE and mode != MODE_IMPEDANCE:
                self.write(cell,MODE,mode) #restore previous state
                nowmode = self.read(cell,MODE)

        return z

    def firmware_bootload(self,filename):
        """Writes the firmware image given by the specified filename to the Batlab. This may take a few minutes."""
        # Check to make sure image is at least the right size
        try:
            with open(filename, "rb") as f:
                sz = os.path.getsize(f.name)
                if not (sz == 15360):
                    print("Image filesize of",sz,"not allowed")
                    return False
        except:
            print("Could not open file")
            return False
        # command the Batlab to enter the bootloader
        print("Entering Bootloader")
        self.write(UNIT,BOOTLOAD,0x0000)
        sleep(2)
        # load the image onto the batlab
        with open(filename, "rb") as f:
            byte = f.read(1)
            ctr = 0x0400
            while byte:
                self.write(BOOTLOADER,BL_ADDR,int(ctr))
                self.write(BOOTLOADER,BL_DATA,int(ord(byte)))
                bb = self.read(BOOTLOADER,BL_DATA).value()
                if(bb != int(ord(byte))):
                    logging.warning("Data Mismatch. Trying again")
                    continue
                print(str(ctr - 0x03FF) + " of 15360: " + str(bb) )
                ctr = ctr + 1
                byte = f.read(1)
        # attempt to reboot into the new image
        self.write(BOOTLOADER,BL_BOOTLOAD,0x0000)
        sleep(2)
        if(self.read(BOOTLOADER,BL_DATA).value() == COMMAND_ERROR):
            self.sn = int(self.read(UNIT,SERIAL_NUM).value()) + (int(self.read(UNIT,DEVICE_ID).value()) << 16)
            print("Connected to Batlab " + str(self.sn))
            fw = int(self.read(UNIT,FIRMWARE_VER).value())
            print("Firmware Version " + str(fw))
            return True
        else:
            print("Batlab still in Bootloader -- Try again")
            return False

    def firmware_check(self,flag_download):
        """Checks GitHub for the latest firmware version, and downloads it if ``flag_download`` is True.
        
        Returns:
            A 2-list: [version, filename].
        """
        # Download latest version and get version number
        urlpath =urlopen('https://github.com/Lexcelon/batlab-firmware-measure/releases/latest/')
        string = urlpath.read().decode('utf-8')
        pattern = re.compile('/[^/]*\.bin"') #the pattern actually creates duplicates in the list
        filelist = pattern.findall(string)
        filename = filelist[0]
        versionlist = re.findall(r'\d+', filename)
        version = int(versionlist[0])
        pattern = re.compile('".*\.bin"') #the pattern actually creates duplicates in the list
        filelist2 = pattern.findall(string)
        filename2 = filelist2[0]
        filename2=filename2[:-1]
        filename2=filename2[1:]
        filename=filename[:-1]
        filename=filename[1:]
        if flag_download == True:
            remotefile = urlopen('https://github.com' + filename2)
            localfile = open(filename,'wb')
            localfile.write(remotefile.read())
            localfile.close()
            remotefile.close()
        return [version,filename]

    def firmware_update(self):
        """Checks if the firmware on the Batlab is outdated, and updates the firmware if it needs updating. This may take several minutes."""
        version,filename = self.firmware_check(True)
        loadedver = self.read(UNIT,FIRMWARE_VER).data
        print("Latest Version is",version,". Current version is",loadedver)
        if(version > loadedver):
            print("Initiating Firmware Update")
            sleep(2)
            self.firmware_bootload(filename)
        else:
            print("Firmware is up to date.")

    # Reading thread - parses incoming packets and adds them to queues
    def thd_read(self):
        while True:
            if self.killevt.is_set(): #stop the thread if the batlab object goes out of scope
                return
            val = None
            try:
                val = self.ser.read()
            except:
                return
            if(val):
                inbuf = []
                ctr = 0
                byte = ord(val)
                if(byte == 0xAA): #Command Response Byte 1: 0xAA
                    while (len(inbuf) < 4 and ctr < 20):
                        for b in self.ser.read():
                            inbuf.append(b)
                        ctr = ctr + 1
                    if ctr == 20:
                        continue
                    p = batlab.packet.Packet()
                    p.timestamp = datetime.datetime.now()
                    p.type = 'RESPONSE'
                    p.namespace = inbuf[0]
                    if((inbuf[1] & 0x80)): #Command Response Byte 3:  w/~r + addr
                        p.write = True
                    p.addr = inbuf[1] & 0x7F
                    p.data = inbuf[2] + inbuf[3]*256 #data payload
                    self.qresponse.put(p) #Add the packet to the queue
                    p.print_packet()
                elif(byte == 0xAF): #stream packet Byte 1: 0xAF
                    while len(inbuf) < 12 and ctr < 20:
                        for b in self.ser.read():
                            inbuf.append(b)
                        ctr = ctr + 1
                    if ctr == 20:
                        continue
                    p = batlab.packet.Packet()
                    p.timestamp = datetime.datetime.now()
                    p.namespace = inbuf[0]
                    if(inbuf[1] == 0):
                        p.type = 'STREAM'
                        p.mode = inbuf[2] + inbuf[3] * 256
                        p.status = inbuf[4] + inbuf[5] * 256
                        p.temp = inbuf[6] + inbuf[7] * 256
                        p.current = inbuf[8] + inbuf[9] * 256
                        p.voltage = inbuf[10] + inbuf[11] * 256
                    self.qstream.put(p) #Add the packet to the queue
                    p.print_packet()
                else:
                    logging.warning("<<thdBatlab:Packet Loss Detected>>")
