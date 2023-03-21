from time import sleep, ctime, time
from builtins import input
import batlab.batpool
import batlab.func
import batlab.encoder
from batlab.constants import *

bp = batlab.batpool.Batpool()
sleep(1)
bl = bp.batpool[bp.batactive] #get the active batlab object
bl.write(UNIT,SETTINGS,5)
bl.write(0,CURRENT_SETPOINT,batlab.encoder.Encoder(1).assetpoint())
bl.write(0,MODE,MODE_CHARGE)

mode = bl.read(0,MODE).data
while mode != 6:
    print(bl.read(0,VOLTAGE).asvoltage())
    print(bl.read(0,DUTY).data)
    print(bl.read(0,STATUS).data)
    mode = bl.read(0,MODE).data
    print(mode)
    sleep(.01)