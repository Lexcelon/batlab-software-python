# calibrates Batlab current measurement against a Keithley 2200-series power supply
# optimizes for minimal absolute error in order to minimize error in capacity measurements

# Requirements: 
#   Keithley I/O Layer (https://www.tek.com/en/support/software/application/850c10)
#   PyVISA (https://pyvisa.readthedocs.io/en/latest/)
#   IMPORTANT: copy of Batlab library obtained from https://github.com/ConorGover/batlab-software-python
#       The original Lexcelon Batlab library has a bug which will corrupt the calibration values.

from time import sleep
import numpy as np
from scipy.optimize import minimize

import batlab.batpool
import batlab.func
import batlab.encoder
from batlab.constants import *

import pyvisa

Fault = Exception

min_current = 1/8
max_current = 3    # This should be the planned discharge current for testing
step = 1/8

# set to "RELATIVE" to optimize for minimal relative error using the least-squares method
# set to "ABSOLUTE" to optimize for minimal absolute error (least absolute deviations)
#   ABSOLUTE will give more accurate capacity measurements
OPTIMIZE_FOR = "ABSOLUTE"

currents = {}

class PowerSupply:
    def __init__(self):
        self.com_port = None
        self.ps = None
        self.rm = pyvisa.ResourceManager()
        try:
            self.list = self.rm.list_resources()
            first3 = ''
            n = 0
            while first3 != 'USB':
                first3 = self.list[n][0:3]
                n += 1
        except:
            raise Fault('Ensure power supply is powered on and connected to computer')
        self.com_port = self.list[n-1]
        self.ps = self.rm.open_resource(self.com_port)
        sleep(0.5)

    def get_current(self):
        if self.ps is None:
            raise Fault('Power supply not initialized')
        current = float(self.ps.query('MEAS:CURR? ch3'))
        return current

ps = PowerSupply()
# disable channels 1 and 2
ps.ps.write('inst:sel ch1')
ps.ps.write('outp:enab 0')
ps.ps.write('inst:sel ch2')
ps.ps.write('outp:enab 0')
# turn on channel 3 at 4V, 4.1A
ps.ps.write('inst:sel ch3')
ps.ps.write('outp:enab 1')
ps.ps.write('volt 4V')
ps.ps.write('curr 4.1A')
ps.ps.write('outp on')
sleep(1)
    
def test_calibration():
    current = min_current
    while current <= max_current:
        bl.write(cell,CURRENT_SETPOINT,batlab.encoder.Encoder(current).assetpoint())

        # wait for Batlab's current feedback loop to stabilize
        prev_duty = 0
        duty = 1
        while duty != prev_duty:
            prev_duty = duty
            duty = bl.read(cell,DUTY).data
            sleep(0.5)

        # make sure Batlab is in discharge mode
        if bl.read(cell,MODE).data != MODE_DISCHARGE:
            print(bl.read(cell,ERROR).aserr())
            raise Fault('Something went wrong ¯\_(ツ)_/¯')
        
        bat_curr_sum = 0
        ps_curr_sum = 0
        for i in range(8):
            bat_curr_sum += bl.read(cell,CURRENT).ascurrent()
            ps_curr_sum += ps.get_current()
            sleep(0.05)
        bat_current = bat_curr_sum / 8
        ps_current = ps_curr_sum / 8
        if OPTIMIZE_FOR == "ABSOLUTE":
            error = (bat_current - ps_current)
            print(f"Batlab says: {bat_current:.3f} A and PS says: {ps_current:.3f} A.   Error: {(error*1000):.0f} mA")
        elif OPTIMIZE_FOR == "RELATIVE":
            error = (bat_current - ps_current) / ps_current
            print(f"Batlab says: {bat_current:.3f} A and PS says: {ps_current:.3f} A.   Error: {error:.3%}")
        
        if current == max_current:
            break
        current = min( (current + step), max_current )

try:
    bp = batlab.batpool.Batpool()
    sleep(1)
    bl = bp.batpool[bp.batactive] #get the active batlab object
except:
    raise Fault('Ensure that Batlab is connected to computer')
# enable current feedback in firmware
bl.write(UNIT,SETTINGS,5)
# make sure Batlab is getting 5V power (needed for fan)
if (bl.read(COMMS, PSU).data != 1):
    raise Fault('Ensure that 5V power supply is connected to Batlab.')
# find out which Batlab slot the power supply is connected to
i = 0
v = 0
while v < 3:
    v = bl.read(i,VOLTAGE).asvoltage()
    i += 1
    if i > 4:
        raise Fault('Ensure that Keithley power supply is connected to Batlab.')
cell = i - 1

sca_old = bl.read(cell,CURRENT_CALIB_SCA).data
off_old = bl.read(cell,CURRENT_CALIB_OFF).data
print('old calibration: SCA = ' + str(sca_old) + ', OFF = ' + str(off_old))
bl.write(cell,MODE,MODE_DISCHARGE)
test_calibration()

print('setting scale factor to 1 and offset to 0')
bl.write(cell,CURRENT_CALIB_SCA,0x4000)
bl.write(cell,CURRENT_CALIB_OFF,0)

bl.write(cell,CURRENT_SETPOINT,batlab.encoder.Encoder(0).assetpoint())
bl.write(cell,ERROR,0)
bl.write(cell,MODE,MODE_DISCHARGE)

try:
    current = min_current
    while current <= max_current:
        bl.write(cell,CURRENT_SETPOINT,batlab.encoder.Encoder(current).assetpoint())

        # wait for Batlab's current feedback loop to stabilize
        prev_duty = 0
        duty = 1
        while duty != prev_duty:
            prev_duty = duty
            duty = bl.read(cell,DUTY).data
            sleep(0.2)

        # make sure Batlab is in discharge mode
        if bl.read(cell,MODE).data != MODE_DISCHARGE:
            print(bl.read(cell,ERROR).aserr())
            raise Fault('Something went wrong ¯\_(ツ)_/¯')
        
        bat_curr_sum = 0
        ps_curr_sum = 0
        for i in range(8):
            bat_curr_sum += bl.read(cell,CURRENT).ascurrent()
            ps_curr_sum += ps.get_current()
            sleep(0.05)
        bat_current = bat_curr_sum / 8
        ps_current = ps_curr_sum / 8
        currents[bat_current] = ps_current
        if OPTIMIZE_FOR == "ABSOLUTE":
            error = (bat_current - ps_current)
            print(f"Batlab says: {bat_current:.3f} A and PS says: {ps_current:.3f} A.   Error: {(error*1000):.0f} mA")
        elif OPTIMIZE_FOR == "RELATIVE":
            error = (bat_current - ps_current) / ps_current
            print(f"Batlab says: {bat_current:.3f} A and PS says: {ps_current:.3f} A.   Error: {error:.3%}")

        if current == max_current:
            break
        current = min( (current + step), max_current )

    bat_currents = list(currents.keys())
    ps_currents = list(currents.values())

    x = np.array(bat_currents)
    y = np.array(ps_currents)
    # initial guess for the parameters: scale factor = 1, offset = 0
    params0 = np.array([1, 0])

    if OPTIMIZE_FOR == "ABSOLUTE":
        def objective(params, x, y):
            m, b = params
            return np.sum(np.abs(y - m*x - b))
        
        # since most of the charge/discharge happens at the max current, we'll constrain the line of best fit to go through that point
        # the last current value was the maximum
        x0 = bat_current
        y0 = ps_current
        def constraint(params, x0, y0):
            m, b = params
            return y0 - m * x0 - b
        constraint_dict = {'type': 'eq', 'fun': constraint, 'args': (x0, y0)}
        result = minimize(objective, params0, args=(x, y), constraints=constraint_dict)

    elif OPTIMIZE_FOR == "RELATIVE":
        def objective(params, x, y):
            m, b = params
            return np.sum((y - (m * x + b))**2)
        result = minimize(objective, params0, args=(x, y))

    m, b = result.x

    print('new calibration: scale factor = ' + str(m) + ', offset = ' + str(b))
    # in the firmware, the scale factor is a divisor, so we need to invert it
    sca_new = int(0x4000 / m)
    # the offset is subtracted rather than added, hence the negative sign
    # note: in the Batlab Encoder library there is an asioff() method, but it is wrong.
    #   ascurrent() gives the correct value.
    off_new = batlab.encoder.Encoder(-b).ascurrent()
    print('new calibration: SCA = ' + str(sca_new) + ', OFF = ' + str(off_new))
    bl.write(cell,CURRENT_CALIB_SCA,sca_new)
    bl.write(cell,CURRENT_CALIB_OFF,off_new)
    sleep(0.1)

    print("Now let's try that again.")
    test_calibration()

finally:
    # stop discharge and turn off power supply output
    bl.write(cell,CURRENT_SETPOINT,batlab.encoder.Encoder(0).assetpoint())
    sleep(0.1)
    bl.write(cell,MODE,MODE_STOPPED)
    ps.ps.write('outp off')