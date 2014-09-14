import ctypes
from SpinCorePulseBlaster import *
import time
import sys
import numpy

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

filename = sys.argv[0]
file = open(filename, 'r')
num_of_loops = float(file.readline().strip())
#for the purposes of this script, assume infinite loop will not be used
inf_loop = False
data_lines = file.readlines()
channels_strings = data_lines[0::3]
channels = []
for channel_string in channel_strings:
    channels.append(float(channel_string.strip()))
#pot_per_channel is a list of lists, and each inner list, pot_per_channel[i], contains the pulse_on_times for Channel i
pot_per_channel = data_lines[1::3]
pw_per_channel = data_lines[2::3]


channel_events = []
#channels contains the list of channels used [0,1,2,3,4...]
for channel in channels:
    pulse_on_times = pot_per_channel[channel].split(',')
    pulse_widths = pw_per_channel[channel].split(',')
    num_of_channel_events = len(pulse_on_times)*2
    channel_event_times = np.zeros(num_of_channel_events)
    channel_event_flags = np.zeros(num_of_channel_events)
    for i in range(num_of_channel_events/2):
        channel_event_times[2*i] = pulse_on_times[i]
        channel_event_flags[2*i] = 1
        channel_event_times[2*i+1] = pulse_on_times[i] + pulse_widths[i]
        channel_event_flags[2*i+1] = 0
    channel_events.append([channel_event_times, channel_event_flags, channel])
    
times = []
for i in range(len(channels)):
    times.append(channel_events[i][0])
times = np.concatenate(times)

unique_event_times, unique_indices = np.unique(times, return_index=True)
num_of_unique_events = len(unique_event_times)

flags = np.zeros((num_of_unique_events, 24))

for channel_event in channel_events:
    for i in range(num_of_unique_events):
        coincident_event_index = np.where(channel_event[0] == unique_event_times[i])[0]
        if len(coincident_event_index) > 0:
            ind = coincident_event_index[0]
            flags[i][channel_event[2]] = channel_event[1][coincident_event_index]
        else:
            flags[i][channel_event[2]] = flags[i-1][channel_event[2]]

lengths = []
for i in range(num_of_unique_events-1):
    lengths.append(round(np.asscalar((unique_event_times[i+1] - unique_event_times[i])*(1.e09)), 1))
# if first instruction is a pulse, add some wait time to the end equal to the last pulse separation
if unique_event_times[0] == 0:
    lengths.append(lengths[-2])

binary_flag_list = []
int_flag_list = []
hex_flag_list = []
for i in range(num_of_unique_events):
    flag_string = '0b'
    for j in range(CHANNELS-1, -1, -1):
        flag_string += str(int(flags[i][j]))
    int_flag_list.append(int(flag_string,2))
    binary_flag_list.append(flag_string)
    hex_flag_list.append(hex(int(flag_string,2)))         
            
# if pulses do not start at t = 0s, wait until the first pulse begins
# insert an initial command that turns all the channels off until the first pulse event occurs
if not 0.0 in unique_event_times:
    lengths.insert(0, round(float(self.getFirstSequenceEvent())*1e09, 1))
    hex_flag_list.insert(0,'0x'+'{0:06x}'.format(0).upper())
    int_flag_list.insert(0,0)
    binary_flag_list.insert(0, '0b'+'{0:024b}'.format(0))
    #last flag turns off all the channels, does not have to be included in commands. Last command will loop to first one
    binary_flag_list.pop(-1)
    int_flag_list.pop(-1)
    hex_flag_list.pop(-1)
            
sec2ns = 1e09
cycles_to_ns = (1 / 400.0) * 1e3 # since clockrate is given in MHz
min_instruction_length = 5*cycles_to_ns
LONG_DELAY_TIMESTEP = 500e-09
seq = []
instructions = []
flags_instr = int_flag_list
lengths_instr = lengths
num_of_instructions = len(int_flag_list)
run_time = sum(lengths)/sec2ns
found_bad_instruction = False

# Possible chance that instruction set is a loop, but first instruction should be a long delay.
# Solution: split the first instruction into two instructions, A and B. A has the same flags as the
# the first instruction and it begins the loop. B also has the same flags, but 5*cycles_to_ns is
# subtracted from its length. Do the same thing for the last instruction
first_flag_instr = flags_instr[0]
first_length_instr = lengths_instr[0]
last_flag_instr = flags_instr[-1]
last_length_instr = lengths_instr[-1]


# If first instruction is to keep all the channels low:
if first_flag_instr == 0:
    # Last instruction must be popped from lists because it is unique, it is used to signify the branch or the end of the loop
    # If last instruction length is long enough, subtract min_instruction_length from it
    #  since the final instruction  (branch or end_loop) will have length = min_instruction_length. This instruction does not need to be removed
    if last_length_instr > 2*min_instruction_length:
        lengths_instr[-1] -= min_instruction_length
        last_length_instr = min_instruction_length
        last_flag_instr += ON
    # if short pulse, create the proper flags for this instruction:
    elif last_length_instr < min_instruction_length:
        if last_length_instr == 0:
            last_flags_instr = flags_instr.pop(-1)
            last_lengths_instr = lengths_instr.pop(-1)
            lengths_instr.append(0)
            flags_instr.append(0)
        else:
            flags_instr.pop(-1)
            lengths_instr.pop(-1)
            num_of_instructions -= 1

        short_pulse_len = last_length_instr
        if (short_pulse_len < 1.5*cycles_to_ns):
            bnc_pulse_bits = ONE_PERIOD
            inst_len = min_instruction_length
        elif (short_pulse_len < 2.5*cycles_to_ns):
            bnc_pulse_bits = TWO_PERIOD
            inst_len = min_instruction_length
        elif (short_pulse_len < 3.5*cycles_to_ns):
            bnc_pulse_bits = THREE_PERIOD
            inst_len = min_instruction_length
        elif (short_pulse_len < 4.5*cycles_to_ns):
            bnc_pulse_bits = FOUR_PERIOD
            inst_len = min_instruction_length
        elif (short_pulse_len < 5*cycles_to_ns):
            bnc_pulse_bits = FIVE_PERIOD
            inst_len = min_instruction_length
        elif (short_pulse_len < 5.5*cycles_to_ns):
            bnc_pulse_bits = FIVE_PERIOD
            inst_len = min_instruction_length + 1*cycles_to_ns
        elif (short_pulse_len < 6*cycles_to_ns):
            bnc_pulse_bits = ON
            inst_len = min_instruction_length + 1*cycles_to_ns
        elif (short_pulse_len < 7*cycles_to_ns):
            bnc_pulse_bits = ON
            inst_len = min_instruction_length + 2*cycles_to_ns 
        elif (short_pulse_len < 8*cycles_to_ns):
            bnc_pulse_bits = ON
            inst_len = min_instruction_length + 3*cycles_to_ns 
        last_length_instr = inst_len
        last_flag_instr += bnc_pulse_bits
    
    # else, instruction must be removed:
    else:
        flags_instr.pop(-1)
        lengths_instr.pop(-1)
        num_of_instructions -= 1
        last_flag_instr += ON
    
if not inf_loop:
    # if first instruction is a regular instruction, pop it and use it as the LOOP command
    if first_length_instr < LONG_DELAY_TIMESTEP*sec2ns + min_instruction_length:
        seq.append('%s, LOOP, %s, %f ns' %('{0:024b}'.format(first_flag_instr + ON), num_of_loops, first_length_instr))
        instructions.append((first_flag_instr, LOOP, num_of_loops, first_length_instr))
        flags_instr.pop(0)
        lengths_instr.pop(0)
        num_of_instructions -= 1
    # else, if first instruction is a long delay:
    else:
        # add a dummy instruction with length min_instruction_length to begin loop, then subtract min_instruction_length from original long_delay length
        lengths_instr[0] -= min_instruction_length
        seq.append('%s, LOOP, %s, %f ns' %('{0:024b}'.format(0 + ON), num_of_loops, min_instruction_length))
        instructions.append((0, LOOP, num_of_loops, min_instruction_length))

instructions_range = range(num_of_instructions)
for inst in instructions_range:
    flag_instr = flags_instr[inst]
    length_instr = lengths_instr[inst]

    # wait event
    if length_instr == 0.0:
        seq.append('0, WAIT, 0, 0 ns')
        instructions.append((flag_instr, WAIT, 0, length_instr))
        
    elif length_instr > (2 ** 8)*cycles_to_ns:
        
        # LONG_DELAY
        # Disable short-pulse feature
        flag_instr += ON
        # number of cycles per LONG_DELAY_TIMESTEP
        cycles_per_LD = round(LONG_DELAY_TIMESTEP * sec2ns / cycles_to_ns)
        # how many long delays to make up length_instr? find that quotient
        long_delay_int = int((length_instr/sec2ns)// LONG_DELAY_TIMESTEP)
        # how much time remaining after that?
        remaining_time = round(length_instr - long_delay_int*LONG_DELAY_TIMESTEP*sec2ns, 1)
        
        if (abs(remaining_time - LONG_DELAY_TIMESTEP*sec2ns) < cycles_to_ns):
            # making sure number of continue cycles is a good value
            # if remaining_time is equal to LONG_DELAY_TIMESTEP to within one cycle, add one long delay instruction
            # else, if remaining_time is equal to zero to within one cyce, set remaining_time equal to zero. 
            # These situations most likely occur because of rounding errors
            long_delay_int += 1
            remaining_time -= round(LONG_DELAY_TIMESTEP*sec2ns,1)
        elif (abs(remaining_time - 0) < cycles_to_ns):
            remaining_time = 0.0
        if long_delay_int > 1:
            seq.append('%s, LONG_DELAY, %s, %f ns' %('{0:024b}'.format(flag_instr), str(long_delay_int), LONG_DELAY_TIMESTEP*sec2ns))
            instructions.append((flag_instr, LONG_DELAY, long_delay_int, LONG_DELAY_TIMESTEP*sec2ns))
        else:
            seq.append('%s, CONTINUE, %s, %f ns' %('{0:024b}'.format(flag_instr), str(0), LONG_DELAY_TIMESTEP*sec2ns))
            instructions.append((flag_instr, CONTINUE, 0, LONG_DELAY_TIMESTEP*sec2ns))      
        if remaining_time > 0:
            seq.append('%s, CONTINUE, %s, %f ns' %('{0:024b}'.format(flag_instr), str(0),  remaining_time))
            instructions.append((flag_instr, CONTINUE, 0, remaining_time))
    
    elif (length_instr >= min_instruction_length and length_instr <= (2 ** 8)*cycles_to_ns):  
        # this is a regular instruction
        # Disable short-pulse feature
        flag_instr += ON
        long_delay_int = 0
        continue_cycles = length_instr
        seq.append('%s, CONTINUE, %s, %f ns' %('{0:024b}'.format(flag_instr), str(0), length_instr))      
        instructions.append((flag_instr, CONTINUE, 0, length_instr))
    elif length_instr < cycles_to_ns:
        # this is a bad instruction
        seq.append('----ignoring zero delay----')
    
    # if short pulse:
    elif 0 < length_instr < min_instruction_length:
        # this could be short pulse instruction
        short_pulse_len = length_instr
        seq.append('#### short pulses ####')
        # now have to use the same algorithm as in my C code
        #  if the delay value supplied to pb_inst_pbonly() is INST_LEN
        #   then the delay count written to the PB VLIW is 2
        #  hence changing the bits 21-23 will change the length of
        # pulses on BNC0-3
        # Since the pb_inst_pbonly function works by taking the length field and doing (length*clock_freq)-4
        #   to write onto the delay count, we invert that to get the delay
        #  count value we need.
        if flag_instr == 0:
            bnc_pulse_bits = 0
        elif (short_pulse_len < 1.5*cycles_to_ns):
            bnc_pulse_bits = ONE_PERIOD
            inst_len = min_instruction_length
        elif (short_pulse_len < 2.5*cycles_to_ns):
            bnc_pulse_bits = TWO_PERIOD
            inst_len = min_instruction_length
        elif (short_pulse_len < 3.5*cycles_to_ns):
            bnc_pulse_bits = THREE_PERIOD
            inst_len = min_instruction_length
        elif (short_pulse_len < 4.5*cycles_to_ns):
            bnc_pulse_bits = FOUR_PERIOD
            inst_len = min_instruction_length
        elif (short_pulse_len < 5*cycles_to_ns):
            bnc_pulse_bits = FIVE_PERIOD
            inst_len = min_instruction_length
        elif (short_pulse_len < 5.5*cycles_to_ns):
            bnc_pulse_bits = FIVE_PERIOD
            inst_len = min_instruction_length + 1*cycles_to_ns
        elif (short_pulse_len < 6*cycles_to_ns):
            bnc_pulse_bits = ON
            inst_len = min_instruction_length + 1*cycles_to_ns
        elif (short_pulse_len < 7*cycles_to_ns):
            bnc_pulse_bits = ON
            inst_len = min_instruction_length + 2*cycles_to_ns 
        elif (short_pulse_len < 8*cycles_to_ns):
            bnc_pulse_bits = ON
            inst_len = min_instruction_length + 3*cycles_to_ns
        if inst < num_of_instructions-1:
            # if next low time is shorter than LONG_DELAY, incorporate this low time into the short-pulse instruction and then remove next low time
            if lengths_instr[inst+1] < LONG_DELAY_TIMESTEP*sec2ns - short_pulse_len:
                inst_len = round(lengths_instr[inst+1] + short_pulse_len, 1)
                lengths_instr.pop(inst+1)
                flags_instr.pop(inst+1)
                num_of_instructions -= 1
                instructions_range.pop(-1)
            # else, next low time is a LONG_DELAY. In this case, subtract the mandatory low time of the short-pulse instruction from the next low time
            else:
                lengths_instr[inst+1] -= round((min_instruction_length - short_pulse_len), 1)

        seq.append('%s, CONTINUE, %s, %f ns' %('{0:024b}'.format(flag_instr+bnc_pulse_bits), str(0), inst_len))
        instructions.append((flag_instr + bnc_pulse_bits, CONTINUE, 0, inst_len))

# end of the instruction loop
    
if inf_loop :
    seq.append('%s, BRANCH, 0, %f ns' % ('{0:024b}'.format(last_flag_instr), last_length_instr))
    instructions.append((last_flag_instr, BRANCH, 'start', last_length_instr))
else:
    seq.append('%s, END_LOOP, 0, %f ns' % ('{0:024b}'.format(last_flag_instr), last_length_instr))
    instructions.append((last_flag_instr, END_LOOP, 'start', last_length_instr))

# Check for bad instructions (instructions s.t. length < 5 clock cycles of PB board). The exception is a WAIT command, which has a unique length = 0
for inst in instructions:
    if inst[3] < min_instruction_length and inst[1] != WAIT:
        print 'Bad instruction found!'
        print 'Instruction length: ', inst[3]
        found_bad_instruction = True
        break

    
print 'Initializing'
# No error checking has to be done here, commands can simply be sequential.
# pb object will raise errors if any occur and subprocess will terminate.
print 'Closing Pulse Blaster in case already initialized...'
try:
    pass
    pb.close()
except RuntimeError:
    pass
pb.init()
print 'PulseBlaster board succesfully initiated.'
version = pb.pb_get_version()
print 'Pulse Blaster version: ', version
time.sleep(.1)

pb.setclock(400)
print 'PulseBlaster clock set to 400 MHz'

print 'Loading sequence to PulseBlaster'
pb.start_programming()

flags, op_code, inst_data, length = instructions.pop(0)
start = self.pb.send_instruction(flags, op_code, inst_data, length)
final_flags, final_op_code, final_inst_data, final_length = instructions.pop(-1)
for instruction in instructions:
    flags, op_code, inst_data, length = instruction
    self.pb.send_instruction(flags, op_code, inst_data, length)

final_inst_data = start
self.pb.send_instruction(final_flags, final_op_code, final_inst_data, final_length)

pb.stop_programming()

print 'Starting pulse sequence...'
pb.stop()
pb.start()

#start the sequence, then sleep until the sequence is done repeating
time.sleep(unique_event_times[-1]*num_of_loops)

pb.close()
  

