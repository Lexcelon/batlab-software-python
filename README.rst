batlab-software-python
======================

Python Library and example command line interface script to interact
with a pool of Batlabs over USB. This tool is designed for hobbyists and
more advanced users who would like to incorporate the Batlab hardware in
their own cell testing workflow or enviroment.

The following source files have been provided: \* batlab.py - The Batlab
Library \* batlabutil.py - An example script utilizing the library \*
testmgr.py - Added functionality that adds the concept of a channel that
runs a test workflow. \* constants.py

Batlab API - batlab.py
----------------------

The Batlab Library allows users to manage connections and read and write
commands to a pool of Batlabs connected over a USB interface.

settings class
~~~~~~~~~~~~~~

The ``settings`` class contains information the test manager needs to
run tests on a cell. The general usage is that settings will be
specified in a JSON settings file and then loaded into the program to be
used for tests.

| Members: "acceptableImpedanceThreshold": "batlabToolkitGUIVersion":
| "cellPlaylistName":
| "chargeCurrentSafetyCutoff":
| "chargeRate":
| "chargeTemperatureCutoff":
| "dischargeCurrentSafetyCutoff": "dischargeRate":
| "dischargeTemperatureCutoff":
| "highVoltageCutoff":
| "impedanceReportingPeriod":
| "lowVoltageCutoff":
| "numMeasurementCycles":
| "numWarmupCycles":
| "reportingPeriod":
| "restPeriod":
| "sineWaveFrequency":
| "sineWaveMagnitude":
| "storageDischarge":
| "storageDischargeVoltage":

Methods: \* ``load(filehandle)`` - loads information contained in a test
JSON file into the instance.

logger class
~~~~~~~~~~~~

Manages access to files for writing test log information.

Methods: \* ``log(logstring,filename)`` - writes entry 'logstring' into
file 'filename'

batpool class
~~~~~~~~~~~~~

The ``batpool`` class spins up a thread that manages connections to
Batlab devices connected over USB. It monitors the USB ports and
matinains a dict of connected Batlabs called the ``batpool``. The
contents of this variable are Batlab class instances and they are looked
up in the dict by their Serial Port addresses. Pyserial is used in the
batlab to manage connections to the computer's serial interface.

A second variable, ``batactive`` is used to store the serial port name
of the currently active Batlab, that is, the Batlab to which commands
are currently directed.

Members: \* ``msgqueue`` - queue of string messages describing
plug-unplug events \* ``batpool`` - dictionary of batlab instances by
Serial Port Addrs (ie COM5) \* ``batactive`` - Serial port of active
Batlab \* ``logger`` - A logger object that manages access to a log
filename \* ``settings`` - A settings object that contains test settings
imported from a JSON file

Methods: \* ``active_exists()`` - Returns True if the Batlab described
by the ``batactive`` port is connected.

packet class
~~~~~~~~~~~~

The ``packet`` class contains a command response packet from a Batlab.
Information from a batlab register read is returned to the user in a
``packet`` instance. The various methods of the packet instance allow
the user to decode the raw register data into useable information.

Members: \* ``valid`` - Bool describing if data in the packet can be
trusted \* ``timestamp`` - time message was recieved \* ``namespace`` -
Namespace of the register's data this packet contains \* ``addr`` -
Register address \* ``data`` - Raw register packet data (int16) \*
``write`` - True if this response packet was for a register write

Methods: \* ``value()`` - returns the raw data if the packet is a
response packet, or a list of data pieces if the packet is an extended
response packet \* ``asvoltage()`` - represents voltage ``data`` as a
floating point voltage \* ``asvcc()`` - represents vcc ``data`` as a
floating point voltage \* ``asfreq()`` - represents frequency data in Hz
\* ``asioff()`` - represents register current to floating point Amps \*
``assetpoint()`` - represents current setpoint as floating point Amps \*
``asmagdiv()`` - represents magdiv register as Ipp \* ``asmode()`` -
represents a mode register value as an enum string \* ``aserr()`` -
represents error reg bit field as a string of the error flags \*
``astemperature(Rlist,Blist)`` - represents temp data as temeprature in
F \* ``astemperature_c(Rlist,Blist)`` - represents temp data as
temeprature in C \* Rlist - 4 list of 'R' calibration values needed to
interpret temp \* Blist - 4 list of 'B' calibration values needed to
interpret temp \* ``ascurrent()`` - represents current measurement as
float current in Amps \* ``display()`` - Prints out the basic info about
the packet transaction ### charge function \* ``ascharge(data)`` -
converts register data in the form (CHARGEL + CHARGEH << 16) to Coulombs

encoder class
~~~~~~~~~~~~~

Essentially the opposite of the packet class. Takes a human-readable
measurement or command and converts it to the raw batlab register value

Methods: \* ``__init__(data)`` - creates the instance with the supplied
data \* ``asvoltage()`` \* ``asvcc()`` \* ``asfreq()`` \* ``asioff()``
\* ``assetpoint()`` \* ``asmagdiv()`` \* ``astemperature(R,B)`` -
represents temp data as temeprature in F \* ``c_astemperature(R,B)`` -
represents temp data as temeprature in F \* R - 'R' calibration value
needed to interpret temp \* B - 'B' calibration value needed to
interpret temp \* ``ascurrent()`` - represents current measurement as
float current in Amps \* ``aschargel()`` - represents charge in coulombs
as the low word of charge \* ``aschargeh()`` - represents charge in
coulombs as the high word of charge

batlab class
~~~~~~~~~~~~

The class represents 1 'Batlab' unit connected over the USB serial port.
The batpool class automatically creates the ``batlab`` instances when a
Batlab is plugged in, and destroyed once unplugged. If a Batlab instance
is suppleid with a port name on creation, it will automatically connect
to the port. Otherwise, the user will need to call the ``connect``
method.

Members:

-  ``port`` - holds serial port name
-  ``is_open`` - corresponds to pyserial 'is\_open'
-  ``B`` - list of 'B' temeprature calibration constants for each cell
-  ``R`` - list of 'R' temperature calibration constants for each cell
-  ``logger`` - logger object that handles file IO.
-  ``settings`` - Settings object that contains test settings loaded
   from JSON file
-  ``channel[4]`` - 4-list of ``channel`` objects. Each channel can
   manage a test run on it

Methods:

-  ``connect()`` - connects to serial port in ``port`` variable. Spins
   off a receiver thread to receive incoming packets and add them to a
   message queue
-  ``disconnect()`` - gracefully closes serial port and kills reader
   thread
-  ``read(namespace,addr)`` - queries a Batlab register specified by the
   givien namespace and register address. The communication architecture
   spec with all of the namespace and register names, functions, and
   values can be found in the Batlab Programmer's User Manual. Returns:
   a ``packet`` instance containing the read data
-  ``write(namespace,addr,value)`` - writes the value ``value`` to the
   register address ``addr`` in namespace ``namespace``. This is the
   general register write function for the Batlab. It returns a 'write'
   packet
-  ``set_current(cell,current in Amps)`` - a macro for setting the
   CURRENT\_SETPOINT to a certain current for a given cell
-  ``impedance(cell)`` - a macro for taking an impedance measurement on
   a particular cell
-  ``firmware_bootload(filename)`` - writes the firmware image given by
   the specified filename to the batlab. This may take a few minutes
-  ``firmware_check(flag_download)`` - checks GitHub for the latest
   firmware version, and downloads it if the 'flag\_Download' is True.
   It returns a 2 list: [version,filename]
-  ``firmware_update()`` - checks if the firmware on the Batlab is
   outdated, and updates the firmware if it needs updating, This may
   take several minutes.

Library scope functions and defines
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  get\_ports() - returs a list of serial ports with batabs plugged into
   them

   '''namespace definitions''' CELL0 = 0x00 CELL1 = 0x01 CELL2 = 0x02
   CELL3 = 0x03 UNIT = 0x04 BOOTLOADER = 0x05 COMMS = 0xFF '''cell
   register map''' MODE = 0x00 ERROR = 0x01 STATUS = 0x02
   CURRENT\_SETPOINT = 0x03 REPORT\_INTERVAL = 0x04 TEMPERATURE = 0x05
   CURRENT = 0x06 VOLTAGE = 0x07 CHARGEL = 0x08 CHARGEH = 0x09
   VOLTAGE\_LIMIT\_CHG = 0x0A VOLTAGE\_LIMIT\_DCHG= 0x0B
   CURRENT\_LIMIT\_CHG = 0x0C CURRENT\_LIMIT\_DCHG= 0x0D
   TEMP\_LIMIT\_CHG = 0x0E TEMP\_LIMIT\_DCHG = 0x0F DUTY = 0x10
   COMPENSATION = 0x11 CURRENT\_PP = 0x12 VOLTAGE\_PP = 0x13
   CURRENT\_CALIB\_OFF = 0x14 CURRENT\_CALIB\_SCA = 0x15 TEMP\_CALIB\_R
   = 0x16 TEMP\_CALIB\_B = 0x17 CURRENT\_CALIB\_PP = 0x18
   VOLTAGE\_CALIB\_PP = 0x19 CURR\_CALIB\_PP\_OFF = 0x1A
   VOLT\_CALIB\_PP\_OFF = 0x1B CURR\_LOWV\_SCA = 0x1C CURR\_LOWV\_OFF =
   0x1D CURR\_LOWV\_OFF\_SCA = 0x1E

   '''unit register map''' SERIAL\_NUM = 0x00 DEVICE\_ID = 0x01
   FIRMWARE\_VER = 0x02 VCC = 0x03 SINE\_FREQ = 0x04 SYSTEM\_TIMER =
   0x05 SETTINGS = 0x06 SINE\_OFFSET = 0x07 SINE\_MAGDIV = 0x08
   LED\_MESSAGE = 0x09 BOOTLOAD = 0x0A VOLT\_CH\_CALIB\_OFF = 0x0B
   VOLT\_CH\_CALIB\_SCA = 0x0C VOLT\_DC\_CALIB\_OFF = 0x0D
   VOLT\_DC\_CALIB\_SCA = 0x0E LOCK = 0x0F ZERO\_AMP\_THRESH = 0x10
   '''COMMs register map''' LED0 = 0x00 LED1 = 0x01 LED2 = 0x02 LED3 =
   0x03 PSU = 0x04 PSU\_VOLTAGE = 0x05 '''BOOTLOAD register map'''
   BL\_BOOTLOAD = 0x00 BL\_ADDR = 0x01 BL\_DATA = 0x02 '''register
   specific codes and defines''' MODE\_NO\_CELL = 0x0000 MODE\_BACKWARDS
   = 0x0001 MODE\_IDLE = 0x0002 MODE\_CHARGE = 0x0003 MODE\_DISCHARGE =
   0x0004 MODE\_IMPEDANCE = 0x0005 MODE\_STOPPED = 0x0006 MODE\_LIST =
   ['MODE\_NO\_CELL','MODE\_BACKWARDS','MODE\_IDLE','MODE\_CHARGE','MODE\_DISCHARGE','MODE\_IMPEDANCE','MODE\_STOPPED']
   ERR\_VOLTAGE\_LIMIT\_CHG = 0x0001 ERR\_VOLTAGE\_LIMIT\_DCHG = 0x0002
   ERR\_CURRENT\_LIMIT\_CHG = 0x0004 ERR\_CURRENT\_LIMIT\_DCHG = 0x0008
   ERR\_TEMP\_LIMIT\_CHG = 0x0010 ERR\_TEMP\_LIMIT\_DCHG = 0x0020
   ERR\_LIST =
   ['ERR\_VOLTAGE\_LIMIT\_CHG','ERR\_VOLTAGE\_LIMIT\_DCHG','ERR\_CURRENT\_LIMIT\_CHG','ERR\_CURRENT\_LIMIT\_DCHG','ERR\_TEMP\_LIMIT\_CHG','ERR\_TEMP\_LIMIT\_DCHG']
   STAT\_VOLTAGE\_LIMIT\_CHG = 0x0001 STAT\_VOLTAGE\_LIMIT\_DCHG= 0x0002
   STAT\_CURRENT\_LIMIT\_CHG = 0x0004 STAT\_CURRENT\_LIMIT\_DCHG= 0x0008
   STAT\_TEMP\_LIMIT\_CHG = 0x0010 STAT\_TEMP\_LIMIT\_DCHG = 0x0020
   STAT\_BACKWARDS = 0x0040 STAT\_NO\_CELL = 0x0080 SET\_TRIM\_OUTPUT =
   0x0001 SET\_VCC\_COMPENSATION = 0x0002 SET\_DEBUG = 0x8000 LED\_OFF =
   0x0000 LED\_BLIP = 0x0001 LED\_FLASH\_SLOW = 0x0002 LED\_FLASH\_FAST
   = 0x0003 LED\_ON = 0x0004 LED\_PWM = 0x0005 LED\_RAMP\_UP = 0x0006
   LED\_RAMP\_DOWN = 0x0007 LED\_SINE = 0x0008

Batlab Example Utility Script - batlab-util.py
----------------------------------------------

The Batlab Utility script allows users to perform basic interactions
with a pool of connected Batlab units through a simple command-line
interface.

Type 'help' to display the list of commands in the script and how to use
them. The intention for the script is to serve as an example for users
to write their own test software using the Batlab Library.

Test Manager - testmgr.py
-------------------------

This file provides classes and methods for managing tests with a pool of
Batlabs.

channel class
~~~~~~~~~~~~~

Represents one slot or 'channel' in a Batlab.

Members: \* ``bat`` - the batlab object to which this channel belongs \*
``slot`` - integer value of the slot/channel in the Batlab that this
object represents \* ``name`` - name of the cell currently installed in
the slot \* ``test_type`` - you can use this to specify a Cycle Test or
a simple discharge test \* ``test_state`` - state machine variable for
test state \* ``settings`` - settings object containing the test
settings

Methods: \* ``is_testing()`` -- bool, returns False if the test\_state
is IDLE \* ``runtime()`` -- time since test started. \*
``start_test(cellname,test_type=None,timeout_time=None)`` - initialize
the test state machine and start a test on this Batlab channel. First
sets the Batlab to the settings in the ``settings`` data member. \*
``log_lvl2(type)`` - logs 'level 2' test data to the log file and resets
the voltage and current average and resets the charge counter back to
zero.

Note that the test state machine is launched in another thread and
continuously runs.
