import logging
import json

class Settings:
    """Holds information the test manager uses to run tests on a cell.

    The Settings class contains information the test manager needs to
    run tests on a cell. The general usage is that settings will be
    specified in a JSON settings file and then loaded into the program
    to be used for tests.

    Attributes:
        acceptableImpedanceThreshold: Ohms
        batlabCellPlaylistFileVersion
        cellPlaylistName
        chargeCurrentSafetyCutoff: Amps
        chargeRate: Amps
        chargeTemperatureCutoff: Celsius
        dischargeCurrentSafetyCutoff: Amps
        dischargeRate: Amps
        dischargeTemperatureCutoff: Celsius
        highVoltageCutoff: Volt
        impedanceReportingPeriod: Seconds
        lowVoltageCutoff: Volts
        numMeasurementCycles
        numWarmupCycles
        reportingPeriod: Seconds
        restPeriod: Seconds
        sineWaveFrequency: Hz
        sineWaveMagnitude
        storageDischarge: Boolean
        storageDischargeVoltage: Volts

    """
    
    def __init__(self):
        """Initializes Settings with builtin default values."""
        self.jsonsettings = None
        self.acceptable_impedance_threshold = 1.0
        self.batlab_cell_playlist_file_version = "0.0.1"
        self.cell_playlist_name =         "DefaultPlaylist"
        self.chrg_current_cutoff =        4.096
        self.chrg_rate =                  2.0
        self.prechrg_rate =               2.0
        self.chrg_tmp_cutoff =            50
        self.dischrg_current_cutoff =     4.096
        self.dischrg_rate =               2.0
        self.dischrg_tmp_cutoff =         80
        self.high_volt_cutoff =           4.2
        self.impedance_period =           60
        self.low_volt_cutoff =            2.5
        self.num_meas_cyc =               1
        self.num_warm_up_cyc =            0
        self.reporting_period =       1
        self.rest_time =          60
        self.sinewave_freq =         (10000.0/256.0)
        self.sinewave_magnitude =     2.0
        self.bool_storage_dischrg =       0
        self.storage_dischrg_volt =       3.8

        self.trickle_enable                 = 0
        self.pulse_enable                   = 0
        self.constant_voltage_enable        = False
        self.trickle_discharge_engage_limit = 4.1
        self.trickle_charge_engage_limit    = 2.8
        self.trickle_chrg_rate              = 0.5
        self.trickle_dischrg_rate           = 0.5
        self.pulse_discharge_off_time       = 10
        self.pulse_discharge_on_time        = 60
        self.pulse_charge_on_time           = 60
        self.pulse_charge_off_time          = 10
        self.pulse_charge_off_rate          = 0
        self.pulse_discharge_off_rate       = 0
        self.individual_cell_logs           = 0

        self.flag_ignore_safety_limits = False
        self.logfile = 'batlab-log_' + self.cell_playlist_name + '.csv'
        self.cell_logfile = 'batlab-log_' + self.cell_playlist_name + '_'

    def check(self, key, value, minval ,maxval, variable):
        if self.flag_ignore_safety_limits == True:
            return True
        if value < minval or value > maxval:
            logging.warning("{} with value {} is not safe for Lipo cells.".format(key, value))
            logging.warning("Defaulting to {}".format(variable))
            return False
        return True

    def load(self,fhandle):
        """Loads information contained in a test JSON file into the Settings instance."""
        self.jsonsettings = json.load(fhandle)
        for key,value in self.jsonsettings.items():
            if key == "acceptableImpedanceThreshold":
                self.acceptable_impedance_threshold = value
            if key == "batlabCellPlaylistFileVersion":
                self.batlab_cell_playlist_file_version = value
            if key == "cellPlaylistName":
                self.cell_playlist_name = value
            if key == "chargeCurrentSafetyCutoff":
                if self.check(key,value,0,4.096,self.chrg_current_cutoff):
                    self.chrg_current_cutoff = value
            if key == "chargeRate":
                if self.check(key,value,0,4.0,self.chrg_rate):
                    self.chrg_rate = value
            if key == "prechargeRate":
                if self.check(key,value,0,4.0,self.prechrg_rate):
                    self.prechrg_rate = value
            if key == "chargeTemperatureCutoff":
                if self.check(key,value,-60,80,self.chrg_tmp_cutoff):
                    self.chrg_tmp_cutoff = value
            if key == "dischargeCurrentSafetyCutoff":
                if self.check(key,value,0,4.096,self.dischrg_current_cutoff):
                    self.dischrg_current_cutoff = value
            if key == "dischargeRate":
                if self.check(key,value,0,4.0,self.dischrg_rate):
                    self.dischrg_rate = value
            if key == "dischargeTemperatureCutoff":
                if self.check(key,value,-60,80,self.dischrg_tmp_cutoff):
                    self.dischrg_tmp_cutoff = value
            if key == "highVoltageCutoff":
                if self.check(key,value,3.0,4.3,self.high_volt_cutoff):
                    self.high_volt_cutoff = value
            if key == "impedanceReportingPeriod":
                self.impedance_period = value
            if key == "lowVoltageCutoff":
                if self.check(key,value,2.4324,4.25,self.low_volt_cutoff):
                    self.low_volt_cutoff = value
            if key == "numMeasurementCycles":
                self.num_meas_cyc = value
            if key == "numWarmupCycles":
                self.num_warm_up_cyc = value
            if key == "reportingPeriod":
                self.reporting_period = value
            if key == "restPeriod":
                self.rest_time = value
            if key == "sineWaveFrequency":
                if self.check(key,value,39.0625,1054.6875,self.sinewave_freq):
                    self.sinewave_freq = value
            if key == "sineWaveMagnitude":
                if self.check(key,value,0,2,self.sinewave_magnitude):
                    self.sinewave_magnitude = value
            if key == "storageDischarge":
                self.bool_storage_dischrg = value
            if key == "storageDischargeVoltage":
                if self.check(key,value,2.5,4.3,self.storage_dischrg_volt):
                    self.storage_dischrg_volt = value

            if key == "trickleEnable":
                self.trickle_enable = value
            if key == "pulseEnable":
                self.pulse_enable = value
            if key == "constantVoltageEnable":
                self.constant_voltage_enable = value
            if key == "trickleDischrgEngageVoltage":
                self.trickle_discharge_engage_limit = value
            if key == "trickleChrgEngageVoltage":
                self.trickle_charge_engage_limit = value
            if key == "trickleChrgRate":
                self.trickle_chrg_rate = value
            if key == "trickleDischrgRate":
                self.trickle_dischrg_rate = value
            if key == "pulseDischrgOffTime":
                self.pulse_discharge_off_time = value
            if key == "pulseDischrgOnTime":
                self.pulse_discharge_on_time = value
            if key == "pulseChrgOnTime":
                self.pulse_charge_on_time = value
            if key == "pulseChrgOffTime":
                self.pulse_charge_off_time = value
            if key == "pulseDischrgOffRate": 
                self.pulse_discharge_off_rate = value
            if key == "individualCellLogs": 
                self.individual_cell_logs = value

        self.logfile = 'batlab-log_' + self.cell_playlist_name + '.csv'
        self.cell_logfile = 'batlab-log_' + self.cell_playlist_name + '_'
        self.view()

    def view(self):
        """Print out currently loaded settings."""
        print("Currently Loaded Test Settings -",self.logfile)
        print("===========================================================")
        print("cellPlaylistName             :",self.cell_playlist_name     )
        print("chargeCurrentSafetyCutoff    :",self.chrg_current_cutoff    )
        print("chargeRate                   :",self.chrg_rate              )
        print("prechargeRate                :",self.prechrg_rate           )
        print("chargeTemperatureCutoff      :",self.chrg_tmp_cutoff        )
        print("dischargeCurrentSafetyCutoff :",self.dischrg_current_cutoff )
        print("dischargeRate                :",self.dischrg_rate           )
        print("dischargeTemperatureCutoff   :",self.dischrg_tmp_cutoff     )
        print("highVoltageCutoff            :",self.high_volt_cutoff       )
        print("impedanceReportingPeriod     :",self.impedance_period       )
        print("lowVoltageCutoff             :",self.low_volt_cutoff        )
        print("numMeasurementCycles         :",self.num_meas_cyc           )
        print("numWarmupCycles              :",self.num_warm_up_cyc        )
        print("reportingPeriod              :",self.reporting_period       )
        print("restPeriod                   :",self.rest_time              )
        print("sineWaveFrequency            :",self.sinewave_freq          )
        print("sineWaveMagnitude            :",self.sinewave_magnitude     )
        print("storageDischarge             :",self.bool_storage_dischrg   )
        print("storageDischargeVoltage      :",self.storage_dischrg_volt   )
        print("trickleEnable                :",self.trickle_enable                 )
        print("pulseEnable                  :",self.pulse_enable                   )
        print("constantVoltageEnable        :",self.constant_voltage_enable        )
        print("trickleDischrgEngageVoltage  :",self.trickle_discharge_engage_limit )
        print("trickleChrgEngageVoltage     :",self.trickle_charge_engage_limit    )
        print("trickleChrgRate              :",self.trickle_chrg_rate              )
        print("trickleDischrgRate           :",self.trickle_dischrg_rate           )
        print("pulseDischrgOffTime          :",self.pulse_discharge_off_time       )
        print("pulseDischrgOnTime           :",self.pulse_discharge_on_time        )
        print("pulseChrgOnTime              :",self.pulse_charge_on_time           )
        print("pulseChrgOffTime             :",self.pulse_charge_off_time          )
        print("pulseDischrgOffRate          :",self.pulse_discharge_off_rate       )
        print("individualCellLogs           :",self.individual_cell_logs           )
