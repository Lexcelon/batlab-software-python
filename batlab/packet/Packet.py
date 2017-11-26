import logging
import math

# Holds information related to usb packets
class Packet:
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
        '''deprecated'''
        for i in range(0,4):
            self.R[i] = Rlist[i]
            self.B[i] = Blist[i]
    def value(self):
        if(self.type == 'RESPONSE'):
            return self.data
        else:
            li = [self.mode,self.status,self.temp,self.current,self.voltage]
            return li
    def asvoltage(self):
        if(self.data & 0x8000): # the voltage can be negative
            self.data = -0x10000 + self.data
        flt = float(self.data * 4.5 / 2**15)
        return flt
    def asvcc(self):
        return 2**15 * 4.096 / self.data
    def asfreq(self):
        return self.data * (10000.0 / 256.0)
    def asioff(self):
        return self.data / 128.0
    def assetpoint(self):
        return self.data / 128.0
    def asmagdiv(self):
        return 2.0 / (2 ** self.data)
    def asmode(self):
        try:
            return MODE_LIST[self.data]
        except:
            return 'MODE_UNKNOWN: ' + str(self.data)
    def aserr(self):
        for i in range(0,6):
            if self.data & (1 << i):
                return ERR_LIST[i]
        return 'ERR_NONE'
    def astemperature(self):
        Rdiv = self.R[self.namespace]
        R = Rdiv / ((2**15 / self.data)-1)
        To = 25 + 273.15
        Ro = 10000
        B = self.B[self.namespace] # 3380
        Tinv = (1 / To) + (math.log(R/Ro) / B)
        T = (1 / Tinv) - 273.15
        T = (T * 1.8) + 32
        return T
    def astemperature(self,Rlist,Blist):
        Rdiv = Rlist[self.namespace]
        R = Rdiv / ((2**15 / self.data)-1)
        To = 25 + 273.15
        Ro = 10000
        B = Blist[self.namespace] # 3380
        Tinv = (1 / To) + (math.log(R/Ro) / B)
        T = (1 / Tinv) - 273.15
        T = (T * 1.8) + 32
        return T
    def astemperature_c(self,Rlist,Blist):
        Rdiv = Rlist[self.namespace]
        R = Rdiv / ((2**15 / self.data)-1)
        To = 25 + 273.15
        Ro = 10000
        B = Blist[self.namespace] # 3380
        Tinv = (1 / To) + (math.log(R/Ro) / B)
        T = (1 / Tinv) - 273.15
        return T
    def ascurrent(self):
        if(self.data & 0x8000): # the current can be negative
            self.data = -0x10000 + self.data
        return self.data * 4.096 / 2**15
    def print_packet(self):
        if(self.type == 'RESPONSE'):
            if self.write == True:
                logging.info('Wrote: Cell '+str(self.namespace)+', Addr '+"{0:#4X}".format(self.addr & 0x7F))
            else:
                logging.info('Read: Cell '+str(self.namespace)+', Addr '+"{0:#4X}".format(self.addr & 0x7F)+': '+str(self.data))
    def display(self):
        if(self.type == 'RESPONSE'):
            if self.write == True:
                print('Wrote: Cell '+str(self.namespace)+', Addr '+"{0:#4X}".format(self.addr & 0x7F))
            else:
                print('Read: Cell '+str(self.namespace)+', Addr '+"{0:#4X}".format(self.addr & 0x7F)+': '+str(self.data))
