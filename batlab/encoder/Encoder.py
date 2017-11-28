import math

class Encoder:
    """Essentially the opposite of the Packet class. Takes a human-readable measurement or command and converts it to the raw Batlab register value."""
    def __init__(self,data):
        """Creates the instance with the supplied data."""
        self.data = data
        
    def asvoltage(self):
        return int(self.data * 2**15 / 4.5)
    
    def asvcc(self):
        return  int((2**15 * 4.096)  / self.data)
    
    def asfreq(self):
        return int(self.data / (10000.0 / 256.0))
    
    def asioff(self):
        return int(self.data * 128.0)
    
    def assetpoint(self):
        return int((self.data * 128))
    
    def asmagdiv(self):
        return int(1 - math.log2(self.data))
    
    def ascurrent(self):
        return int(self.data * (2**15 - 1) / 4.096)
    
    def aschargel(self):
        return  ((self.data * 9.765625 / 4.096 / 6) * 2**15) & 0xFFFF
    
    def aschargeh(self):
        return  ((self.data * 9.765625 / 4.096 / 6) * 2**15) >> 16
    
    def astemperature(self,Rdiv,B):
        """Represents temperature data as temperature in F.

        Args:
            Rdiv: 'R' calibration value needed to interpret temp
            B: 'B' calibration value needed to interpret temp
        """
        To = 25 + 273.15
        Ro = 10000
        F = (self.data - 32) / 1.8 # F in this case is the temperature in celsius :)
        F = 1/(F + 273.15)
        R = math.exp((F - (1 / To)) * B) * Ro
        if (R > 0 and Rdiv > 0):
            R = (2**15)/(((1/R)*Rdiv) + 1)
        else:
            R = -100 # dummy value
        return int(R)
    
    def c_astemperature(self,Rdiv,B):
        """Represents temperature data as temperature in C.

        Args:
            Rdiv: 'R' calibration value needed to interpret temp
            B: 'B' calibration value needed to interpret temp
        """
    
        To = 25 + 273.15
        Ro = 10000
        F = self.data
        F = 1/(F + 273.15)
        R = math.exp((F - (1 / To)) * B) * Ro
        if (R > 0 and Rdiv > 0):
            R = (2**15)/(((1/R)*Rdiv) + 1)
        else:
            R = -100 # dummy value
        return int(R)
