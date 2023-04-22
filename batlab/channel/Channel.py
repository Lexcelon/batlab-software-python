from batlab.constants import *
import batlab.encoder
import batlab.func

from time import sleep
import datetime
import threading
from copy import deepcopy
import traceback
import math

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
        #TS_IDLE,TS_CHARGE,TS_PRECHARGE,TS_DISCHARGE,TS_CHARGEREST,TS_DISCHARGEREST,TS_POSTDISCHARGE
        self.test_state = TS_IDLE
        # test control variables
        self.start_time = datetime.datetime.now()
        self.killevt = threading.Event()

        self.settings = self.bat.settings
        self.final_charge = False
        self.final_discharge = False
        self.state = 'IDLE'
        self.timeout_time = None

        self.critical_section = threading.Lock()
        thread = threading.Thread(target=self.thd_channel)
        thread.daemon = True
        thread.start()
        #print("channel:",thread.getName())

    def is_testing(self):
        """Bool, returns False if the test_state is IDLE."""
        if self.test_state == TS_IDLE:
            return False
        else:
            return True

    def runtime(self):
        """Time since test started."""
        return datetime.datetime.now() - self.start_time

    def runtime_cycle(self):
        """Time since this test step started"""
        return datetime.datetime.now() - self.last_lvl2_time

    def cycle_number(self):
        """Number of charge/discharge cycles completed"""
        return self.current_cycle

    def end_test(self):
        self.test_state = TS_IDLE
        self.bat.write(self.slot,MODE,MODE_STOPPED)

    def start_test(self,cellname=None,timeout_time=None):
        """Initialize the test state machine and start a test on this Batlab channel. First sets the Batlab to the settings in the ``settings`` data member."""
        self.settings = deepcopy(self.bat.settings)
        self.test_type = self.settings.test_type
        self.charges = self.settings.charges
        self.discharges = self.settings.discharges
        self.ocv_charge_interval = self.settings.ocv_charge_interval

        if cellname is not None:
            self.name = cellname

        self.timeout_time = timeout_time
        
        
        #print the header for the individual cell logfiles if needed
        if self.settings.individual_cell_logs != 0:
            logfile_headerstr = "Cell Name,Batlab SN,Channel,Timestamp (s),Voltage (V),Current (A),Temperature (C),Impedance (Ohm),Charge (C),Test State,Test Type,Runtime (s),VCC (V)"
            self.bat.logger.log(logfile_headerstr,self.settings.cell_logfile + self.name + '.csv')

        # Initialize the test settings
        self.bat.write(self.slot,MODE,MODE_IDLE)
        if self.bat.read(self.slot,MODE).data != MODE_IDLE:
            print("Test on",self.bat.sn,"cell",self.slot,"not started - no cell detected")
            return #test is over ... 
        self.bat.write_verify(self.slot,VOLTAGE_LIMIT_CHG,batlab.encoder.Encoder(self.settings.high_volt_cutoff).asvoltage())
        self.bat.write_verify(self.slot,VOLTAGE_LIMIT_DCHG,batlab.encoder.Encoder(self.settings.low_volt_cutoff).asvoltage())
        self.bat.write_verify(self.slot,CURRENT_LIMIT_CHG,batlab.encoder.Encoder(self.settings.chrg_current_cutoff).ascurrent())
        self.bat.write_verify(self.slot,CURRENT_LIMIT_DCHG,batlab.encoder.Encoder(self.settings.dischrg_current_cutoff).ascurrent())
        self.bat.write_verify(self.slot,TEMP_LIMIT_CHG,batlab.encoder.Encoder(self.settings.chrg_tmp_cutoff).c_astemperature(self.bat.R[self.slot],self.bat.B[self.slot]))
        self.bat.write_verify(self.slot,TEMP_LIMIT_DCHG,batlab.encoder.Encoder(self.settings.dischrg_tmp_cutoff).c_astemperature(self.bat.R[self.slot],self.bat.B[self.slot]))
        self.bat.write(self.slot,CHARGEH,0)
        #self.bat.write(self.slot,CHARGEL,0) # only need to write to one of the charge registers to clear them
        self.bat.write_verify(UNIT,ZERO_AMP_THRESH,batlab.encoder.Encoder(0.05).ascurrent())
        
        # if self.settings.constant_voltage_enable == True: #if we're doing constant voltage charging, we need to have current resolution down to the small range
        #     self.bat.write_verify(UNIT,ZERO_AMP_THRESH,batlab.encoder.Encoder(0.05).ascurrent())
        
        settings = self.bat.read(UNIT,SETTINGS)  
        if self.settings.cv_discharge == True:  
            settings = settings.data | SET_CV_DISCHARGE
        else:
            settings = settings.data & ~SET_CV_DISCHARGE
        self.bat.write_verify(UNIT,SETTINGS,settings)

        self.ocv = self.bat.ocv(self.slot)
        logstr = f"{self.name},{self.bat.sn},{self.slot},{str(datetime.datetime.now())},{self.ocv},0,,,,OCV"
        if self.settings.individual_cell_logs == 0:
            self.bat.logger.log(logstr,self.settings.logfile)
        else:
            self.bat.logger.log(logstr,self.settings.cell_logfile + self.name + '.csv')

        # Actually start the test
        self.bat.write_verify(self.slot,CURRENT_SETPOINT,0)

        if(self.settings.first_stage == FS_CHARGE):
            if self.charges == 1:
                self.final_charge = True
            if (self.bat.read(self.slot,VOLTAGE).asvoltage() >= self.settings.high_volt_cutoff):
                self.charges -= 1
                if self.discharges > 0:
                    self.bat.write(self.slot,MODE,MODE_DISCHARGE)
                    self.bat.write_verify(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.dischrg_rate).assetpoint())
                    self.test_state = TS_DISCHARGE
                else:
                    print("Test on",self.bat.sn,"cell",self.slot,"not started - cell already at high voltage cutoff")
            else:
                self.bat.write(self.slot,MODE,MODE_CHARGE)
                self.bat.write_verify(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.chrg_rate).assetpoint())
                self.test_state = TS_CHARGE
        elif(self.settings.first_stage == FS_DISCHARGE):
            if self.discharges == 1:
                self.final_discharge = True
            if (self.bat.read(self.slot,VOLTAGE).asvoltage() <= self.settings.low_volt_cutoff):
                self.discharges -= 1
                if self.charges > 0:
                    self.bat.write(self.slot,MODE,MODE_CHARGE)
                    self.bat.write_verify(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.chrg_rate).assetpoint())
                    self.test_state = TS_CHARGE
                else:
                    print("Test on",self.bat.sn,"cell",self.slot,"not started - cell already at low voltage cutoff")
            else:
                self.bat.write(self.slot,MODE,MODE_DISCHARGE)
                self.bat.write_verify(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.dischrg_rate).assetpoint())
                self.test_state = TS_DISCHARGE


        # Initialize the control variables
        self.start_time = datetime.datetime.now()
        self.last_lvl2_time = datetime.datetime.now()
        self.last_impedance_time = datetime.datetime.now()
        self.last_lvl1_time = datetime.datetime.now()
        self.rest_time = datetime.datetime.now()
        self.zavg = 0
        self.zcnt = 0
        self.temperature0 = self.bat.read(self.slot,TEMPERATURE).astemperature_c(self.bat.R,self.bat.B)
        self.q = 0
        self.q_prev = 0
        self.q_prev_charge = 0
        self.q_prev_discharge = 0
        self.current_cycle = 0
        self.vcc = 5.0
        self.vprev = 0.0
        self.iprev = 0.0
        self.verrorcnt = 0.0
        

        # control variables for pulse discharge test
        self.pulse_discharge_on_time = 0
        self.pulse_discharge_off_time = 0
        self.pulse_charge_on_time = 0
        self.pulse_charge_off_time = 0
        self.pulse_state = True

        # control variables for trickle charge/discharge at voltage limits
        self.trickle_engaged = False

        self.log_lvl2("START")


    def log_lvl2(self,type):
        """Logs 'level 2' test data to the log file and resets the voltage and current average and resets the charge counter back to zero."""
        # Cell Name,Batlab SN,Channel,Timestamp (s),Voltage (V),Current (A),Temperature (C),Impedance (Ohm),Charge (Coulombs),Test State,Test Type,Charge Capacity (Coulombs),Runtime (s),VCC
        state = l_test_state[self.test_state]
        type = l_test_type[self.test_type]
        # runtime = datetime.datetime.now() - self.last_lvl2_time
        self.last_lvl2_time = datetime.datetime.now()
        logstr = f"{self.name},{self.bat.sn},{self.slot},{datetime.datetime.now()},,,,,{self.q:.4f},{state},{type},{self.runtime()},{self.vcc:.4f}"
        self.bat.logger.log(logstr,self.settings.logfile)
        # print(logstr)
        # print('Test Completed: Batlab',self.bat.sn,', Channel',self.slot)
        self.vcnt = 0
        self.icnt = 0
        self.zcnt = 0
        self.temperature0 = self.bat.read(self.slot,TEMPERATURE).astemperature_c(self.bat.R,self.bat.B)
        self.bat.write(self.slot,CHARGEH,0) #writing to chargeh automatically clears chargel
        sleep(2)

    def state_machine_cycletest(self,mode,v):

        if self.test_state == TS_CHARGEREST:
            if self.i > 0.0:
                self.bat.write(self.slot,CURRENT_SETPOINT,0)
                sleep(1)
                self.bat.write(self.slot,MODE,MODE_STOPPED)
                
            if (datetime.datetime.now() - self.rest_time).total_seconds() > self.settings.rest_time:
                self.log_lvl2("CHARGEREST")

                if self.discharges > 0:
                    self.test_state = TS_DISCHARGE

                    # reset pulse discharge variables
                    self.pulse_state = True
                    self.pulse_discharge_on_time = datetime.datetime.now()
                    self.pulse_discharge_off_time = datetime.datetime.now()
                    self.trickle_engaged = False

                    self.bat.write_verify(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.dischrg_rate).assetpoint())
                    self.bat.write(self.slot,MODE,MODE_DISCHARGE)
                    # self.current_cycle += 1

                    if self.charges == 0 and self.discharges == 1:
                        self.final_discharge = True
                else:
                    self.test_state = TS_IDLE
                    print('Test Completed: Batlab',self.bat.sn,', Channel',self.slot)

        elif self.test_state == TS_DISCHARGE:
            # handle feature to end test after certain amount of time
            if self.timeout_time is not None:
                if self.timeout_time != 0:
                    if(datetime.datetime.now() - self.start_time).total_seconds() > self.timeout_time:
                        self.bat.write_verify(self.slot,MODE,MODE_STOPPED)
            # handle feature to pulse discharge the cell
            if self.settings.pulse_enable == 1:
                if self.pulse_state == True:
                    if self.pulse_discharge_on_time == 0:
                        self.pulse_discharge_on_time = datetime.datetime.now()
                    if (datetime.datetime.now() - self.pulse_discharge_on_time).total_seconds() > self.settings.pulse_discharge_on_time and self.settings.pulse_discharge_on_time > 0:
                        self.bat.write_verify(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.pulse_discharge_off_rate).assetpoint())
                        self.pulse_state = False
                        self.pulse_discharge_off_time = datetime.datetime.now()
                else:
                    if self.pulse_discharge_off_time == 0:
                        self.pulse_discharge_off_time = datetime.datetime.now()
                    if (datetime.datetime.now() - self.pulse_discharge_off_time).total_seconds() > self.settings.pulse_discharge_off_time and self.settings.pulse_discharge_off_time > 0:
                        if self.trickle_engaged == True:
                            self.bat.write_verify(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.trickle_dischrg_rate).assetpoint())
                        else:
                            self.bat.write_verify(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.dischrg_rate).assetpoint())
                        self.pulse_state = True
                        self.pulse_discharge_on_time = datetime.datetime.now()

            elif self.settings.constant_voltage_discharge_enable == True: # handle constant voltage discharge
                stdimpedance = 0.050 / 128.0
                try:
                    stdimpedance = self.zavg / 128.0
                    if(self.zavg > 0.5):
                        stdimpedance = 0.5 / 128.0
                    if(self.zavg < 0.01):
                        stdimpedance = 0.01 / 128.0
                    if(self.zavg == 0 or math.isnan(self.zavg)):
                        stdimpedance = 0.050 / 128.0    
                except:
                    stdimpedance = 0.050 / 128.0
                stdimpedance = stdimpedance * self.settings.constant_voltage_sensitivity
                if v < (self.settings.low_volt_cutoff + (self.bat.setpoints[self.slot] * stdimpedance)) and self.bat.setpoints[self.slot] > self.settings.constant_voltage_stepsize: # if voltage is getting close to the cutoff point and current is flowing at greater than a trickle
                    self.bat.write_verify(self.slot,CURRENT_SETPOINT,self.bat.setpoints[self.slot] - self.settings.constant_voltage_stepsize ) # scale down by 1/32th of an amp
            # handle feature to trickle charge the cell if close to voltage limit
            if self.settings.trickle_enable == 1 and self.settings.constant_voltage_enable == False:
                if v < self.settings.trickle_discharge_engage_limit and self.trickle_engaged == False:
                    self.bat.write_verify(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.trickle_dischrg_rate).assetpoint())
                    self.trickle_engaged = True


            if self.final_discharge == True:
                if self.q_prev_discharge > 0:
                    if self.q > self.q_prev_discharge * self.settings.final_soc:
                        self.discharges -= 1
                        self.log_lvl2("CHARGE")
                        self.test_state = TS_CHARGEREST
                        self.rest_time = datetime.datetime.now()

            if mode == MODE_STOPPED:
                self.discharges -= 1
                self.log_lvl2("DISCHARGE")
                self.test_state = TS_DISCHARGEREST
                self.rest_time = datetime.datetime.now()


        elif self.test_state == TS_DISCHARGEREST:
            if self.i > 0.0:
                self.bat.write(self.slot,CURRENT_SETPOINT,0)
                sleep(1)
                self.bat.write(self.slot,MODE,MODE_STOPPED)

            if (datetime.datetime.now() - self.rest_time).total_seconds() > self.settings.rest_time:
                self.log_lvl2("DISCHARGEREST")
                self.current_cycle += 1

                if self.charges > 0:
                    self.test_state = TS_CHARGE

                    # reset pulse charge variables
                    self.pulse_state = True
                    self.pulse_charge_on_time = datetime.datetime.now()
                    self.pulse_charge_off_time = datetime.datetime.now()
                    self.trickle_engaged = False

                    self.bat.write_verify(self.slot,CURRENT_SETPOINT,0)
                    self.bat.write(self.slot,MODE,MODE_CHARGE)
                    sleep(0.010)
                    self.bat.write_verify(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.chrg_rate).assetpoint())

                    if self.discharges == 0 and self.charges == 1:
                        self.final_charge = True

                else:
                    self.test_state = TS_IDLE
                    print('Test Completed: Batlab',self.bat.sn,', Channel',self.slot)

        elif self.test_state == TS_CHARGE:
            # handle feature to pulse charge the cell
            if self.settings.pulse_enable == 1:
                if self.pulse_state == True:
                    if self.pulse_charge_on_time == 0:
                        self.pulse_charge_on_time = datetime.datetime.now()
                    if (datetime.datetime.now() - self.pulse_charge_on_time).total_seconds() > self.settings.pulse_charge_on_time and self.settings.pulse_charge_on_time > 0:
                        self.bat.write_verify(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.pulse_charge_off_rate).assetpoint())
                        self.pulse_state = False
                        self.pulse_charge_off_time = datetime.datetime.now()
                else:
                    if self.pulse_charge_off_time == 0:
                        self.pulse_charge_off_time = datetime.datetime.now()
                    if (datetime.datetime.now() - self.pulse_charge_off_time).total_seconds() > self.settings.pulse_charge_off_time and self.settings.pulse_charge_off_time > 0:
                        if self.trickle_engaged == True:
                            self.bat.write_verify(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.trickle_chrg_rate).assetpoint())
                        else:
                            self.bat.write_verify(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.chrg_rate).assetpoint())
                        self.pulse_state = True
                        self.pulse_charge_on_time = datetime.datetime.now()

            elif self.settings.constant_voltage_enable == True: # handle constant voltage charge
                stdimpedance = 0.050 / 128.0
                try:
                    stdimpedance = self.zavg / 128.0
                    if(self.zavg > 0.5):
                        stdimpedance = 0.5 / 128.0
                    if(self.zavg < 0.01):
                        stdimpedance = 0.01 / 128.0
                    if(self.zavg == 0 or math.isnan(self.zavg)):
                        stdimpedance = 0.050 / 128.0    
                except:
                    stdimpedance = 0.050 / 128.0
                stdimpedance = stdimpedance * self.settings.constant_voltage_sensitivity
                if v > (self.settings.high_volt_cutoff - (self.bat.setpoints[self.slot] * stdimpedance)) and self.bat.setpoints[self.slot] > self.settings.constant_voltage_stepsize: # if voltage is getting close to the cutoff point and current is flowing at greater than a trickle
                    self.bat.write_verify(self.slot,CURRENT_SETPOINT,self.bat.setpoints[self.slot] - self.settings.constant_voltage_stepsize ) # scale down by 1/32th of an amp

            # handle feature to trickle charge the cell if close to voltage limit
            if self.settings.trickle_enable == 1 and self.settings.constant_voltage_enable == False:
                if v > self.settings.trickle_charge_engage_limit and self.trickle_engaged == False:
                    self.bat.write_verify(self.slot,CURRENT_SETPOINT,batlab.encoder.Encoder(self.settings.trickle_chrg_rate).assetpoint())
                    self.trickle_engaged = True

            if self.final_charge == True:
                if self.q_prev_charge > 0:
                    if self.q > self.q_prev_charge * self.settings.final_soc:
                        self.charges -= 1
                        self.log_lvl2("CHARGE")
                        self.test_state = TS_CHARGEREST
                        self.rest_time = datetime.datetime.now()

            if mode == MODE_STOPPED:
                self.charges -= 1
                self.log_lvl2("CHARGE")
                self.test_state = TS_CHARGEREST
                self.rest_time = datetime.datetime.now()

        elif self.test_state == TS_POSTDISCHARGE:
            if mode == MODE_STOPPED or v < self.settings.storage_dischrg_volt:
                self.log_lvl2("POSTDISCHARGE")
                self.bat.write_verify(self.slot,MODE,MODE_IDLE)
                self.test_state = TS_IDLE
                print('Test Completed: Batlab',self.bat.sn,', Channel',self.slot,', Time:',datetime.datetime.now())

    def thd_channel(self):
        while(True):
            try:
                if self.killevt.is_set(): #stop the thread if the batlab object goes out of scope
                    return
                if self.bat.settings is None:
                    sleep(1)
                    continue
                if self.bat.logger is None:
                    sleep(1)
                    continue
                if self.bat.bootloader == True:
                    sleep(1)
                    continue
            except:
                sleep(1)
                continue
            try:
                self.state = l_test_state[self.test_state]
                ts = datetime.datetime.now()
                
                
                with self.bat.critical_section:
                    # patch for current compensation problem in firmware versions <= 3
                    # fix is to move the current compensation control loop to software and turn it off in hardware.
                    # mode = self.bat.read(self.slot,MODE).asmode()
                    # i = self.bat.read(self.slot,CURRENT).ascurrent()
                    # p = self.bat.read(self.slot,CURRENT_SETPOINT)
                    # op = p.assetpoint() # actual operating point
                    # op_raw = p.data
                    # sp_raw = self.bat.setpoints[self.slot] #current setpoint
                    # sp = sp_raw / 128.0
                    # if mode == 'MODE_CHARGE' or mode == 'MODE_DISCHARGE':
                    #     print(mode,self.slot,i,op,sp)
                    #     if i > 0 and (sp >= 0.35 or i < 0.37):
                    #         if i < (sp - 0.01):
                    #             op_raw += 1
                    #         elif i > (sp + 0.01):
                    #             op_raw -= 1
                    #     if i > 4.02:
                    #         op_raw -= 1
                    #     if sp > 4.5:
                    #         op_raw = 575
                    #     if op_raw < self.settings.constant_voltage_stepsize and sp_raw > 0: #make sure that some amount of trickle current is flowing even if our setpoint is close to 0
                    #         op_raw = self.settings.constant_voltage_stepsize
                    #     if op_raw > 575 and sp_raw <= 575: #If for some reason we read a garbage op_raw, then don't make that our new setpoint
                    #         op_raw = sp_raw
                    #     if not math.isnan(op_raw):
                    #         # writes to the firmware setpoitn will update the software setpoint, so we need to restore the software setpoint after we write 
                    #         self.bat.write(self.slot,CURRENT_SETPOINT,op_raw)
                    #         self.bat.setpoints[self.slot] = sp_raw
                            
                    #reset the batlab watchdog timer (shuts off current flow if it reaches 0 --- 256 to 0 in about 30 seconds)
                    self.bat.write(UNIT,WATCHDOG_TIMER,WDT_RESET) #If firmware version is < 3, this command will not do anything

                    # actual test manager stuff --- take measurements and control test state machine 
                    if self.test_state != TS_IDLE:
                        # take the measurements
                        v = self.bat.read(self.slot,VOLTAGE).asvoltage()
                        i = self.bat.read(self.slot,CURRENT).ascurrent()
                        t = self.bat.read(self.slot,TEMPERATURE).astemperature_c(self.bat.R,self.bat.B)
                        q = self.bat.charge(self.slot) #self.bat.read(self.slot,CHARGEH).data * 65536 + self.bat.read(self.slot,CHARGEL).data
                        mode = self.bat.read(self.slot,MODE).data
                        
                        #take VCC measurement - cannot safely continue test if VCC is too low
                        vc  = self.bat.read(UNIT,VCC).asvcc()
                        if not math.isnan(vc):
                            if vc < 4.7:
                                print("Warning: VCC on",self.bat.sn,"is dangerously low.")
                                print("This could be caused by using multiple Batlab units with the same 5V power supply.")
                            if vc < 4.1 and self.vcc < 4.1:
                                self.bat.write_verify(self.slot,MODE,MODE_STOPPED)
                                self.test_state = TS_IDLE
                                print('Test Aborted due to low VCC: Batlab',self.bat.sn,', Channel',self.slot,', Time:',datetime.datetime.now())
                            self.vcc = vc
                            
                            
                        # detect voltage measurement inconsistency hardware problem that was found on a couple of batlabs
                        if not math.isnan(v) and not math.isnan(i):
                            if self.iprev > 0.05 and self.vprev > 0.5:
                                if math.fabs(i - self.iprev) < 0.05:
                                    if self.vprev - v > 0.2:
                                        self.verrorcnt += 1
                                        print("Warning: unexpected voltage jump detected on Batlab",self.bat.sn," Channel",self.slot,', Time:',datetime.datetime.now())
                                        if self.verrorcnt > 5:
                                            self.bat.write_verify(self.slot,MODE,MODE_STOPPED)
                                            self.test_state = TS_IDLE
                                            print('Test Aborted due to voltage measurement inconsistency. Possible hardware problem with: Batlab',self.bat.sn,', Channel',self.slot,', Time:',datetime.datetime.now())                       
                            self.iprev = i
                            self.vprev = v

                        self.q = q
                        if q != 0:
                            if self.test_state == TS_CHARGE and self.final_charge == False:
                                self.q_prev_charge = q
                            elif self.test_state == TS_DISCHARGE and self.final_discharge == False:
                                self.q_prev_discharge = q
                        
                        state = l_test_state[self.test_state]
                        type = l_test_type[self.test_type]

                        # log the results
                        if (ts - self.last_lvl1_time).total_seconds() > self.settings.reporting_period:
                            self.last_lvl1_time = datetime.datetime.now()
                            if self.settings.impedance_charge_interval > 0 and ((q - self.q_prev) > self.settings.impedance_charge_interval) and self.trickle_engaged == False:
                                self.q_prev = q
                                z = self.bat.impedance(self.slot)
                                if math.isnan(z):
                                    z = 0
                                    print("error in impedance measurement")
                                self.last_impedance_time = datetime.datetime.now()
                                self.zcnt += 1
                                self.zavg += (z - self.zavg) / self.zcnt
                                logstr = f"{self.name},{self.bat.sn},{self.slot},{ts},,,{t:.4f},{z:.4f},{q:.4f},IMP,{type},,{self.vcc:.4f}"
                            elif self.settings.ocv_charge_interval > 0 and ((q - self.q_prev) > self.settings.ocv_charge_interval):
                                self.q_prev = q
                                self.ocv = self.bat.ocv(self.slot)
                                logstr = f"{self.name},{self.bat.sn},{self.slot},{ts},{self.ocv:.4f},{0},{t:.4f},,{q:.4f},OCV,{type},{self.runtime()},{self.vcc}"               
                            else:
                                logstr = f"{self.name},{self.bat.sn},{self.slot},{ts},{v:.4f},{i:.4f},{t:.4f},,{q:.4f},{state},{type},{self.runtime()},{self.vcc:.4f}" 


                            if self.settings.individual_cell_logs == 0:
                                self.bat.logger.log(logstr,self.settings.logfile)
                            else:
                                self.bat.logger.log(logstr,self.settings.cell_logfile + self.name + '.csv')
                        

                        # actually run the test state machine - decides what to do next
                        self.state_machine_cycletest(mode,v)

                sleep(0.01)
                if self.settings.reporting_period < 0.5:
                    sleep(0.5)
                elif self.settings.reporting_period < 1.0:
                    sleep(self.settings.reporting_period)
                else:
                    sleep(1)

            except:
                sleep(2)
                print('Exception on Channel',self.slot,self.name,'...Continuing test')
                traceback.print_exc()
                continue
