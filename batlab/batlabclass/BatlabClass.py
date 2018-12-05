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
import math
import traceback

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
        self.initialized = False
        self.error = False
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
        self.channel = None
        self.bootloader = False
        if self.connect() == 0:
            self.channel = [batlab.channel.Channel(self,0), batlab.channel.Channel(self,1), batlab.channel.Channel(self,2), batlab.channel.Channel(self,3)]
        else:
            self.error = True
        self.initialized = True

    def connect(self):
        """Connects to serial port in ``port`` variable. Spins off a receiver thread to receive incoming packets and add them to a message queue."""
        try:
            self.ser = serial.Serial(None,38400,timeout=2,writeTimeout=0)
            self.ser.port = self.port
            self.ser.close()
            self.ser.open()
        except:
            logging.warning("Could not connect to port")
            return -1
        self.is_open = self.ser.is_open
        thread = threading.Thread(target=self.thd_read) #start receiver thread
        thread.daemon = True
        thread.start()
        #print("batlab:",thread.getName())
        if self.read(0x05,0x01).value() == 257: #then we're not in the bootloader
            # self.write(UNIT,SETTINGS,SET_TRIM_OUTPUT)  -- no longer do this because it is buggy in V3 Firmware.
            self.write(UNIT,WATCHDOG_TIMER,WDT_RESET) #do this so the watchdog is happy during these initialization commands
            self.write(CELL0,MODE,MODE_IDLE)
            self.write(CELL1,MODE,MODE_IDLE)
            self.write(CELL2,MODE,MODE_IDLE)
            self.write(CELL3,MODE,MODE_IDLE)
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
            if(math.isnan(a) or math.isnan(b)):
                logging.warning("Serial Number retrieval failed. Trying Again")
                a = self.read(0x04,0x00).data
                b = self.read(0x04,0x01).data
            
            self.ver = str(self.read(0x04,0x02).data)
            
            if int(self.ver) > 3:
                self.write_verify(UNIT,SETTINGS,SET_WATCHDOG_TIMER) #this setting is only meaningful if the firmware version is 4 or greater.
                self.write(UNIT,WATCHDOG_TIMER,WDT_RESET)
                
        else:
            logging.info("The Batlab is in the bootloader")
            self.bootloader = True
        return 0

    def disconnect(self):
        """Gracefully closes serial port and kills reader thread."""
        if self.channel is not None:
            for ch in self.channel:
                ch.killevt.set()
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
        q = batlab.packet.Packet()
        if not (namespace in NAMESPACE_LIST):
            print("Namespace Invalid")
            q.valid = False
            q.data = float('nan')
            return q
        if (not namespace == 0x05) and self.bootloader == True:
            print("Reg Read not vaild when Batlab is in Bootloader")
            q.valid = False
            q.data = float('nan')
            return q
        try:
            with self.critical_read:
                outctr = 0
                exceptctr = 0
                while(self.ser.is_open):
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
                            print("<<thdBatlab:read fail - flushing write buffer with packet start code")
                            self.ser.write((0xAA).to_bytes(1,byteorder='big'))
                            self.ser.write((0xAA).to_bytes(1,byteorder='big'))
                            self.ser.write((0xAA).to_bytes(1,byteorder='big'))
                            self.ser.write((0xAA).to_bytes(1,byteorder='big'))
                            self.ser.write((0xAA).to_bytes(1,byteorder='big'))
                            q.valid = False
                            q.data = float('nan')
                            return q
                        outctr = outctr + 1
                    except:
                        if exceptctr > 20:
                            #print('Exception on Batlab read...Continuing')
                            #traceback.print_exc()
                            break
                        exceptctr += 1
                        sleep(0.005)
                        continue
                q.valid = False
                q.data = float('nan')
                return q
        except:
            q.valid = False
            q.data = float('nan')
            return q

    def write(self,namespace,addr,value):
        """Writes the value ``value`` to the register address ``addr`` in namespace ``namespace``. This is the general register write function for the Batlab.

        Returns:
            A 'write' packet.
        """
        failresponse = batlab.packet.Packet()
        failresponse.valid = False
        failresponse.data = float('nan')
        if not (namespace in NAMESPACE_LIST):
            print("Namespace Invalid")
            return failresponse
        if (not namespace == 0x05) and self.bootloader == True:
            print("Write not vaild when Batlab is in Bootloader")
            return failresponse
        if(math.isnan(value)):
            print("Write Value invalid - nan")
            return failresponse
        if value > 65535 or value < -65535:
            print("Invalid value: 16 bit value expected")
            return failresponse
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
                exceptctr = 0
                namespace = int(namespace)
                addr = int(addr)
                value = int(value)
                while(self.ser.is_open):
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
                            q.data = float('nan')
                            return q
                        outctr = outctr + 1
                    except:
                        if exceptctr > 20:
                            #print('Exception on Batlab write...Continuing')
                            #traceback.print_exc()
                            break
                        exceptctr += 1
                        sleep(0.005)
                        continue
                q.valid = False
                q.data = float('nan')
                return q
        except:
            return failresponse
            
    def write_verify(self,namespace,addr,value):
        """Writes the value ``value`` to the register address ``addr`` in namespace ``namespace``. Reads the register back and compares the result, Retries if they do not match.

        Returns:
            Returns True if results match, Returns False if timeout condition occurred
        """

        #mimick what the write function does to tweak the current setpoint so we don't have an issue here.
        if addr == CURRENT_SETPOINT and namespace < 4:
            if value > 575: #maximum value to write to this register
                value = 575
            if value < 0:
                value = 0
            self.write(namespace,addr,0) #If you are going to change the current setpoint, it is best to first set it back to 0
            sleep(0.01)
        
        #Actually write the value to the register
        self.write(namespace,addr,value)  
        sleep(0.005)        
        
        tmp = self.read(namespace,addr).data
        ctr = 0
        while(not (tmp == value)):
            print(datetime.datetime.now()," - Register Write Error - Retrying",self.sn,namespace,addr,tmp,value)
            #traceback.print_stack()
            sleep(0.015)
            self.write(namespace,addr,value)
            sleep(0.015)
            tmp = self.read(namespace,addr).data
            sleep(0.015)
            ctr += 1
            if (ctr > 10):
                print("Unable to Write Register - CRITICAL FAILURE")
                return False
        return True

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
        
        if mode == MODE_DISCHARGE or mode == MODE_CHARGE or mode == MODE_IDLE or mode == MODE_IMPEDANCE or mode == MODE_STOPPED or mode == MODE_NO_CELL or mode == MODE_BACKWARDS:
            self.write(cell,MODE,mode) #restore previous state
            nowmode = self.read(cell,MODE)
            while nowmode == MODE_IMPEDANCE and mode != MODE_IMPEDANCE:
                self.write(cell,MODE,mode) #restore previous state
                nowmode = self.read(cell,MODE)
        z = 0.0   
        if math.isnan(imag) or math.isnan(vmag):
            z = float('nan')
        elif imag < 0.000001:
            z = 0
        else:
            z = vmag / imag

        return z
    
    def charge(self,cell):
        """A macro for taking a charge measurement that handles the case if the charge register rolls over in between high and low reads"""
        set = self.read(UNIT,SETTINGS).data
        multiplier = 6.0
        if not (set & SET_CH0_HI_RES == 0):
            multiplier = 1.0
        ch = self.read(cell,CHARGEH).data
        cl = self.read(cell,CHARGEL).data
        chp = self.read(cell,CHARGEH).data
        if math.isnan(ch) or math.isnan(cl) or math.isnan(chp):
            return float('nan')
        if chp == ch:
            data = (ch << 16) + cl
            return ((multiplier * data / 2**15 ) * 4.096 / 9.765625)
        cl = self.read(cell,CHARGEL).data
        data = (chp << 16) + cl
        return ((multiplier * data / 2**15 ) * 4.096 / 9.765625)

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
        self.bootloader = True
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
            self.bootloader = False
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
            
    def calibration_recover(self,filename):
        """Method to re-write Non-volatile Memory (Calibration Constants) in case they got erased. supply filename containing 49 rows representing the 49 constants"""
        value_list = []
        try:
            with open(filename, "r") as f:
                for value in f:
                    value_list.append(int(value))
            if len(value_list) != 49:
                print("File was corrupt. Expecting 49 integer values")
                return False    
        except:
            print("File was missing or otherwise could not be read")
            return False
        valctr = 0
        
        
        
        #write the serial number
        sn = value_list[valctr]
        self.write(UNIT,SERIAL_NUM,sn % 65536)
        self.write(UNIT,DEVICE_ID,sn // 65536)
        valctr += 1
        
        #write everything else
        for i in range(0,4):
            self.write(i,CURRENT_CALIB_OFF ,value_list[valctr])
            valctr += 1
            self.write(i,CURRENT_CALIB_SCA ,value_list[valctr])
            valctr += 1
            self.write(i,CURR_LOWV_OFF     ,value_list[valctr])
            valctr += 1
            self.write(i,CURR_LOWV_SCA     ,value_list[valctr])
            valctr += 1
            self.write(i,CURR_LOWV_OFF_SCA ,value_list[valctr])
            valctr += 1
            self.write(i,TEMP_CALIB_R      ,value_list[valctr])
            valctr += 1
            self.write(i,TEMP_CALIB_B      ,value_list[valctr])
            valctr += 1
            self.write(i,CURRENT_CALIB_PP  ,value_list[valctr])
            valctr += 1
            self.write(i,VOLTAGE_CALIB_PP  ,value_list[valctr])
            valctr += 1
            self.write(i,CURR_CALIB_PP_OFF ,value_list[valctr])
            valctr += 1
            self.write(i,VOLT_CALIB_PP_OFF ,value_list[valctr])
            valctr += 1
        self.write(UNIT,VOLT_CH_CALIB_OFF,value_list[valctr])
        valctr += 1
        self.write(UNIT,VOLT_CH_CALIB_SCA,value_list[valctr])
        valctr += 1
        self.write(UNIT,VOLT_DC_CALIB_OFF,value_list[valctr])
        valctr += 1
        self.write(UNIT,VOLT_DC_CALIB_SCA,value_list[valctr])
        valctr += 1


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
