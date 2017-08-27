from serial import *
from time import sleep, ctime, time
import datetime
import sys
import math
import queue
import threading
from batlab import *
###################################################################################################
ver = '1.0.0'
###################################################################################################
def main():
	bp = batpool()
	print('Batlab Utility Script Version ',ver)
	parse_cmd('help',bp)
	while(True):
		try:
			while bp.msgqueue.qsize() > 0:
				print(bp.msgqueue.get())
			cmd = input(">>>").rstrip()
			parse_cmd(cmd,bp)
		except KeyboardInterrupt:
			quit()
###################################################################################################
def parse_cmd(cmd,bp):
	p = cmd.split()
	if(not p):
		return
	if p[0] == 'help': # get the usage information
		print('General Commands                                                               ')
		print(' list                              - list ports and SNs of connected batlabs   ')
		print(' active (port)                     - set currently active batlab. Or read value')
		print(' quit                              - Exit the program                          ')
		#print(' cmd [input file]                  - Execute batlab-util commands in input file')
		print('Active Batlab Commands                                                         ')
		print(' write [namespace] [addr] [data]   - General Purpose Command for Writing Regs  ')
		print(' read [namespace] [addr]           - General purpose Command for Reading Regs  ')
		print(' update [firmware bin file]        - install firmware update, local bin file   ')
		print(' info                              - return unit namespace information         ')
		print(' measure (cell)                    - return voltage,current,temp,charge        ')
		print(' setpoints (cell)                   - return setpoint information for cell     ')
		print(' impedance [cell]                  - take Z measurment                         ')
		print(' charge [cell] (setpoint)          - begin charge on cell, optionally set I    ')
		print(' sinewave [cell] (setpoint)        - begin sine on cell, optionally set f in Hz')
		print(' discharge [cell] (setpoint)       - begin discharge on cell, optionally set I ')
		#print(' test [settings file]              - starts full cycle test using settings ini ')
		print(' stop (cell)                       - set all cells to stop mode, or only 1 cell')
		print(' reset (cell)                      - set all cells to IDLE mode, or only 1 cell')
	if p[0] == 'list':
		print('PORT SERIAL ACTIVE')
		print('==================')
		if len(bp.batpool.items()) == 0:
			print('No Batlabs Found')
		for port,bat in bp.batpool.items():
			if bp.batactive == port:
				print(port,bat.sn,'*')
			else:
				print(port,bat.sn)
	if p[0] == 'active':
		if len(p) > 1:
			bp.batactive = p[1]
		else:
			print(bp.batactive)
	if p[0] == 'quit':
		bp.quitevt.set() #tries to tell all of the Batlabs to stop the tests
		sleep(2)
		quit()
	if p[0] == 'write':
		if isready(bp):
			bp.batpool[bp.batactive].write(eval(p[1]),eval(p[2]),eval(p[3])).print_packet()
	if p[0] == 'read':
		if isready(bp):
			bp.batpool[bp.batactive].read(eval(p[1]),eval(p[2])).print_packet()
	if p[0] == 'info':
		if isready(bp):
			print('Serial Num  :',bp.batpool[bp.batactive].sn)
			print('FirmwareVer :',bp.batpool[bp.batactive].read(UNIT,FIRMWARE_VER).data)
			print('VCC         :','{:.4f}'.format(bp.batpool[bp.batactive].read(UNIT,VCC).asvcc()),'V')
			print('SINE_FREQ   :','{:.4f}'.format(bp.batpool[bp.batactive].read(UNIT,SINE_FREQ).asfreq()),'Hz')
			print('SETTINGS    :',bp.batpool[bp.batactive].read(UNIT,SETTINGS).data)
			print('SINE_OFFSET :','{:.4f}'.format(bp.batpool[bp.batactive].read(UNIT,SINE_OFFSET).asioff()),'A')
			print('SINE_MAGDIV :','{:.4f}'.format(bp.batpool[bp.batactive].read(UNIT,SINE_MAGDIV).asmagdiv()),'App')
			print('LOCKED      :',bp.batpool[bp.batactive].read(UNIT,LOCK).value())
	if p[0] == 'measure':
		if isready(bp):
			a = 0
			b = 0
			cell = 0
			if len(p) > 1:
				cell = eval(p[1])
				a = cell
				b = cell + 1
			else:
				a = 0
				b = 4
			for iter in range(a,b):
				v = '{:.4f}'.format(bp.batpool[bp.batactive].read(iter,VOLTAGE).asvoltage())
				i = '{:.4f}'.format(bp.batpool[bp.batactive].read(iter,CURRENT).ascurrent())
				#t = '{:.4f}'.format(0.1)
				t = '{:.4f}'.format(bp.batpool[bp.batactive].read(iter,TEMPERATURE).astemperature(bp.batpool[bp.batactive].R,bp.batpool[bp.batactive].B))
				cl = bp.batpool[bp.batactive].read(iter,CHARGEL).data
				ch = bp.batpool[bp.batactive].read(iter,CHARGEH).data
				c = '{:.4f}'.format(ascharge(cl + (ch << 16)))
				mode = bp.batpool[bp.batactive].read(iter,MODE).asmode()
				err = bp.batpool[bp.batactive].read(iter,ERROR).aserr()
				print('CELL'+str(iter)+':',v,'V',i,'A',t,'degF',c,'C',mode,err)
	if p[0] == 'setpoints':
		if isready(bp):
			a = 0
			b = 0
			cell = 0
			if len(p) > 1:
				cell = eval(p[1])
				a = cell
				b = cell + 1
			else:
				a = 0
				b = 4
			for iter in range(a,b):
				sp = '{:.4f}'.format(bp.batpool[bp.batactive].read(iter,CURRENT_SETPOINT).assetpoint())
				vh = '{:.4f}'.format(bp.batpool[bp.batactive].read(iter,VOLTAGE_LIMIT_CHG).asvoltage())
				vl = '{:.4f}'.format(bp.batpool[bp.batactive].read(iter,VOLTAGE_LIMIT_DCHG).asvoltage())
				ih = '{:.4f}'.format(bp.batpool[bp.batactive].read(iter,CURRENT_LIMIT_CHG).ascurrent())
				il = '{:.4f}'.format(bp.batpool[bp.batactive].read(iter,CURRENT_LIMIT_DCHG).ascurrent())
				th = '{:.4f}'.format(bp.batpool[bp.batactive].read(iter,TEMP_LIMIT_CHG).astemperature())
				tl = '{:.4f}'.format(bp.batpool[bp.batactive].read(iter,TEMP_LIMIT_DCHG).astemperature())
				print('CELL'+str(iter)+':',sp,'A',vh,'V',vl,'V',ih,'A',il,'A',th,'degF',tl,'degF')
	if p[0] == 'impedance':
		if isready(bp) and len(p) > 1:
			try:
				cell = eval(p[1])
				'''start impedance measurment'''
				bp.batpool[bp.batactive].write(cell,MODE,MODE_IMPEDANCE)
				sleep(2)
				'''collect results'''
				imag = bp.batpool[bp.batactive].read(cell,CURRENT_PP).ascurrent()
				vmag = bp.batpool[bp.batactive].read(cell,VOLTAGE_PP).asvoltage()
				z = vmag / imag
				bp.batpool[bp.batactive].write(cell,MODE,MODE_IDLE)
				print('Impedance:',z,'Ohms')
			except:
				print('Impedance Measurement Could not be taken - check that cell is present')
	if p[0] == 'charge':
		if isready(bp) and len(p) > 1:
			cell = int(eval(p[1]))
			if(len(p) > 2):
				bp.batpool[bp.batactive].write(cell,CURRENT_SETPOINT,encoder(eval(p[2])).assetpoint())
			bp.batpool[bp.batactive].write(cell,MODE,MODE_CHARGE)
	if p[0] == 'sinewave':
		if isready(bp) and len(p) > 1:
			cell = int(eval(p[1]))
			if(len(p) > 2):
				bp.batpool[bp.batactive].write(UNIT,SINE_FREQ,encoder(eval(p[2])).asfreq())
			bp.batpool[bp.batactive].write(cell,MODE,MODE_IMPEDANCE)
	if p[0] == 'discharge':
		if isready(bp) and len(p) > 1:
			cell = int(eval(p[1]))
			if(len(p) > 2):
				bp.batpool[bp.batactive].write(cell,CURRENT_SETPOINT,encoder(eval(p[2])).assetpoint())
			bp.batpool[bp.batactive].write(cell,MODE,MODE_DISCHARGE)
	if p[0] == 'stop':
		if isready(bp):
			if(len(p) > 1):
				cell = int(eval(p[1]))
				bp.batpool[bp.batactive].write(cell,MODE,MODE_STOPPED)
			else:
				bp.batpool[bp.batactive].write(CELL0,MODE,MODE_STOPPED)
				bp.batpool[bp.batactive].write(CELL1,MODE,MODE_STOPPED)
				bp.batpool[bp.batactive].write(CELL2,MODE,MODE_STOPPED)
				bp.batpool[bp.batactive].write(CELL3,MODE,MODE_STOPPED)
	if p[0] == 'reset':
		if isready(bp):
			if(len(p) > 1):
				cell = int(eval(p[1]))
				bp.batpool[bp.batactive].write(cell,MODE,MODE_IDLE)
			else:
				bp.batpool[bp.batactive].write(CELL0,MODE,MODE_IDLE)
				bp.batpool[bp.batactive].write(CELL1,MODE,MODE_IDLE)
				bp.batpool[bp.batactive].write(CELL2,MODE,MODE_IDLE)
				bp.batpool[bp.batactive].write(CELL3,MODE,MODE_IDLE)
	if p[0] == 'update':
		if isready(bp) and len(p) > 1:
			'''command the Batlab to enter the bootloader'''
			print("Entering Bootloader")
			bp.batpool[bp.batactive].write(UNIT,BOOTLOAD,0x0000)
			sleep(2)
			'''load the image onto the batlab'''
			with open(p[1], "rb") as f:
				byte = f.read(1)
				ctr = 0x0400
				while byte:
					bp.batpool[bp.batactive].write(BOOTLOADER,BL_ADDR,int(ctr))
					bp.batpool[bp.batactive].write(BOOTLOADER,BL_DATA,int(ord(byte)))
					bb = bp.batpool[bp.batactive].read(BOOTLOADER,BL_DATA).value()
					if(bb != int(ord(byte))):
						print("Data Mismatch. Trying again")
						continue
					print(str(ctr - 0x03FF) + " of 15360: " + str(bb) ) 
					ctr = ctr + 1
					byte = f.read(1)
			'''attempt to reboot into the new image'''
			bp.batpool[bp.batactive].write(BOOTLOADER,BL_BOOTLOAD,0x0000)
			sleep(2)
			if(bp.batpool[bp.batactive].read(BOOTLOADER,BL_DATA).value() == COMMAND_ERROR):
				sn = int(bp.batpool[bp.batactive].read(UNIT,SERIAL_NUM).value()) + (int(bp.batpool[bp.batactive].read(UNIT,DEVICE_ID).value()) << 16)
				print("Connected to Batlab " + str(sn))
				fw = int(bp.batpool[bp.batactive].read(UNIT,FIRMWARE_VER).value())
				print("Firmware Version " + str(fw))
			else:
				print("Batlab still in Bootloader -- Try again")
main()