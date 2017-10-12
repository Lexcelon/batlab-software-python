# batlab-software-python

Python Library and example command line interface script to interact with a 
pool of Batlabs over USB. This tool is designed for hobbyists and more 
advanced users who would like to incorporate the Batlab hardware in their
own cell testing workflow or enviroment.

Two source files have been provided:
  * batlab.py - The Batlab Library
  * batlab-util.py - An example script utilizing the library

## Batlab API - batlab.py

The Batlab Library allows users to manage connections and read and write 
commands to a pool of Batlabs connected over a USB interface. 

### batpool class

The `batpool` class spins up a thread that manages connections to 
Batlab devices connected over USB. It monitors the USB ports and 
matinains a dict of connected Batlabs called the `batpool`. The 
contents of this variable are Batlab class instances and they are
looked up in the dict by their Serial Port addresses. Pyserial is used
in the batlab to manage connections to the computer's serial interface.

A second variable, `batactive` is used to store the serial port name of
the currently active Batlab, that is, the Batlab to which commands are 
currently directed.

Members:
* `msgqueue` - queue of string messages describing plug-unplug events
* `batpool` - dictionary of batlab instances by Serial Port Addrs (ie COM5)
* `batactive` - Serial port of active Batlab

Methods:
* `active_exists()` - Returns True if the Batlab described by the `batactive` port is connected.


###  packet class

The `packet` class contains a command response packet from a Batlab.
Information from a batlab register read is returned to the user in 
a `packet` instance. The various methods of the packet instance allow
the user to decode the raw register data into useable information.

Members:
  *  `valid` - Bool describing if data in the packet can be trusted
  *  `timestamp` - time message was recieved
  *  `namespace` - Namespace of the register's data this packet contains
  *  `addr` - Register address
  *  `data` - Raw register packet data (int16)
  *  `write` - True if this response packet was for a register write
 
Methods:
* `value()` - returns the raw data if the packet is a response packet, or a list of data pieces if the packet is an extended response packet
* `asvoltage()` - represents voltage `data` as a floating point voltage
* `asvcc()` - represents vcc `data` as a floating point voltage
* `asfreq()` - represents frequency data in Hz
* `asioff()` - represents register current to floating point Amps
* `assetpoint()` - represents current setpoint as floating point Amps
* `asmagdiv()` - represents magdiv register as Ipp
* `asmode()` - represents a mode register value as an enum string
* `aserr()` - represents error reg bit field as a string of the error flags
* `astemperature(Rlist,Blist)` - represents temp data as temeprature in F
  * Rlist - 4 list of 'R' calibration values needed to interpret temp
  * Blist - 4 list of 'B' calibration values needed to interpret temp
* `ascurrent()` - represents current measurement as float current in Amps
* `display()` - Prints out the basic info about the packet transaction
### charge function
* `ascharge(data)` - converts register data in the form (CHARGEL + CHARGEH << 16) to Coulombs

### encoder class

Essentially the opposite of the packet class. Takes a human-readable
measurement or command and converts it to the raw batlab register value

Methods:
* `__init__(data)` - creates the instance with the supplied data
* `asvoltage()` 
* `asvcc()` 
* `asfreq()` 
* `asioff()` 
* `assetpoint()`
* `asmagdiv()`
* `astemperature(R,B)` - represents temp data as temeprature in F
  * R - 'R' calibration value needed to interpret temp
  * B - 'B' calibration value needed to interpret temp
* `ascurrent()` - represents current measurement as float current in Amps
* `aschargel()` - represents charge in coulombs as the low word of charge
* `aschargeh()` - represents charge in coulombs as the high word of charge


### batlab class

The class represents 1 'Batlab' unit connected over the USB serial port.
The batpool class automatically creates the `batlab` instances when a 
Batlab is plugged in, and destroyed once unplugged. If a Batlab instance
is suppleid with a port name on creation, it will automatically connect
to the port. Otherwise, the user will need to call the `connect` method.

Members:

* `port` - holds serial port name
* `is_open` - corresponds to pyserial 'is_open'
* `B` - list of 'B' temeprature calibration constants for each cell
* `R` - list of 'R' temperature calibration constants for each cell

Methods:

* `connect()` - connects to serial port in `port` variable. Spins off a 
	receiver thread to receive incoming packets and add them to a message queue
* `disconnect()` - gracefully closes serial port and kills reader thread
* `read(namespace,addr)` - queries a Batlab register specified by the givien
	namespace and register address. The communication architecture spec with
	all of the namespace and register names, functions, and values can be found
	in the Batlab Programmer's User Manual.
		Returns: a `packet` instance containing the read data
* `write(namespace,addr,value)` - writes the value `value` to the register
	address `addr` in namespace `namespace`. This is the general register write
	function for the Batlab. It returns a 'write' packet
* `set_current(cell,current in Amps)` - a macro for setting the CURRENT_SETPOINT to
	a certain current for a given cell
* `firmware_bootload(filename)` - writes the firmware image given by the specified filename to the batlab. This may take a few minutes
* `firmware_check(flag_download)` - checks GitHub for the latest firmware version, and downloads it if the 'flag_Download' is True. It returns a 2 list: [version,filename]
* `firmware_update()` - checks if the firmware on the Batlab is outdated, and updates the firmware if it needs updating, This may take several minutes.
	
### Library scope functions and defines

* get_ports() - returs a list of serial ports with batabs plugged into them
	

	'''namespace definitions'''
	CELL0             = 0x00
	CELL1             = 0x01
	CELL2             = 0x02
	CELL3             = 0x03
	UNIT              = 0x04
	BOOTLOADER        = 0x05
	COMMS             = 0xFF
	'''cell register map'''
	MODE              = 0x00
	ERROR             = 0x01
	STATUS            = 0x02
	CURRENT_SETPOINT  = 0x03
	REPORT_INTERVAL   = 0x04
	TEMPERATURE       = 0x05
	CURRENT           = 0x06
	VOLTAGE           = 0x07
	CHARGEL           = 0x08
	CHARGEH           = 0x09 
	VOLTAGE_LIMIT_CHG = 0x0A
	VOLTAGE_LIMIT_DCHG= 0x0B
	CURRENT_LIMIT_CHG = 0x0C
	CURRENT_LIMIT_DCHG= 0x0D
	TEMP_LIMIT_CHG    = 0x0E
	TEMP_LIMIT_DCHG   = 0x0F
	DUTY              = 0x10
	COMPENSATION      = 0x11
	CURRENT_PP        = 0x12
	VOLTAGE_PP        = 0x13
	CURRENT_CALIB_OFF = 0x14
	CURRENT_CALIB_SCA = 0x15
	TEMP_CALIB_R      = 0x16
	TEMP_CALIB_B      = 0x17
	CURRENT_CALIB_PP  = 0x18
	VOLTAGE_CALIB_PP  = 0x19
	CURR_CALIB_PP_OFF = 0x1A
	VOLT_CALIB_PP_OFF = 0x1B
	CURR_LOWV_SCA     = 0x1C
	CURR_LOWV_OFF     = 0x1D
	CURR_LOWV_OFF_SCA = 0x1E

	'''unit register map'''
	SERIAL_NUM       =  0x00
	DEVICE_ID        =  0x01
	FIRMWARE_VER     =  0x02
	VCC              =  0x03
	SINE_FREQ        =  0x04
	SYSTEM_TIMER     =  0x05
	SETTINGS         =  0x06
	SINE_OFFSET      =  0x07
	SINE_MAGDIV      =  0x08
	LED_MESSAGE      =  0x09
	BOOTLOAD         =  0x0A
	VOLT_CH_CALIB_OFF = 0x0B
	VOLT_CH_CALIB_SCA = 0x0C
	VOLT_DC_CALIB_OFF = 0x0D
	VOLT_DC_CALIB_SCA = 0x0E
	LOCK              = 0x0F
	ZERO_AMP_THRESH   = 0x10
	'''COMMs register map'''
	LED0             = 0x00
	LED1             = 0x01
	LED2             = 0x02
	LED3             = 0x03
	PSU              = 0x04
	PSU_VOLTAGE      = 0x05
	'''BOOTLOAD register map'''
	BL_BOOTLOAD      = 0x00
	BL_ADDR          = 0x01
	BL_DATA          = 0x02
	'''register specific codes and defines'''
	MODE_NO_CELL           = 0x0000
	MODE_BACKWARDS         = 0x0001
	MODE_IDLE              = 0x0002
	MODE_CHARGE            = 0x0003
	MODE_DISCHARGE         = 0x0004
	MODE_IMPEDANCE         = 0x0005
	MODE_STOPPED           = 0x0006
	MODE_LIST = ['MODE_NO_CELL','MODE_BACKWARDS','MODE_IDLE','MODE_CHARGE','MODE_DISCHARGE','MODE_IMPEDANCE','MODE_STOPPED']
	ERR_VOLTAGE_LIMIT_CHG  = 0x0001
	ERR_VOLTAGE_LIMIT_DCHG = 0x0002
	ERR_CURRENT_LIMIT_CHG  = 0x0004
	ERR_CURRENT_LIMIT_DCHG = 0x0008
	ERR_TEMP_LIMIT_CHG     = 0x0010
	ERR_TEMP_LIMIT_DCHG    = 0x0020
	ERR_LIST = ['ERR_VOLTAGE_LIMIT_CHG','ERR_VOLTAGE_LIMIT_DCHG','ERR_CURRENT_LIMIT_CHG','ERR_CURRENT_LIMIT_DCHG','ERR_TEMP_LIMIT_CHG','ERR_TEMP_LIMIT_DCHG']
	STAT_VOLTAGE_LIMIT_CHG = 0x0001
	STAT_VOLTAGE_LIMIT_DCHG= 0x0002
	STAT_CURRENT_LIMIT_CHG = 0x0004
	STAT_CURRENT_LIMIT_DCHG= 0x0008
	STAT_TEMP_LIMIT_CHG    = 0x0010
	STAT_TEMP_LIMIT_DCHG   = 0x0020
	STAT_BACKWARDS         = 0x0040
	STAT_NO_CELL           = 0x0080
	SET_TRIM_OUTPUT        = 0x0001
	SET_VCC_COMPENSATION   = 0x0002
	SET_DEBUG              = 0x8000
	LED_OFF                = 0x0000 
	LED_BLIP               = 0x0001
	LED_FLASH_SLOW         = 0x0002
	LED_FLASH_FAST         = 0x0003
	LED_ON                 = 0x0004
	LED_PWM                = 0x0005
	LED_RAMP_UP            = 0x0006
	LED_RAMP_DOWN          = 0x0007
	LED_SINE               = 0x0008
	
	
## Batlab Example Utility Script - batlab-util.py

The Batlab Utility script allows users to perform basic interactions with
a pool of connected Batlab units through a simple command-line interface.

Type 'help' to display the list of commands in the script and how to use them. The intention for the script is to serve as an example for users to write their own test software using the Batlab Library.








