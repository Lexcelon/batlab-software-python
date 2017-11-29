from batlab.constants import *
import batlab.encoder
import batlab.func

from time import sleep
import datetime
import threading
from copy import deepcopy
import traceback

try:
    # Python 2.x
    import Queue as queue
except ImportError:
    # Python 3.x
    import queue as queue

class Channel:
    """Represents one slot or 'channel' in a Batlab.

    Attributes:
        bat: The Batlab object to which this channel belongs
        slot: Integer value of the slot/channel in the Batlab that this object represents
        name: Name of the cell currently installed in the slot
        test_type: You can use this to specify a Cycle Test or a simple discharge test
        test_state: State machine variable for test state. Note that the test state machine is launched in another thread and continuously runs.
        settings: Settings object containing the test settings
    """
    def __init__(self,bat,slot):
        self.bat = bat
        self.slot = slot
        self.name = None # name of the cell in this channel
        #TT_DISCHARGE,TT_CYCLE
        self.test_type = TT_CYCLE
        #TS_IDLE,TS_CHARGE,TS_PRECHARGE,TS_DISCHARGE,TS_CHARGEREST,TS_DISCHARGEREST,TS_POSTDISCHARGE
        self.test_state = TS_IDLE
        # test control variables
        self.start_time = datetime.datetime.now()

        self.settings = self.bat.settings
        self.state = 'IDLE'
        self.timeout_time = None

        self.critical_section = threading.Lock()
        thread = threading.Thread(target=self.thd_channel)
        thread.daemon = True
        thread.start()

    def is_testing(self):
        """Bool, returns False if the test_state is IDLE."""
        if self.test_state == TS_IDLE:
            return False
        else:
            return True

    def runtime(self):
        """Time since test started."""
        return datetime.datetime.now() - self.start_time

    def end_test(self):
        self.test_state = TS_IDLE
        self.bat.write(self.slot,MODE,MODE_STOPPED)

    def start_test(self,cellname=None,test_type=None,timeout_time=None):
        """Initialize the test state machine and start a test on this Batlab channel. First sets the Batlab to the settings in the ``settings`` data member."""
        self.settings = deepcopy(self.bat.settings)

        if cellname is not None:
            self.name = cellname
        if test_type is not None:
            self.test_type = test_type
        self.timeout_time = timeout_time

        # Initialize the test settings
        self.bat.write(self.slot,MODE,MODE_IDLE)
        self.bat.write(self.slot,VOLTAGE_LIMIT_CHG,batlab.encoder.Encoder(self.settings.high_volt_cutoff).asvoltage())
        self.bat.write(self.slot,VOLTAGE_LIMIT_DCHG,batlab.encoder.Encoder(self.settings.low_volt_cutoff).asvoltage())
        self.bat.write(self.slot,CURRENT_LIMIT_CHG,batlab.encoder.Encoder(self.settings.chrg_current_cutoff).ascurrent())
        self.bat.write(self.slot,CURRENT_LIMIT_DCHG,batlab.encoder.Encoder(self.settings.dischrg_current_cutoff).ascurrent())
        self.bat.write(self.slot,TEMP_LIMIT_CHG,batlab.encoder.Encoder(self.settings.chrg_tmp_cutoff).c_astemperature(self.bat.R[self.slot],self.bat.B[self.slot]))
        self.bat.write(self.slot,TEMP_LIMIT_DCHG,batlab.encoder.Encoder(self.settings.dischrg_tmp_cutoff).c_astemperature(self.bat.R[self.slot],self.bat.B[self.slot]))
        self.bat.write(self.slot,CHARGEH,0)
        self.bat.write(self.slot,CHARGEL,0)

        # Actually start the test
        if(self.test_type == TT_CYCLE):
            self.bat.write(self.slot,CURRENT_SETPOINT,0)
            self.bat.write(self.slot,MODE,MODE_CHARGE)
            sleep(0.010)
            self.bat.write(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.chrg_rate).assetpoint())
            self.test_state = TS_PRECHARGE
        else: # Simple Discharge Test
            self.bat.write(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.dischrg_rate).assetpoint())
            self.bat.write(self.slot,MODE,MODE_DISCHARGE)
            self.test_state = TS_DISCHARGE

        # Initialize the control variables
        self.start_time = datetime.datetime.now()
        self.last_lvl2_time = datetime.datetime.now()
        self.last_impedance_time = datetime.datetime.now()
        self.rest_time = datetime.datetime.now()
        self.vavg = 0
        self.vcnt = 0
        self.zavg = 0
        self.zcnt = 0
        self.iavg = 0
        self.icnt = 0
        self.temperature0 = self.bat.read(self.slot,TEMPERATURE).astemperature_c(self.bat.R,self.bat.B)
        self.q = 0
        self.e = 0
        self.deltat = 0
        self.current_cycle = 0

        # control variables for pulse discharge test
        self.pulse_discharge_on_time = 0
        self.pulse_discharge_off_time = 0
        self.pulse_charge_on_time = 0
        self.pulse_charge_off_time = 0
        self.pulse_state = True

        # control variables for trickle charge/discharge at voltage limits
        self.trickle_engaged = False


    def log_lvl2(self,type):
        """Logs 'level 2' test data to the log file and resets the voltage and current average and resets the charge counter back to zero."""
        # Cell Name,Batlab SN,Channel,Timestamp (s),Voltage (V),Current (A),Temperature (C),Impedance (Ohm),Energy (J),Charge (Coulombs),Test State,Test Type,Charge Capacity (Coulombs),Energy Capacity (J),Avg Impedance (Ohm),delta Temperature (C),Avg Current (A),Avg Voltage,Runtime (s)
        state = l_test_state[self.test_state]
        runtime = datetime.datetime.now() - self.last_lvl2_time
        self.last_lvl2_time = datetime.datetime.now()
        logstr = str(self.name) + ',' + str(self.bat.sn) + ',' + str(self.slot) + ',' + str(datetime.datetime.now()) + ',,,,,,,' + ',' + type + ',' + '{:.4f}'.format(self.q) + ',' + '{:.4f}'.format(self.e) + ',' + '{:.4f}'.format(self.zavg) + ',' + '{:.4f}'.format(self.deltat) + ',' + '{:.4f}'.format(self.iavg) + ',' + '{:.4f}'.format(self.vavg) + ',' + str(runtime.total_seconds())
        self.bat.logger.log(logstr,self.settings.logfile)
        # print(logstr)
        # print('Test Completed: Batlab',self.bat.sn,', Channel',self.slot)
        self.vcnt = 0
        self.icnt = 0
        self.zcnt = 0
        self.temperature0 = self.bat.read(self.slot,TEMPERATURE).astemperature_c(self.bat.R,self.bat.B)
        self.bat.write(self.slot,CHARGEH,0)
        self.bat.write(self.slot,CHARGEL,0)
        sleep(2)

    def state_machine_cycletest(self,mode,v):
        if self.test_state == TS_PRECHARGE:
            # handle feature to trickle charge the cell if close to voltage limit
            if self.settings.trickle_enable == 1:
                if v > self.settings.trickle_charge_engage_limit and self.trickle_engaged == False:
                    self.bat.write(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.trickle_chrg_rate).assetpoint())
                    self.trickle_engaged = True

            if mode == MODE_STOPPED:
                self.log_lvl2("PRECHARGE")
                self.test_state = TS_CHARGEREST
                self.rest_time = datetime.datetime.now()
                # We should rarely hit this condition - it means you don't want to make any testing cycles, just carge up and stop, or charge up and equalize
                if self.current_cycle >= (self.settings.num_meas_cyc + self.settings.num_warm_up_cyc):
                    if self.settings.bool_storage_dischrg:
                        self.test_state = TS_POSTDISCHARGE
                        self.bat.write(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.dischrg_rate).assetpoint())
                        self.bat.write(self.slot,MODE,MODE_DISCHARGE)
                    else:
                        self.test_state = TS_IDLE
                        print('Test Completed: Batlab',self.bat.sn,', Channel',self.slot)

        elif self.test_state == TS_CHARGEREST:
            if (datetime.datetime.now() - self.rest_time).total_seconds() > self.settings.rest_time:
                self.log_lvl2("CHARGEREST")
                self.test_state = TS_DISCHARGE

                # reset pulse discharge variables
                self.pulse_state = True
                self.pulse_discharge_on_time = datetime.datetime.now()
                self.pulse_discharge_off_time = datetime.datetime.now()
                self.trickle_engaged = False

                self.bat.write(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.dischrg_rate).assetpoint())
                self.bat.write(self.slot,MODE,MODE_DISCHARGE)
                self.current_cycle += 1

        elif self.test_state == TS_DISCHARGE:
            # handle feature to end test after certain amount of time
            if self.timeout_time is not None:
                if self.timeout_time != 0:
                    if(datetime.datetime.now() - self.start_time).total_seconds() > self.timeout_time:
                        self.bat.write(self.slot,MODE,MODE_STOPPED)
            # handle feature to pulse discharge the cell
            if self.settings.pulse_enable == 1:
                if self.pulse_state == True:
                    if self.pulse_discharge_on_time == 0:
                        self.pulse_discharge_on_time = datetime.datetime.now()
                    if (datetime.datetime.now() - self.pulse_discharge_on_time).total_seconds() > self.settings.pulse_discharge_on_time and self.settings.pulse_discharge_on_time > 0:
                        self.bat.write(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.pulse_discharge_off_rate).assetpoint())
                        self.pulse_state = False
                        self.pulse_discharge_off_time = datetime.datetime.now()
                else:
                    if self.pulse_discharge_off_time == 0:
                        self.pulse_discharge_off_time = datetime.datetime.now()
                    if (datetime.datetime.now() - self.pulse_discharge_off_time).total_seconds() > self.settings.pulse_discharge_off_time and self.settings.pulse_discharge_off_time > 0:
                        if self.trickle_engaged == True:
                            self.bat.write(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.trickle_dischrg_rate).assetpoint())
                        else:
                            self.bat.write(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.dischrg_rate).assetpoint())
                        self.pulse_state = True
                        self.pulse_discharge_on_time = datetime.datetime.now()

            # handle feature to trickle charge the cell if close to voltage limit
            if self.settings.trickle_enable == 1:
                if v < self.settings.trickle_discharge_engage_limit and self.trickle_engaged == False:
                    self.bat.write(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.trickle_dischrg_rate).assetpoint())
                    self.trickle_engaged = True


            if mode == MODE_STOPPED:
                if self.test_type == TT_CYCLE:
                    self.log_lvl2("DISCHARGE")
                    self.test_state = TS_DISCHARGEREST
                    self.rest_time = datetime.datetime.now()

                if self.test_type == TT_DISCHARGE:
                    self.log_lvl2("DISCHARGE")
                    self.test_state = TS_IDLE
                    print('Test Completed: Batlab',self.bat.sn,', Channel',self.slot)

        elif self.test_state == TS_DISCHARGEREST:
            if (datetime.datetime.now() - self.rest_time).total_seconds() > self.settings.rest_time:
                self.log_lvl2("DISCHARGEREST")
                self.test_state = TS_CHARGE

                # reset pulse charge variables
                self.pulse_state = True
                self.pulse_charge_on_time = datetime.datetime.now()
                self.pulse_charge_off_time = datetime.datetime.now()
                self.trickle_engaged = False

                self.bat.write(self.slot,CURRENT_SETPOINT,0)
                self.bat.write(self.slot,MODE,MODE_CHARGE)
                sleep(0.010)
                self.bat.write(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.chrg_rate).assetpoint())
                

        elif self.test_state == TS_CHARGE:
            # handle feature to pulse charge the cell
            if self.settings.pulse_enable == 1:
                if self.pulse_state == True:
                    if self.pulse_charge_on_time == 0:
                        self.pulse_charge_on_time = datetime.datetime.now()
                    if (datetime.datetime.now() - self.pulse_charge_on_time).total_seconds() > self.settings.pulse_charge_on_time and self.settings.pulse_charge_on_time > 0:
                        self.bat.write(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.pulse_charge_off_rate).assetpoint())
                        self.pulse_state = False
                        self.pulse_charge_off_time = datetime.datetime.now()
                else:
                    if self.pulse_charge_off_time == 0:
                        self.pulse_charge_off_time = datetime.datetime.now()
                    if (datetime.datetime.now() - self.pulse_charge_off_time).total_seconds() > self.settings.pulse_charge_off_time and self.settings.pulse_charge_off_time > 0:
                        if self.trickle_engaged == True:
                            self.bat.write(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.trickle_chrg_rate).assetpoint())
                        else:
                            self.bat.write(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.chrg_rate).assetpoint())
                        self.pulse_state = True
                        self.pulse_charge_on_time = datetime.datetime.now()

            # handle feature to trickle charge the cell if close to voltage limit
            if self.settings.trickle_enable == 1:
                if v > self.settings.trickle_charge_engage_limit and self.trickle_engaged == False:
                    self.bat.write(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.trickle_chrg_rate).assetpoint())
                    self.trickle_engaged = True

            if mode == MODE_STOPPED:
                self.log_lvl2("CHARGE")
                self.test_state = TS_CHARGEREST
                self.rest_time = datetime.datetime.now()
                if self.current_cycle >= (self.settings.num_meas_cyc + self.settings.num_warm_up_cyc):
                    if self.settings.bool_storage_dischrg:
                        self.test_state = TS_POSTDISCHARGE
                        self.bat.write(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.dischrg_rate).assetpoint())
                        self.bat.write(self.slot,MODE,MODE_DISCHARGE)
                    else:
                        self.test_state = TS_IDLE
                        print('Test Completed: Batlab',self.bat.sn,', Channel',self.slot)

        elif self.test_state == TS_POSTDISCHARGE:
            if mode == MODE_STOPPED or v < self.settings.storage_dischrg_volt:
                self.log_lvl2("POSTDISCHARGE")
                self.test_state = TS_IDLE
                print('Test Completed: Batlab',self.bat.sn,', Channel',self.slot)

    def thd_channel(self):
        while(True):
            try:
                if self.bat.settings is None:
                    sleep(1)
                    continue
                if self.bat.logger is None:
                    sleep(1)
                    continue
            except:
                sleep(1)
                continue
            try:
                self.state = l_test_state[self.test_state]
                ts = datetime.datetime.now()
                
                
                with self.bat.critical_section:
                    #patch for current compensation problem in firmware versions <= 3
                    #fix is to move the current compensation control loop to software and turn it off in hardware.
                    mode = self.bat.read(self.slot,MODE).asmode()
                    i = self.bat.read(self.slot,CURRENT).ascurrent()
                    p = self.bat.read(self.slot,CURRENT_SETPOINT)
                    op = p.assetpoint() # actual operating point
                    op_raw = p.data
                    sp_raw = self.bat.setpoints[self.slot] #current setpoint
                    sp = sp_raw / 128.0
                    if mode == 'MODE_CHARGE' or mode == 'MODE_DISCHARGE':
                        #print(mode,self.slot,i,op,sp)
                        if i > 0 and sp > 0.5:
                            if i < (sp - 0.01):
                                op_raw += 1
                            elif i > (sp + 0.01):
                                op_raw -= 1
                        if i > 4.02:
                            op_raw -= 1
                        if sp > 4.5:
                            op_raw = 575    
                        # writes to the firmware setpoitn will update the software setpoint, so we need to restore the software setpoint after we write 
                        self.bat.write(self.slot,CURRENT_SETPOINT,op_raw)
                        self.bat.setpoints[self.slot] = sp_raw

                    # actual test manager stuff --- take measurements and control test state machine 
                    if self.test_state != TS_IDLE:
                        # take the measurements
                        v = self.bat.read(self.slot,VOLTAGE).asvoltage()
                        self.vcnt += 1
                        self.vavg += (v - self.vavg) / self.vcnt
                        i = self.bat.read(self.slot,CURRENT).ascurrent()
                        self.icnt += 1
                        self.iavg += (i - self.iavg) / self.icnt
                        t = self.bat.read(self.slot,TEMPERATURE).astemperature_c(self.bat.R,self.bat.B)
                        self.bat.write(UNIT,LOCK,LOCK_LOCKED)
                        q = self.bat.read(self.slot,CHARGEH).data * 65536 + self.bat.read(self.slot,CHARGEL).data
                        q = batlab.func.ascharge(q)
                        self.bat.write(UNIT,LOCK,LOCK_UNLOCKED)
                        e = q * self.vavg
                        mode = self.bat.read(self.slot,MODE).data
                        err = self.bat.read(self.slot,ERROR).data

                        self.q = q
                        self.e = e
                        self.deltat = t - self.temperature0
                        state = l_test_state[self.test_state]

                        # log the results
                        if (ts - self.last_impedance_time).total_seconds() > self.settings.impedance_period and self.settings.impedance_period > 0 and self.trickle_engaged == False:
                            z = self.bat.impedance(self.slot)
                            self.last_impedance_time = datetime.datetime.now()
                            self.zcnt += 1
                            self.zavg += (z - self.zavg) / self.zcnt
                            logstr = str(self.name) + ',' + str(self.bat.sn) + ',' + str(self.slot) + ',' + str(ts) + ',' + '{:.4f}'.format(v) + ',' + '{:.4f}'.format(i) + ',' + '{:.4f}'.format(t) + ',' + '{:.4f}'.format(z) + ',' + '{:.4f}'.format(e) + ',' + '{:.4f}'.format(q) + ',' + state + ',,,,,,,'
                        else:
                            logstr = str(self.name) + ',' + str(self.bat.sn) + ',' + str(self.slot) + ',' + str(ts) + ',' + '{:.4f}'.format(v) + ',' + '{:.4f}'.format(i) + ',' + '{:.4f}'.format(t) + ',,' + '{:.4f}'.format(e) + ',' + '{:.4f}'.format(q) + ',' + state + ',,,,,,,'
                        self.bat.logger.log(logstr,self.settings.logfile)

                        # actually run the test state machine - decides what to do next
                        self.state_machine_cycletest(mode,v)


                if self.settings.reporting_period < 0.5:
                    sleep(0.5)
                else:
                    sleep(self.settings.reporting_period)

            except:
                sleep(2)
                print('Exception on Channel',self.slot,self.name,'...Continuing test')
                traceback.print_exc()
                continue
