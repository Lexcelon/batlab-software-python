from batlab.constants import *
from batlab import channel, packet

import serial
import serial.tools.list_ports
from time import sleep, ctime, time
import datetime
import sys
import math
import os
import json
import traceback
import re
import logging
import threading

is_python2 = sys.version[0] == '2'

if is_python2:
    import Queue as queue
    from urllib2 import urlopen
else:
    import queue as queue
    from urllib.request import urlopen

def ascharge(data):
    return ((6 * (data / 2**15) ) * 4.096 / 9.765625)

# Holds an instance of 1 Batlab. Pass in a COM port
class Batlab:
    def __init__(self,port=None,logger=None,settings=None):
        self.sn = ''
        self.ver = ''
        self.port = port
        self.is_open = False
        self.qstream = queue.Queue()   #Queue of stream packets
        self.qresponse = queue.Queue() #Queue of response packets
        self.killevt = threading.Event()
        self.B = [3380,3380,3380,3380]
        self.R = [10000,10000,10000,10000]
        self.logger = logger
        self.settings = settings
        self.critical_write = threading.Lock()
        self.critical_read = threading.Lock()
        self.connect()
        self.channel = [channel.Channel(self,0), channel.Channel(self,1), channel.Channel(self,2), channel.Channel(self,3)]

    def connect(self):
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
            self.write(UNIT,SETTINGS,SET_TRIM_OUTPUT)
            self.R[0] = self.read(0x00,0x16).data
            self.R[1] = self.read(0x01,0x16).data
            self.R[2] = self.read(0x02,0x16).data
            self.R[3] = self.read(0x03,0x16).data
            self.B[0] = self.read(0x00,0x17).data
            self.B[1] = self.read(0x01,0x17).data
            self.B[2] = self.read(0x02,0x17).data
            self.B[3] = self.read(0x03,0x17).data
            a = self.read(0x04,0x00).data
            b = self.read(0x04,0x01).data
            self.sn = str(a + b*65536)
            self.ver = str(self.read(0x04,0x02).data)
        else:
            logging.info("The Batlab is in the bootloader")

    def disconnect(self):
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
        if not (namespace in NAMESPACE_LIST):
            print("Namespace Invalid")
            return None
        try:
            with self.critical_read:
                q = packet.Packet()
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
        if not (namespace in NAMESPACE_LIST):
            print("Namespace Invalid")
            return None
        if value > 65535 or value < -65535:
            print("Invalid value: 16 bit value expected")
            return None
        if(value & 0x8000): #convert large numbers into negative numbers because the to_bytes call is expecting an int16
            value = -0x10000 + value

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

    # Retrieve stream packet from queue
    def get_stream(self):
        q = None
        while self.qstream.qsize() > 0:
            q = self.qstream.get()
        return q

    # Macros
    def set_current(self,cell,current):
        self.write(cell,CURRENT_SETPOINT,int((current/5.0)*640))
    def sn(self):
        a = self.read(UNIT,0x00).data
        b = self.read(UNIT,0x01).data
        return a + b*65536
    def ver(self):
        return self.read(0x04,0x02).data
    def impedance(self,cell):
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
                    p = packet.Packet()
                    p.timestamp = datetime.datetime.now()
                    p.type = 'RESPONSE'
                    p.namespace = inbuf[0]
                    if((inbuf[1] & 0x80)):       #Command Response Byte 3:  w/~r + addr
                        p.write = True
                    p.addr = inbuf[1] & 0x7F
                    p.data = inbuf[2] + inbuf[3]*256  #data payload
                    self.qresponse.put(p)                     #Add the packet to the queue
                    p.print_packet()
                elif(byte == 0xAF): #stream packet Byte 1: 0xAF
                    while len(inbuf) < 12 and ctr < 20:
                        for b in self.ser.read():
                            inbuf.append(b)
                        ctr = ctr + 1
                    if ctr == 20:
                        continue
                    p = packet.Packet()
                    p.timestamp = datetime.datetime.now()
                    p.namespace = inbuf[0]
                    if(inbuf[1] == 0):
                        p.type = 'STREAM'
                        p.mode = inbuf[2] + inbuf[3] * 256
                        p.status = inbuf[4] + inbuf[5] * 256
                        p.temp = inbuf[6] + inbuf[7] * 256
                        p.current = inbuf[8] + inbuf[9] * 256
                        p.voltage = inbuf[10] + inbuf[11] * 256
                    self.qstream.put(p)                     #Add the packet to the queue
                    p.print_packet()
                else:
                    logging.warning("<<thdBatlab:Packet Loss Detected>>")