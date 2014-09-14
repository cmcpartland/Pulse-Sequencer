import ctypes
from SpinCorePulseBlaster import *
import pickle
import time
import sys

 #constants defined by spincore
PULSE_PROGRAM  = 0
CONTINUE       = 0
STOP           = 1
LOOP           = 2
END_LOOP       = 3
LONG_DELAY     = 7
BRANCH         = 6
ALL_FLAGS_ON   = 0x1FFFFF
ON             = 0xE00000
ONE_PERIOD     = 0x200000
TWO_PERIOD     = 0x400000
THREE_PERIOD   = 0x600000 
FOUR_PERIOD    = 0x800000
FIVE_PERIOD    = 0xA00000
SIX_PERIOD     = 0xC00000 


libraryFileName = 'spinapi64.dll'
try:
    test = ctypes.cdll.LoadLibrary(libraryFileName)
except OSError :
    print 'Necessary dll could not be loaded: ', libraryFileName
    raise 
else:
    pb = SpinCorePulseBlaster(libraryFile = libraryFileName)

    
command = sys.stdin.readline().strip()

if command == 'Initialize':
    print 'Initializing'
    
    
    # No error checking has to be done here, commands can simply be sequential.
    # pb object will raise errors if any occur and subprocess will terminate.
    print 'Closing Pulse Blaster in case already initialized...'
    try:
        pass
        pb.pb_close()
    except RuntimeError:
        sys.stdout.flush()
    pb.pb_init()
    print 'Pulse Blaster board succesfully initiated.'
    sys.stdout.flush()
    version = pb.pb_get_version()
    print 'Pulse Blaster version: ', version
    sys.stdout.flush()
    print 'Closing Pulse Blaster.'
    try:
        pass
        pb.pb_close()
    except RuntimeError:
        sys.stdout.flush()
    time.sleep(2)
    
elif command == 'Start sequence':
    print 'Starting sequence'
    sys.stdout.flush() 
    data = sys.stdin.readline().strip()
    data = pickle.loads(data.replace("\\()", "\n"))
    instructions = data[0]
    clock_freq = float(data[1])
    inf_loop = data[2]
    run_time = float(data[3])
    num_of_loops = int(data[4])
    
    print 'PB clock frequency: ', clock_freq, ' Mhz'
    sys.stdout.flush()
    
    if not inf_loop:
        print 'Number of loops: ', num_of_loops
        sys.stdout.flush()
    
    print 'Loop sequence run time: ', run_time, ' s'
    sys.stdout.flush()
    
    print 'Closing Pulse Blaster in case already initialized...'
    sys.stdout.flush()
    try:
        pass
        pb.pb_close()
    except RuntimeError:
        sys.stdout.flush()
    pb.pb_init()
    print 'Connected to SpinCore Pulse Blaster.'
    pb.pb_setclock(float(clock_freq))
    print 'Clock frequency loaded: %s MHz' % clock_freq
    sys.stdout.flush()
    print '\tStatus:', pb.pb_status()
    sys.stdout.flush()
   
    pb.pb_start_programming()
    
    flags, op_code, inst_data, length = instructions.pop(0)
    start = pb.pb_send_instruction(flags, op_code, inst_data, length)
    final_flags, final_op_code, final_inst_data, final_length = instructions.pop(-1)
    for instruction in instructions:
        flags, op_code, inst_data, length = instruction
        pb.pb_send_instruction(flags, op_code, inst_data, length)
    
    #if inf_loop:
    final_inst_data = start
    pb.pb_send_instruction(final_flags, final_op_code, final_inst_data, final_length)
    
    pb.pb_stop_programming()
    print 'Programming finished.'
    sys.stdout.flush()
    print '\tStatus:', pb.pb_status()
    sys.stdout.flush()

    print 'Starting pulse sequence.'
    sys.stdout.flush()
    
    # Before starting, pb_stop() or pb_reset() must be called
    pb.pb_stop()
    pb.pb_start()
    print '\tStatus:',  pb.pb_status()
    sys.stdout.flush()
    
    
    # If PB is sent a wait instruction, check PB every 1 second to see if the board has been triggered. Else, add 1 second to total run time
    start_time = time.time()
    current_time = start_time
    while current_time < start_time + run_time:
        status = pb.pb_status()
        if 'Waiting' in status:
                time.sleep(1)
                print '\tStatus:', status
                run_time += 1
        else:
            time.sleep(run_time/100.0)
        current_time = time.time()
    

    print 'Stopping pulse sequence.'
    sys.stdout.flush()
    # Send final instruction to PB to turn off all channels. Stopping the PB leaves the TTL states as they were in the last instruction
    pb.pb_start_programming()
    pb.pb_send_instruction(0, 0, 0, 6e03/clock_freq)
    pb.pb_stop_programming()
    pb.pb_stop()
    pb.pb_start()
    time.sleep(6e-06/clock_freq)
    pb.pb_stop()
    print '\tStatus:', pb.pb_status()
    sys.stdout.flush()
    pb.pb_close()


