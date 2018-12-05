from time import sleep, ctime, time
from builtins import input
import logging

import batlab.batpool
import batlab.func
import batlab.encoder
from batlab.constants import *
import threading

def batlabutil():
    bp = batlab.batpool.Batpool() # Create the Batpool
    print('Batlab Utility Script')
    batlab_parse_cmd('help',bp)
    while(True):
        try:
            while bp.msgqueue.qsize() > 0: # get message from the Batpool message queue
                print(bp.msgqueue.get()) # These messages relate to Batlab Plug/unplug events
            cmd = input(">>> ").rstrip()
            batlab_parse_cmd(cmd,bp)
        except (KeyboardInterrupt, EOFError):
            print()
            quit()

def batlab_parse_cmd(cmd,bp):
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
        print('Global Batlab Commands                                                         ')
        print(' global cycletest [c1 c2 ... cn]   - start test on all given cells,load batlabs')
        print('                                   - by serial num order then by slot num asc  ')
        print(' global measure                    - measure all cells on all connected batlabs')
        print('Active Batlab Test Commands                                                    ')
        print(' cycletest [cell] [cellname]       - Start cycle test using loaded settings    ')
        print(' cycletest all [cell0name c1 c2 c3]- Start cycle test using loaded settings    ')
        print(' dischargetest [cell] [cellname] (timeout)  - Start disch tst w/ loaded setngs ')
        print(' load settings [settings filename] - Load in test settings from .json file     ')
        print(' view settings                     - display current test settings             ')
        print('Active Batlab Lower-Level Commands                                             ')
        print(' write [namespace] [addr] [data]   - General Purpose Command for Writing Regs  ')
        print(' read [namespace] [addr]           - General purpose Command for Reading Regs  ')
        print('    example: "read UNIT FIRMWARE_VER"                                          ')
        print(' info                              - return unit namespace information         ')
        print(' measure (cell)                    - return voltage,current,temp,charge        ')
        print(' setpoints (cell)                  - return setpoint information for cell     ')
        print(' impedance [cell]                  - take Z measurment                         ')
        print(' charge [cell] (setpoint)          - begin charge on cell, optionally set I    ')
        print(' charge all (setpoint)             - begin charge on all cells, optional set I ')
        print(' sinewave [cell] (setpoint)        - begin sine on cell, optionally set f in Hz')
        print(' discharge [cell] (setpoint)       - begin discharge on cell, optionally set I ')
        print(' discharge all (setpoint)          - begin discharge on all cell, option set I ')
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


    # FOLLOWING COMMANDS HELP YOU MANAGE THE CONTEXT - The Batlab specific commands only interact with one Batlab at a time - the 'Active' Batlab. But all are technically opened on the serial port
    if p[0] == 'threads':
        for t in threading.enumerate():
            print(t.getName())
    if p[0] == 'list':
        print('PORT SERIAL ACTIVE')
        print('==================')
        if len(bp.batpool.items()) == 0:
            print('No Batlabs Found')
        for port,bat in bp.batpool.items():
            if bp.batactive == port:
                print(port,bat.sn,'*Active*',':')
                for aa in range(0,4):
                    if bat.channel[aa].is_testing():
                        print('    Channel ',aa,': TESTING',bat.channel[aa].name,'Runtime:',bat.channel[aa].runtime(),'State:',bat.channel[aa].state,'State Runtime:',bat.channel[aa].runtime_cycle(),'Cycle Number:',bat.channel[aa].cycle_number())
                    else:
                        print('    Channel ',aa,': IDLE')
            else:
                print(port,bat.sn,':')
                for aa in range(0,4):
                    if bat.channel[aa].is_testing():
                        print('    Channel ',aa,': TESTING',bat.channel[aa].name,'Runtime:',bat.channel[aa].runtime(),'State:',bat.channel[aa].state,'State Runtime:',bat.channel[aa].runtime_cycle(),'Cycle Number:',bat.channel[aa].cycle_number())
                    else:
                        print('    Channel ',aa,': IDLE')

    if p[0] == 'active':
        if len(p) > 1:
            bp.batactive = p[1]
        else:
            print(bp.batactive)

    if p[0] == 'quit':
        bp.quit()
        quit()

    if p[0] == 'load' and len(p) > 2:
        if p[1] == 'settings':
            with open(p[2],'r') as fhandle:
                bp.settings.load(fhandle)
                fhandle.seek(0) #reset cursor back to beginning of file
                print('Results File will be written to testResults/',bp.settings.logfile)
                # Print the Header to the CSV file dictated by this settings file
                logfile_headerstr = '"' + fhandle.read().replace('"','""') + '"' + ',,,,,,,,,,,,,,,,,,,'
                bp.logger.log(logfile_headerstr,bp.settings.logfile)
                logfile_headerstr = "Cell Name,Batlab SN,Channel,Timestamp (s),Voltage (V),Current (A),Temperature (C),Impedance (Ohm),Energy (J),Charge (Coulombs),Test State,Test Type,Charge Capacity (Coulombs),Energy Capacity (J),Avg Impedance (Ohm),delta Temperature (C),Avg Current (A),Avg Voltage,Runtime (s),VCC (V)"
                bp.logger.log(logfile_headerstr,bp.settings.logfile)

    if p[0] == 'view' and len(p) > 1:
        if p[1] == 'settings':
            bp.settings.view()

    if p[0] == 'ignore' and len(p) > 1: #Don't advertise this on help page
        if p[1] == 'safety':
            bp.settings.flag_ignore_safety_limits = True
            logging.warning("Test Safety Limits Disabled")
            
            
    if p[0] == 'global' and len(p) > 1:
        if p[1] == 'cycletest': 
            batlist = []
            for port,bat in bp.batpool.items():
                batlist.append(bat)
            batlist.sort(key=lambda x: int(x.sn), reverse=False)
            cell = 0
            misses = 0
            for bat in batlist:
                with bat.critical_section:
                    for slot in range(0,4):
                        if (cell < len(p)-2): 
                            if bat.channel[slot].is_testing():
                                print("Can't start test - Test is already running on this channel")
                                misses += 1
                            elif bat.read(slot,MODE).data == MODE_NO_CELL or bat.read(slot,MODE).data == MODE_BACKWARDS:
                                print("Can't start test - No Cell Detected")
                                misses += 1
                            else:
                                bat.channel[slot].start_test(p[2+cell],1)
                            cell += 1
                        else:
                            print("Started cycle test on",cell - misses,"cells")
                            return
                        
        if p[1] == 'measure':
            batlist = []
            for port,bat in bp.batpool.items():
                batlist.append(bat)
            batlist.sort(key=lambda x: int(x.sn), reverse=False)
            for bat in batlist:
                with bat.critical_section:
                    vc = '{:.4f}'.format(bat.read(UNIT,VCC).asvcc())
                    print('Batlab',bat.sn,': VCC',vc,'V')
                    for iter in range(0,4):
                        v = '{:.4f}'.format(bat.read(iter,VOLTAGE).asvoltage())
                        i = '{:.4f}'.format(bat.read(iter,CURRENT).ascurrent())
                        t = '{:2.0f}'.format(bat.read(iter,TEMPERATURE).astemperature(bat.R,bat.B))
                        tc = '{:2.0f}'.format((float(t)-32)*5.0/9.0)
                        chg = bat.charge(iter)
                        c = '{:6.0f}'.format(chg)
                        mode = bat.read(iter,MODE).asmode()
                        err = bat.read(iter,ERROR).aserr()
                        sp = bat.read(iter,CURRENT_SETPOINT).assetpoint()
                        if mode == 'MODE_STOPPED':
                            print('   CELL'+str(iter)+':',v,'V','0.0000','A',t,tc,'degF/C',c,'Coulombs',mode,'-',err)
                        elif sp == 0 or mode == 'MODE_IDLE' or mode == 'MODE_NO_CELL':
                            print('   CELL'+str(iter)+':',v,'V','0.0000','A',t,tc,'degF/C',c,'Coulombs',mode)
                        else:
                            print('   CELL'+str(iter)+':',v,'V',i,'A',t,tc,'degF/C',c,'Coulombs',mode)

    # COMMANDS BELOW THIS LINE REFERENCE THE ACTIVE BATLAB
    if bp.active_exists(): #checks to make sure the bp.batpool[bp.batactive] exists
        b = bp.batpool[bp.batactive] #get the active batlab object
        with bp.batlocks[bp.batactive]: #aqcuire the lock so the batpool doesn't delete the batlab object out from under you during an un-plug event
            with b.critical_section:
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
                    #try:
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
                        t = '{:2.0f}'.format(b.read(iter,TEMPERATURE).astemperature(b.R,b.B))
                        tc = '{:2.0f}'.format((float(t)-32)*5.0/9.0)
                        chg = b.charge(iter)
                        c = '{:6.0f}'.format(chg)
                        mode = b.read(iter,MODE).asmode()
                        err = b.read(iter,ERROR).aserr()
                        sp = b.read(iter,CURRENT_SETPOINT).assetpoint()
                        if mode == 'MODE_STOPPED':
                            print('CELL'+str(iter)+':',v,'V','0.0000','A',t,tc,'degF/C',c,'Coulombs',mode,'-',err)
                        elif sp == 0 or mode == 'MODE_IDLE' or mode == 'MODE_NO_CELL':
                            print('CELL'+str(iter)+':',v,'V','0.0000','A',t,tc,'degF/C',c,'Coulombs',mode)
                        else:
                            print('CELL'+str(iter)+':',v,'V',i,'A',t,tc,'degF/C',c,'Coulombs',mode)
                    #except:
                    #    print("Invalid Usage.")

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
                            #sp = '{:.4f}'.format(b.read(iter,CURRENT_SETPOINT).assetpoint())
                            sp = '{:.4f}'.format(b.setpoints[iter]/128.0)
                            vh = '{:.4f}'.format(b.read(iter,VOLTAGE_LIMIT_CHG).asvoltage())
                            vl = '{:.4f}'.format(b.read(iter,VOLTAGE_LIMIT_DCHG).asvoltage())
                            ih = '{:.4f}'.format(b.read(iter,CURRENT_LIMIT_CHG).ascurrent())
                            il = '{:.4f}'.format(b.read(iter,CURRENT_LIMIT_DCHG).ascurrent())
                            th = '{:.1f}'.format(b.read(iter,TEMP_LIMIT_CHG).astemperature(b.R,b.B))
                            tl = '{:.1f}'.format(b.read(iter,TEMP_LIMIT_DCHG).astemperature(b.R,b.B))
                            print('CELL'+str(iter)+':',sp,'A setpoint,',vh,'V CHG,',vl,'V DISCHG,',ih,'A CHG,',il,'A DISCHG,',th,'degF CHG,',tl,'degF DISCHG')
                    except:
                        print("Invalid Usage.")

                if p[0] == 'lowcurrent':
                    if len(p) > 1:
                        current = eval(p[1])
                    b.write(UNIT,ZERO_AMP_THRESH,batlab.encoder.Encoder(current).ascurrent())

                if p[0] == 'impedance' and len(p) > 1:
                    try:
                        cell = eval(p[1])
                        if b.channel[cell].is_testing():
                            print("Ignoring command - test running on this channel")
                            return
                        z = b.impedance(cell)
                        print('Impedance:',z,'Ohms')
                    except:
                        print('Impedance Measurement Could not be taken - check that cell is present')

                if p[0] == 'charge' and len(p) > 1:
                    try:
                        if str(p[1]) == 'all':
                            for cell in range(0,4):
                                if b.channel[cell].is_testing():
                                    print("Ignoring command - test running on this channel")
                                    continue
                                if(len(p) > 2):
                                    b.write(cell,CURRENT_SETPOINT,batlab.encoder.Encoder(eval(p[2])).assetpoint())
                                b.write(cell,ERROR,0)
                                
                                #in <= V3 firmware, a race condition exists between the charge relay and the current setpoint. We need to wait 10ms for the relay to click.
                                sp = b.read(cell,CURRENT_SETPOINT).data
                                b.write(cell,CURRENT_SETPOINT,0)
                                b.write(cell,MODE,MODE_CHARGE)
                                sleep(0.01)
                                b.write(cell,CURRENT_SETPOINT,sp)
                        else:
                            cell = int(eval(p[1]))
                            if b.channel[cell].is_testing():
                                print("Ignoring command - test running on this channel")
                                return
                            if(len(p) > 2):
                                b.write(cell,CURRENT_SETPOINT,batlab.encoder.Encoder(eval(p[2])).assetpoint())
                            b.write(cell,ERROR,0)
                            
                            #in <= V3 firmware, a race condition exists between the charge relay and the current setpoint. We need to wait 10ms for the relay to click.
                            sp = b.read(cell,CURRENT_SETPOINT).data
                            b.write(cell,CURRENT_SETPOINT,0)
                            b.write(cell,MODE,MODE_CHARGE)
                            sleep(0.01)
                            b.write(cell,CURRENT_SETPOINT,sp)
                    except:
                        print("Invalid Usage.")

                if p[0] == 'sinewave' and len(p) > 1:
                    try:
                        cell = int(eval(p[1]))
                        if b.channel[cell].is_testing():
                            print("Ignoring command - test running on this channel")
                            return
                        if(len(p) > 2):
                            b.write(UNIT,SINE_FREQ,batlab.encoder.Encoder(eval(p[2])).asfreq())
                        b.write(cell,ERROR,0)
                        b.write(cell,MODE,MODE_IMPEDANCE)
                    except:
                        print("Invalid Usage.")

                if p[0] == 'discharge' and len(p) > 1:
                    try:
                        if str(p[1]) == 'all':
                            if(len(p) > 2):
                                b.write(0,CURRENT_SETPOINT,batlab.encoder.Encoder(eval(p[2])).assetpoint())
                                b.write(1,CURRENT_SETPOINT,batlab.encoder.Encoder(eval(p[2])).assetpoint())
                                b.write(2,CURRENT_SETPOINT,batlab.encoder.Encoder(eval(p[2])).assetpoint())
                                b.write(3,CURRENT_SETPOINT,batlab.encoder.Encoder(eval(p[2])).assetpoint())
                            b.write(0,ERROR,0)
                            b.write(1,ERROR,0)
                            b.write(2,ERROR,0)
                            b.write(3,ERROR,0)
                            b.write(0,MODE,MODE_DISCHARGE)
                            b.write(1,MODE,MODE_DISCHARGE)
                            b.write(2,MODE,MODE_DISCHARGE)
                            b.write(3,MODE,MODE_DISCHARGE)
                        
                        else:
                            cell = int(eval(p[1]))
                            # if b.channel[cell].is_testing():
                            # print("Ignoring command - test running on this channel")
                            # return
                            
                            if(len(p) > 2):
                                b.write(cell,CURRENT_SETPOINT,batlab.encoder.Encoder(eval(p[2])).assetpoint())
                            b.write(cell,ERROR,0)
                            b.write(cell,MODE,MODE_DISCHARGE)
                    except:
                        print("Invalid Usage.")

                if p[0] == 'stop':
                    if(len(p) > 1):
                        try:
                            cell = int(eval(p[1]))
                            b.write(cell,MODE,MODE_STOPPED)
                            b.write(cell,ERROR,0)
                            b.channel[cell].end_test()
                        except:
                            print("Invalid Usage.")
                    else:
                        b.write(CELL0,MODE,MODE_STOPPED)
                        b.channel[CELL0].end_test()
                        b.write(CELL0,ERROR,0)
                        b.write(CELL1,MODE,MODE_STOPPED)
                        b.channel[CELL1].end_test()
                        b.write(CELL1,ERROR,0)
                        b.write(CELL2,MODE,MODE_STOPPED)
                        b.channel[CELL2].end_test()
                        b.write(CELL2,ERROR,0)
                        b.write(CELL3,MODE,MODE_STOPPED)
                        b.channel[CELL3].end_test()
                        b.write(CELL3,ERROR,0)

                if p[0] == 'reset':
                    if(len(p) > 1):
                        try:
                            cell = int(eval(p[1]))
                            b.channel[cell].end_test()
                            b.write(cell,MODE,MODE_IDLE)
                        except:
                            print("Invalid Usage.")
                    else:
                        b.channel[CELL0].end_test()
                        b.channel[CELL1].end_test()
                        b.channel[CELL2].end_test()
                        b.channel[CELL3].end_test()
                        b.write(CELL0,MODE,MODE_IDLE)
                        b.write(CELL1,MODE,MODE_IDLE)
                        b.write(CELL2,MODE,MODE_IDLE)
                        b.write(CELL3,MODE,MODE_IDLE)

                if p[0] == 'firmware' and len(p) > 1:

                    if p[1] == 'load' and len(p) > 2:
                        b.firmware_bootload(p[2]) # The entire bootload procedure is a library function

                    if p[1] == 'update':
                        b.firmware_update()

                    if p[1] == 'check':
                        ver,filename = b.firmware_check(False) # firmware_check(True) checks AND downloads image
                        print("Latest version is:",ver)
                
                if p[0] == 'recover' and len(p) > 1:
                    b.calibration_recover(p[1])

                if p[0] == 'cycletest' and len(p) > 2:
                    TT_DISCHARGE = 0
                    TT_CYCLE = 1
                    #try:
                    if p[1] == 'all':
                        if len(p) > 5:
                            for cell in range(0,4):
                                if b.channel[cell].is_testing():
                                    print("Can't start test - Test is already running on this channel")
                                    continue
                                b.channel[cell].start_test(p[2+cell],TT_CYCLE)
                        else:
                            print("Invalid Usage.")
                            return
                    else:
                        cell = int(eval(p[1]))
                        if b.channel[cell].is_testing():
                            print("Can't start test - Test is already running on this channel")
                            return
                        b.channel[cell].start_test(p[2],TT_CYCLE)
                    #except:
                    #    print("Invalid Usage.")
                        

                if p[0] == 'dischargetest' and len(p) > 2:
                    TT_DISCHARGE = 0
                    TT_CYCLE = 1
                    try:
                        cell = int(eval(p[1]))
                        if b.channel[cell].is_testing():
                            print("Can't start test - Test is already running on this channel")
                            return
                        if len(p) > 3:
                            timeout = eval(p[3])
                        else:
                            timeout = None
                            b.channel[cell].start_test(p[2],TT_DISCHARGE,timeout)
                    except:
                        print("Invalid Usage.")

    else:
        if bp.batactive == '':
            print('No Batlab Currently Set As Active')
        else:
            print('Batlab on ' + bp.batactive + ' not found')
                
if __name__=="__main__":
    batlabutil()
