Batlab library for Python
=========================

.. image:: https://travis-ci.org/Lexcelon/batlab-software-python.svg?branch=master
	   :target: https://travis-ci.org/Lexcelon/batlab-software-python

.. image:: https://badge.fury.io/py/batlab.svg
	   :target: https://badge.fury.io/py/batlab

.. image:: https://readthedocs.org/projects/batlab-software-python/badge/?version=latest
	   :target: http://batlab-software-python.readthedocs.io/en/latest/?badge=latest
	   :alt: Documentation Status

``batlab-software-python`` is a Python library and example command line script to interact with a pool of Batlabs over USB. This tool is designed for hobbyists and more advanced users who would like to incorporate the Batlab hardware in their own cell testing workflow or environment.

Getting Started
---------------

Requirements
~~~~~~~~~~~~

Python >=3.4 is currently supported by this module.

Python >=2.7 is not yet supported.

Installation
~~~~~~~~~~~~

To install the latest release you can use `pip <https://pip.pypa.io/en/stable/>`_:

```
pip install batlab
```

To upgrade, you can run:

``pip install batlab --upgrade`` or ``pip install batlab -U``.

Documentation
-------------

Deployment
----------

Contributing
------------

When contributing to this repository, please first discuss the change you wish to make via issue, email, or any other method with the owners of this repository before making a change.

Git branching model
~~~~~~~~~~~~~~~~~~~

We follow the development model described `here <http://nvie.com/posts/a-successful-git-branching-model/>`_. Anything in the ``master`` branch is considered production. Most work happens in the ``develop`` branch or in a feature branch that is merged into ``develop`` before being merged into ``master``.

Documenting
~~~~~~~~~~~



Running tests
~~~~~~~~~~~~~

License
-------

Acknowledgements
----------------









settings class
~~~~~~~~~~~~~~

The ``settings`` class contains information the test manager needs to run tests on a cell. The general usage is that settings will be specified in a JSON settings file and then loaded into the program to be used for tests.

Members:

* ``acceptableImpedanceThreshold``
* ``batlabCellPlaylistFileVersion``
* ``cellPlaylistName``
* ``chargeCurrentSafetyCutoff``
* ``chargeRate``
* ``chargeTemperatureCutoff``
* ``dischargeCurrentSafetyCutoff``
* ``dischargeRate``
* ``dischargeTemperatureCutoff``
* ``highVoltageCutoff``
* ``impedanceReportingPeriod``
* ``lowVoltageCutoff``
* ``numMeasurementCycles``
* ``numWarmupCycles``
* ``reportingPeriod``
* ``restPeriod``
* ``sineWaveFrequency``
* ``sineWaveMagnitude``
* ``storageDischarge``
* ``storageDischargeVoltage``

Methods:

* ``load(filehandle)`` - loads information contained in a test JSON file into the instance.

logger class
~~~~~~~~~~~~

Manages access to files for writing test log information.

Methods:

* ``log(logstring,filename)`` - writes entry 'logstring' into file 'filename'

batpool class
~~~~~~~~~~~~~

The ``batpool`` class spins up a thread that manages connections to Batlab devices connected over USB. It monitors the USB ports and maintains a dict of connected Batlabs called the ``batpool``. The contents of this variable are Batlab class instances and they are looked up in the dict by their Serial Port addresses. Pyserial is used in the batlab to manage connections to the computer's serial interface.

A second variable, ``batactive`` is used to store the serial port name of the currently active Batlab, that is, the Batlab to which commands are currently directed.

Members:

* ``msgqueue`` - queue of string messages describing plug-unplug events
* ``batpool`` - dictionary of batlab instances by Serial Port Addrs (ie COM5)
* ``batactive`` - Serial port of active Batlab
* ``logger`` - A logger object that manages access to a log filename
* ``settings`` - A settings object that contains test settings imported from a JSON file

Methods:

* ``active_exists()`` - Returns True if the Batlab described by the ``batactive`` port is connected.

packet class
~~~~~~~~~~~~

The ``packet`` class contains a command response packet from a Batlab. Information from a batlab register read is returned to the user in a ``packet`` instance. The various methods of the packet instance allow the user to decode the raw register data into useable information.

Members:

* ``valid`` - Bool describing if data in the packet can be trusted
* ``timestamp`` - time message was received
* ``namespace`` - Namespace of the register's data this packet contains
* ``addr`` - Register address
* ``data`` - Raw register packet data (int16)
* ``write`` - True if this response packet was for a register write

Methods:

* ``value()`` - returns the raw data if the packet is a response packet, or a list of data pieces if the packet is an extended response packet
* ``asvoltage()`` - represents voltage ``data`` as a floating point voltage
* ``asvcc()`` - represents vcc ``data`` as a floating point voltage
* ``asfreq()`` - represents frequency data in Hz
* ``asioff()`` - represents register current to floating point Amps
* ``assetpoint()`` - represents current setpoint as floating point Amps
* ``asmagdiv()`` - represents magdiv register as Ipp
* ``asmode()`` - represents a mode register value as an enum string
* ``aserr()`` - represents error reg bit field as a string of the error flags
* ``astemperature(Rlist,Blist)`` - represents temp data as temperature in F
* ``astemperature_c(Rlist,Blist)`` - represents temp data as temperature in C
    
  * Rlist - 4 list of 'R' calibration values needed to interpret temp
  * Blist - 4 list of 'B' calibration values needed to interpret temp

* ``ascurrent()`` - represents current measurement as float current in Amps
* ``display()`` - Prints out the basic info about the packet transaction ### charge function
* ``ascharge(data)`` - converts register data in the form (CHARGEL + CHARGEH << 16) to Coulombs

encoder class
~~~~~~~~~~~~~

Essentially the opposite of the packet class. Takes a human-readable measurement or command and converts it to the raw Batlab register value.
  
Methods:

* ``__init__(data)`` - creates the instance with the supplied data
* ``asvoltage()``
* ``asvcc()``
* ``asfreq()``
* ``asioff()``
* ``assetpoint()``
* ``asmagdiv()``
* ``astemperature(R,B)`` - represents temp data as temperature in F
* ``c_astemperature(R,B)`` - represents temp data as temperature in F

  * R - 'R' calibration value needed to interpret temp
  * B - 'B' calibration value needed to interpret temp

* ``ascurrent()`` - represents current measurement as float current in Amps
* ``aschargel()`` - represents charge in coulombs as the low word of charge
* ``aschargeh()`` - represents charge in coulombs as the high word of charge

batlab class
~~~~~~~~~~~~

The class represents 1 'Batlab' unit connected over the USB serial port. The batpool class automatically creates the ``batlab`` instances when a Batlab is plugged in, and destroyed once unplugged. If a Batlab instance is supplied with a port name on creation, it will automatically connect to the port. Otherwise, the user will need to call the ``connect`` method.

Members:

* ``port`` - holds serial port name
* ``is_open`` - corresponds to pyserial 'is\_open'
* ``B`` - list of 'B' temeprature calibration constants for each cell
* ``R`` - list of 'R' temperature calibration constants for each cell
* ``logger`` - logger object that handles file IO.
* ``settings`` - Settings object that contains test settings loaded from JSON file
* ``channel[4]`` - 4-list of ``channel`` objects. Each channel can manage a test run on it

Methods:

* ``connect()`` - connects to serial port in ``port`` variable. Spins off a receiver thread to receive incoming packets and add them to a message queue
* ``disconnect()`` - gracefully closes serial port and kills reader thread
* ``read(namespace,addr)`` - queries a Batlab register specified by the given namespace and register address. The communication architecture spec with all of the namespace and register names, functions, and values can be found in the Batlab Programmer's User Manual. Returns: a ``packet`` instance containing the read data
* ``write(namespace,addr,value)`` - writes the value ``value`` to the register address ``addr`` in namespace ``namespace``. This is the general register write function for the Batlab. It returns a 'write' packet
* ``set_current(cell,current in Amps)`` - a macro for setting the CURRENT\_SETPOINT to a certain current for a given cell
* ``impedance(cell)`` - a macro for taking an impedance measurement on a particular cell
* ``firmware_bootload(filename)`` - writes the firmware image given by the specified filename to the batlab. This may take a few minutes
* ``firmware_check(flag_download)`` - checks GitHub for the latest firmware version, and downloads it if the 'flag\_Download' is True. It returns a 2 list: [version,filename]
* ``firmware_update()`` - checks if the firmware on the Batlab is outdated, and updates the firmware if it needs updating, This may take several minutes.

Library scope functions
~~~~~~~~~~~~~~~~~~~~~~~

* ``get_ports()`` - returns a list of serial ports with Batlabs plugged into them

Batlab Example Utility Script - batlab-util.py
----------------------------------------------

The Batlab Utility script allows users to perform basic interactions with a pool of connected Batlab units through a simple command-line interface.

Type 'help' to display the list of commands in the script and how to use them. The intention for the script is to serve as an example for users to write their own test software using the Batlab Library.

Test Manager - testmgr.py
-------------------------

This file provides classes and methods for managing tests with a pool of Batlabs.

channel class
~~~~~~~~~~~~~

Represents one slot or 'channel' in a Batlab.

Members:

* ``bat`` - the batlab object to which this channel belongs
* ``slot`` - integer value of the slot/channel in the Batlab that this object represents
* ``name`` - name of the cell currently installed in the slot
* ``test_type`` - you can use this to specify a Cycle Test or a simple discharge test
* ``test_state`` - state machine variable for test state
* ``settings`` - settings object containing the test settings

Methods:

* ``is_testing()`` - bool, returns False if the test_state is IDLE
* ``runtime()`` - time since test started.
* ``start_test(cellname,test_type=None,timeout_time=None)`` - initialize the test state machine and start a test on this Batlab channel. First sets the Batlab to the settings in the ``settings`` data member.
* ``log_lvl2(type)`` - logs 'level 2' test data to the log file and resets the voltage and current average and resets the charge counter back to zero.

Note that the test state machine is launched in another thread and continuously runs.
