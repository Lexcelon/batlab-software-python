import logging
import math
from batlab.constants import *

class Packet:
    """Holds information related to USB packets.
    
    The ``packet`` class contains a command response packet from a Batlab. Information from a batlab register read is returned to the user in a ``packet`` instance. The various methods of the packet instance allow the user to decode the raw register data into useable information.

    Attributes:
        valid: Bool describing if data in the packet can be trusted
        timestamp: Time message was received
        namespace: Namespace of the register's data this packet contains
        addr: Register address
        data: Raw register packet data (int16)
        write: True if this response packet was for a register write
    """
    def __init__(self):
        self.valid = True
        self.timestamp = None
        self.namespace = None
        self.type = None
        self.addr = None
        self.data = None
        self.mode = None
        self.status = None
        self.temp = None
        self.voltage = None
        self.current = None
        self.write = None
        self.R = [1500,1500,1500,1500]
        self.B = [3380,3380,3380,3380]
    def set_temps(Rlist,Blist):
        """Deprecated."""
        for i in range(0,4):
            self.R[i] = Rlist[i]
            self.B[i] = Blist[i]
            
    def value(self):
        """Returns the raw data if the packet is a response packet, or a list of data pieces if the packet is an extended response packet."""
        if(self.type == 'RESPONSE'):
            return self.data
        else:
            li = [self.mode,self.status,self.temp,self.current,self.voltage]
            return li
        
    def asvoltage(self):
        """Represents voltage ``data`` as a floating point voltage."""
        if(math.isnan(self.data)):
            return float(('nan'))
        if(self.data & 0x8000): # the voltage can be negative
            self.data = -0x10000 + self.data
        flt = float(self.data * 4.5 / 2**15)
        return flt
    
    def asvcc(self):
        """Represents vss ``data`` as a floating point voltage."""
        return 2**15 * 4.096 / self.data
    
    def asfreq(self):
        """Represents frequency data in Hz."""
        return self.data * (10000.0 / 256.0)
    
    def asioff(self):
        """Represents register current to floating point Amps."""
        return self.data / 128.0
    
    def assetpoint(self):
        """Represents current setpoint as floating point Amps."""
        return self.data / 128.0
    
    def asmagdiv(self):
        """Represents magdiv register as Ipp."""
        return 2.0 / (2 ** self.data)
    
    def asmode(self):
        """Represents a mode register value as an enum string."""
        try:
            return MODE_LIST[self.data]
        except:
            return 'MODE_UNKNOWN: ' + str(self.data)
        
    def aserr(self):
        """Represents error reg bit field as a string of the error flags."""
        if(math.isnan(self.data)):
            return 'ERR_NONE'
        for i in range(0,len(ERR_LIST)):
            if self.data & (1 << i):
                return ERR_LIST[i]
        return 'ERR_NONE'
    
    def astemperature(self):
        try:
            Rdiv = self.R[self.namespace]
            R = Rdiv / ((2**15 / self.data)-1)
            To = 25 + 273.15
            Ro = 10000
            B = self.B[self.namespace] # 3380
            Tinv = (1 / To) + (math.log(R/Ro) / B)
            T = (1 / Tinv) - 273.15
            T = (T * 1.8) + 32
        except:
            T = float('nan')
        return T
    
    def astemperature(self,Rlist,Blist):
        """Represents temp data as temperature in F.

        Args:
            Rlist: 4 list of 'R' calibration values needed to interpret temp
            Blist: 4 list of 'B' calibration values needed to interpret temp
        """
        try:
            Rdiv = Rlist[self.namespace]
            R = Rdiv / ((2**15 / self.data)-1)
            To = 25 + 273.15
            Ro = 10000
            B = Blist[self.namespace] # 3380
            Tinv = (1 / To) + (math.log(R/Ro) / B)
            T = (1 / Tinv) - 273.15
            T = (T * 1.8) + 32
        
        except:
            T = float('nan')
        return T
    
    def astemperature_c(self,Rlist,Blist):
        """Represents temp data as temperature in C.

        Args:
            Rlist: 4 list of 'R' calibration values needed to interpret temp
            Blist: 4 list of 'B' calibration values needed to interpret temp
        """
        try:
            Rdiv = Rlist[self.namespace]
            R = Rdiv / ((2**15 / self.data)-1)
            To = 25 + 273.15
            Ro = 10000
            B = Blist[self.namespace] # 3380
            Tinv = (1 / To) + (math.log(R/Ro) / B)
            T = (1 / Tinv) - 273.15
        except:
            T = float('nan')
        return T
    
    def ascurrent(self):
        if(math.isnan(self.data)):
            return float(('nan'))
        """Represents current measurement as float current in Amps."""
        if(self.data & 0x8000): # the current can be negative
            self.data = -0x10000 + self.data
        return self.data * 4.096 / 2**15
    
    def print_packet(self):
        if(self.type == 'RESPONSE'):
            if self.write == True:
                logging.info("Wrote: Cell "+str(self.namespace)+", Addr "+"{0:#4X}".format(self.addr & 0x7F))
            else:
                logging.info("Read: Cell "+str(self.namespace)+", Addr "+"{0:#4X}".format(self.addr & 0x7F)+": "+str(self.data))
                
    def display(self):
        """Prints out the basic info about the packet transaction ### charge function."""
        if(self.type == 'RESPONSE'):
            if self.write == True:
                print('Wrote: Cell '+str(self.namespace)+', Addr '+"{0:#4X}".format(self.addr & 0x7F))
            else:
                print('Read: Cell '+str(self.namespace)+', Addr '+"{0:#4X}".format(self.addr & 0x7F)+': '+str(self.data))
