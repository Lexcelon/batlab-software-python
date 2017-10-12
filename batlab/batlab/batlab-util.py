from time import sleep, ctime, time

# Import the Batlab class - do it this way so you can use all of the defined constants for register
# mappings. I know my Python looks like C. I'm an embedded systems guy and I'd love it if some of
# you more python inclined people would completely re-write this script to be more Pythonic.
from batlab import * 
###################################################################################################
def main():
	bp = batpool() # Create the Batpool
	print('Batlab Utility Script')
	parse_cmd('help',bp)
	while(True):
		try:
			while bp.msgqueue.qsize() > 0: #get message from the Batpool message queue
				print(bp.msgqueue.get()) #These messages relate to Batlab Plug/unplug events
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
		print(' help                              - show this help                            ')
		print(' constants                         - show the register and namespace names     ')
		print('Active Batlab Commands                                                         ')
		print(' write [namespace] [addr] [data]   - General Purpose Command for Writing Regs  ')
		print(' read [namespace] [addr]           - General purpose Command for Reading Regs  ')
		print('    example: "read UNIT FIRMWARE_VER"                                          ')
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
		print(' firmware load [firmware bin file] - load firmware update from local bin file  ')
		print(' firmware update                   - check for firmware update. Load if needed ')
		print(' firmware check                    - check for firmware update.                ')
		
	if p[0] == 'constants':
		print('NAMESPACE LIST: CELL0, CELL1, CELL2, CELL3, UNIT, BOOTLOADER, COMMS            ')
		print('CELL REGISTERS: MODE, ERROR, STATUS, CURRENT_SETPOINT, REPORT_INTERVAL         ')
		print('CELL REGISTERS: TEMPERATURE, CURRENT, VOLTAGE, CHARGEL, CHARGEH                ')
		print('CELL REGISTERS: VOLTAGE_LIMIT_CHG, VOLTAGE_LIMIT_DCHG, CURRENT_LIMIT_CHG       ')
		print('CELL REGISTERS: CURRENT_LIMIT_DCHG, TEMP_LIMIT_CHG, TEMP_LIMIT_DCHG            ')
		print('CELL REGISTERS: CURRENT_PP, VOLTAGE_PP                                         ')
		print('UNIT REGISTERS: SERIAL_NUM, DEVICE_ID, FIRMEWARE_VER, VCC, SINE_FREQ           ')
		print('UNIT REGISTERS: SETTINGS, SINE_OFFSET, SINE_MAGDIV, LED_MESSAGE, LOCK          ')
		print('COMM REGISTERS: LED0, LED1, LED2, LED3, PSU, PSU_VOLTAGE                       ')

		
	###############################################################################################
	# FOLLOWING COMMANDS HELP YOU MANAGE THE CONTEXT - The Batlab specific commands only interact 
	# with one Batlab at a time - the 'Active' Batlab. But all are technically opened on the serial
	# port
	###############################################################################################
		
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
		bp.quit()
		quit()
		
	###############################################################################################
	# COMMANDS BELOW THIS LINE REFERENCE THE ACTIVE BATLAB
	###############################################################################################
	if bp.active_exists(): #checks to make sure the bp.batpool[bp.batactive] exists
		b = bp.batpool[bp.batactive] #get the active batlab object
		if p[0] == 'write' and len(p) == 4:
			try:
				b.write(eval(p[1]),eval(p[2]),eval(p[3])).display()
			except:
				print("Invalid Usage.")
			
		if p[0] == 'read' and len(p) == 3:
			try:
				b.read(eval(p[1]),eval(p[2])).display()
			except:
				print("Invalid Usage.")
			
		if p[0] == 'info':
			print('Serial Num  :',b.read(UNIT,SERIAL_NUM).data + b.read(UNIT,DEVICE_ID).data * 65536 )
			print('FirmwareVer :',b.read(UNIT,FIRMWARE_VER).data)
			print('VCC         :','{:.4f}'.format(b.read(UNIT,VCC).asvcc()),'V')
			print('SINE_FREQ   :','{:.4f}'.format(b.read(UNIT,SINE_FREQ).asfreq()),'Hz')
			print('SETTINGS    :',b.read(UNIT,SETTINGS).data)
			print('SINE_OFFSET :','{:.4f}'.format(b.read(UNIT,SINE_OFFSET).asioff()),'A')
			print('SINE_MAGDIV :','{:.4f}'.format(b.read(UNIT,SINE_MAGDIV).asmagdiv()),'App')
			print('LOCKED      :',b.read(UNIT,LOCK).value())
			
		if p[0] == 'measure':
			try:
				aa = 0
				bb = 0
				cell = 0
				if len(p) > 1:
					cell = eval(p[1])
					aa = cell
					bb = cell + 1
				else:
					aa = 0
					bb = 4
				for iter in range(aa,bb):
					v = '{:.4f}'.format(b.read(iter,VOLTAGE).asvoltage())
					i = '{:.4f}'.format(b.read(iter,CURRENT).ascurrent())
					t = '{:.4f}'.format(b.read(iter,TEMPERATURE).astemperature(b.R,b.B))
					cl = b.read(iter,CHARGEL).data
					ch = b.read(iter,CHARGEH).data
					c = '{:.4f}'.format(ascharge(cl + (ch << 16)))
					mode = b.read(iter,MODE).asmode()
					err = b.read(iter,ERROR).aserr()
					print('CELL'+str(iter)+':',v,'V',i,'A',t,'degF',c,'Coulombs',mode,err)
			except:
				print("Invalid Usage.")
				
		if p[0] == 'setpoints':
			try:
				aa = 0
				bb = 0
				cell = 0
				if len(p) > 1:
					cell = eval(p[1])
					aa = cell
					bb = cell + 1
				else:
					aa = 0
					bb = 4
				for iter in range(aa,bb):
					sp = '{:.4f}'.format(b.read(iter,CURRENT_SETPOINT).assetpoint())
					vh = '{:.4f}'.format(b.read(iter,VOLTAGE_LIMIT_CHG).asvoltage())
					vl = '{:.4f}'.format(b.read(iter,VOLTAGE_LIMIT_DCHG).asvoltage())
					ih = '{:.4f}'.format(b.read(iter,CURRENT_LIMIT_CHG).ascurrent())
					il = '{:.4f}'.format(b.read(iter,CURRENT_LIMIT_DCHG).ascurrent())
					th = '{:.4f}'.format(b.read(iter,TEMP_LIMIT_CHG).astemperature(b.R,b.B))
					tl = '{:.4f}'.format(b.read(iter,TEMP_LIMIT_DCHG).astemperature(b.R,b.B))
					print('CELL'+str(iter)+':',sp,'A setpoint,',vh,'V CHG,',vl,'V DISCHG,',ih,'A CHG,',il,'A DISCHG,',th,'degF CHG,',tl,'degF DISCHG')
			except:
				print("Invalid Usage.")
				
		if p[0] == 'impedance' and len(p) > 1:
			try:
				cell = eval(p[1])
				'''start impedance measurment'''
				b.write(cell,MODE,MODE_IMPEDANCE)
				sleep(2)
				'''collect results'''
				imag = b.read(cell,CURRENT_PP).ascurrent()
				vmag = b.read(cell,VOLTAGE_PP).asvoltage()
				z = vmag / imag
				b.write(cell,MODE,MODE_IDLE)
				print('Impedance:',z,'Ohms')
			except:
				print('Impedance Measurement Could not be taken - check that cell is present')
				
		if p[0] == 'charge' and len(p) > 1:
			try:
				cell = int(eval(p[1]))
				if(len(p) > 2):
					b.write(cell,CURRENT_SETPOINT,encoder(eval(p[2])).assetpoint())
				b.write(cell,MODE,MODE_CHARGE)
			except:
				print("Invalid Usage.")
				
		if p[0] == 'sinewave' and len(p) > 1:
			try:
				cell = int(eval(p[1]))
				if(len(p) > 2):
					b.write(UNIT,SINE_FREQ,encoder(eval(p[2])).asfreq())
				b.write(cell,MODE,MODE_IMPEDANCE)
			except:
				print("Invalid Usage.")
			
		if p[0] == 'discharge' and len(p) > 1:
			try:
				cell = int(eval(p[1]))
				if(len(p) > 2):
					b.write(cell,CURRENT_SETPOINT,encoder(eval(p[2])).assetpoint())
				b.write(cell,MODE,MODE_DISCHARGE)
			except:
				print("Invalid Usage.")
			
		if p[0] == 'stop':
			if(len(p) > 1):
				try:
					cell = int(eval(p[1]))
					b.write(cell,MODE,MODE_STOPPED)
				except:
					print("Invalid Usage.")
			else:
				b.write(CELL0,MODE,MODE_STOPPED)
				b.write(CELL1,MODE,MODE_STOPPED)
				b.write(CELL2,MODE,MODE_STOPPED)
				b.write(CELL3,MODE,MODE_STOPPED)
				
		if p[0] == 'reset':
			if(len(p) > 1):
				try:
					cell = int(eval(p[1]))
					b.write(cell,MODE,MODE_IDLE)
				except:
					print("Invalid Usage.")
			else:
				b.write(CELL0,MODE,MODE_IDLE)
				b.write(CELL1,MODE,MODE_IDLE)
				b.write(CELL2,MODE,MODE_IDLE)
				b.write(CELL3,MODE,MODE_IDLE)
				
		if p[0] == 'firmware' and len(p) > 1:
		
			if p[1] == 'load' and len(p) > 2:
				b.firmware_bootload(p[2]) #The entire bootload procedure is a library function
				
			if p[1] == 'update':
				b.firmware_update()
			
			if p[1] == 'check':
				ver,filename = b.firmware_check(False) #firmware_check(True) checks AND downloads image
				print("Latest version is:",ver)
	
	else:
		if bp.batactive == '':
			print('No Batlab Currently Set As Active')
		else:
			print('Batlab on ' + bp.batactive + ' not found')
###################################################################################################
main()