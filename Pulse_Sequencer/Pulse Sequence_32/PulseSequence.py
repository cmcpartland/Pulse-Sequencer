from PulseChannel import PulseChannel
import numpy as np
import ctypes
           
class PulseSequence:
       
    def __init__(self, num_of_channels=0):
        self.num_of_channels = num_of_channels
        self.num_of_wait_events = 0
        self.channels = []
        self.pulse_channel_indices = []
        self.wait_events = []
        # latest_sequence_event is the last time that a channel is turned off
        self.latest_sequence_event = 0
        self.first_sequence_event = 0
        
        
        # constants defined by spincore
        self._PULSE_PROGRAM  = 0
        self._CONTINUE       = 0
        self._STOP           = 1
        self._LOOP           = 2
        self._END_LOOP       = 3
        self._LONG_DELAY     = 7
        self._WAIT           = 8
        self._BRANCH         = 6
        self._ALL_FLAGS_ON   = 0x1FFFFF
        self._ON             = 0xE00000
        self._ONE_PERIOD     = 0x200000
        self._TWO_PERIOD     = 0x400000
        self._THREE_PERIOD   = 0x600000
        self._FOUR_PERIOD    = 0x800000
        self._FIVE_PERIOD    = 0xA00000
        self._SIX_PERIOD     = 0xC00000 
        self._CHANNELS = 21
        
    def addChannel(self):
        self.num_of_channels += 1
        if self.num_of_channels != 1:
            channel = PulseChannel(pulse_channel_index = self.channels[-1].pulse_channel_index+1)
        else:  
            channel = PulseChannel()
        self.channels.append(channel)
        self.pulse_channel_indices.append(channel.pulse_channel_index)
        self.setLatestSequenceEvent()
        self.setFirstSequenceEvent()

    def deleteChannel(self, index):
        if self.num_of_channels > 0:
            self.channels.pop(index)
            self.num_of_channels -= 1
            self.pulse_channel_indices.pop(index)
            self.setLatestSequenceEvent()
            self.setFirstSequenceEvent()
            return True
        else:
            return False
    
    def addWaitEvent(self, time):
        self.wait_events.append(float(time))
        self.num_of_wait_events += 1
        self.wait_events.sort()
        print self.wait_events
        self.setLatestSequenceEvent()
        self.setFirstSequenceEvent()
    
    def deleteWaitEvent(self, index):
        self.wait_events.pop(index)
        self.num_of_wait_events -= 1
        self.wait_events.sort()
        self.setLatestSequenceEvent()
        self.setFirstSequenceEvent()
        
    def getFirstSequenceEvent(self):
        self.setFirstSequenceEvent()
        return self.first_sequence_event
        
    def setFirstSequenceEvent(self):
        if self.num_of_channels > 1:
            temp_channels = []
            for channel in self.channels:
                channel.setFirstChannelEvent()
                if channel.num_of_pulse_trains > 0:
                    temp_channels.append(channel)
            #    if channel.first_channel_event < self.first_sequence_event:
            #        self.first_sequence_event = channel.first_channel_event
            if len(temp_channels) > 0:
                self.first_sequence_event = sorted(temp_channels, key=lambda x: x.first_channel_event)[0].first_channel_event
            else:
                self.first_sequence_event = 0
        if self.num_of_wait_events > 0:
            if float(self.wait_events[0]) < self.first_sequence_event:
                self.first_sequence_event = float(self.wait_events[0])        
    
    def setLatestSequenceEvent(self):
        self.latest_sequence_event = 0
        for i in range(self.num_of_channels):
            if self.channels[i].latest_channel_event > self.latest_sequence_event:
                self.latest_sequence_event = self.channels[i].latest_channel_event
        if self.num_of_wait_events > 0:
            if float(self.wait_events[-1]) > self.latest_sequence_event:
                self.latest_sequence_event = float(self.wait_events[-1])
                
    def convertSequenceToBinaryInstructions(self, inf_loop, num_of_loops):
        self.setFirstSequenceEvent()
        self.setLatestSequenceEvent()
        #Create the event - an event occurs when a channel is turned on or off.
        channel_events = []
        for channel in self.channels:
            pulse_on_times = []
            pulse_widths = []
            for i in range(channel.num_of_pulse_trains):
                pulse_on_times += channel.pulse_trains[i].pulse_on_times
                pulse_widths += channel.pulse_trains[i].pulse_widths
            num_of_channel_events = len(pulse_on_times)*2
            channel_event_times = np.zeros(num_of_channel_events)
            channel_event_flags = np.zeros(num_of_channel_events)
            for i in range(num_of_channel_events/2):
                channel_event_times[2*i] = pulse_on_times[i]
                channel_event_flags[2*i] = 1
                channel_event_times[2*i+1] = pulse_on_times[i] + pulse_widths[i]
                channel_event_flags[2*i+1] = 0
            channel_events.append([channel_event_times, channel_event_flags, channel.pulse_channel_index])
            
            
        times = []
        for i in range(self.num_of_channels):
            times.append(channel_events[i][0])
        times = np.concatenate(times)
        
        # Get unique event times to eliminate coincident events.
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
       
        # Define the wait times between each command, aka the 'lengths' parameter. 
        # Default unit for lengths is ns: multiply each length by 1e09
        lengths = []
        for i in range(num_of_unique_events-1):
            lengths.append(round(np.asscalar((unique_event_times[i+1] - unique_event_times[i])*(1.e09)), 1))
        # if first instruction is a pulse, add some wait time to the end equal to the last pulse separation
        if unique_event_times[0] == 0:
            lengths.append(lengths[-2])
        # 
        # flags is currently backwards, i.e. flags[0][0] represents the on-off state of the first pulse event of channel 0,
        # but commands have to be entered in the reverse order, i.e. flag[0][-1] should represent the on-off state of the first pulse
        # event of channel 0. binary_flag_list will be created to reflect this.
        binary_flag_list = []
        int_flag_list = []
        hex_flag_list = []
        for i in range(num_of_unique_events):
            flag_string = '0b'
            for j in range(self._CHANNELS-1, -1, -1):
                flag_string += str(int(flags[i][j]))
            int_flag_list.append(int(flag_string,2))
            binary_flag_list.append(flag_string)
            hex_flag_list.append(hex(int(flag_string,2)))


        # if pulses do not start at t = 0s, wait until the first pulse begins
        # insert an initial command that turns all the channels off until the first pulse event occurs
        if self.getFirstSequenceEvent() != 0.0:
            lengths.insert(0, round(float(self.getFirstSequenceEvent())*1e09, 1))
            hex_flag_list.insert(0,'0x'+'{0:06x}'.format(0).upper())
            int_flag_list.insert(0,0)
            binary_flag_list.insert(0, '0b'+'{0:024b}'.format(0))
            #last flag turns off all the channels, does not have to be included in commands. Last command will loop to first one
            binary_flag_list.pop(-1)
            int_flag_list.pop(-1)
            hex_flag_list.pop(-1)


        # Comment this to remove wait events
        for wait_event in self.wait_events:
            if wait_event > unique_event_times[-1]:
                int_flag_list.append(0)
                int_flag_list.append(0)
                lengths.append(float(unique_event_times[-1] - wait_event)*1e09)
                lengths.append(0.0)
            else:
                insert_index = np.where(unique_event_times > wait_event)[0][0]
                lengths[insert_index] = float(lengths[insert_index] - (unique_event_times[insert_index] - wait_event)*1e09)
                lengths.insert(insert_index+1, float(unique_event_times[insert_index] - wait_event)*1e09)
                lengths.insert(insert_index+1, 0.0)
                int_flag_list.insert(insert_index+1, int_flag_list[insert_index])
                int_flag_list.insert(insert_index+1, 0)
        
        sec2ns = 1e09
        cycles_to_ns = (1 / 400.0) * 1e3 # since clockrate is given in MHz
        min_instruction_length = 5*cycles_to_ns
        LONG_DELAY_TIMESTEP = 500e-09
        seq = []
        instructions = []
        flags_instr = int_flag_list
        lengths_instr = lengths
        num_of_instructions = len(int_flag_list)
        run_time = sum(lengths)*num_of_loops/sec2ns
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
                last_flag_instr += self._ON
            # if short pulse, create the proper flags for this instruction:
            elif last_length_instr < min_instruction_length:
                flags_instr.pop(-1)
                lengths_instr.pop(-1)
                num_of_instructions -= 1
                short_pulse_len = last_length_instr
                if (short_pulse_len < 1.5*cycles_to_ns):
                    bnc_pulse_bits = self._ONE_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 2.5*cycles_to_ns):
                    bnc_pulse_bits = self._TWO_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 3.5*cycles_to_ns):
                    bnc_pulse_bits = self._THREE_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 4.5*cycles_to_ns):
                    bnc_pulse_bits = self._FOUR_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 5*cycles_to_ns):
                    bnc_pulse_bits = self._FIVE_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 5.5*cycles_to_ns):
                    bnc_pulse_bits = self._FIVE_PERIOD
                    inst_len = min_instruction_length + 1*cycles_to_ns
                elif (short_pulse_len < 6*cycles_to_ns):
                    bnc_pulse_bits = self._ON
                    inst_len = min_instruction_length + 1*cycles_to_ns
                elif (short_pulse_len < 7*cycles_to_ns):
                    bnc_pulse_bits = self._ON
                    inst_len = min_instruction_length + 2*cycles_to_ns 
                elif (short_pulse_len < 8*cycles_to_ns):
                    bnc_pulse_bits = self._ON
                    inst_len = min_instruction_length + 3*cycles_to_ns 
                last_length_instr = inst_len
                last_flag_instr += bnc_pulse_bits
            # else, instruction must be removed:
            else:
                flags_instr.pop(-1)
                lengths_instr.pop(-1)
                num_of_instructions -= 1
                last_flag_instr += self._ON
            
        if not inf_loop:
            # if first instruction is a regular instruction, pop it and use it as the LOOP command
            if first_length_instr < LONG_DELAY_TIMESTEP*sec2ns + min_instruction_length:
                seq.append('%s, LOOP, %s, %f ns' %('{0:024b}'.format(first_flag_instr + self._ON), num_of_loops, first_length_instr))
                instructions.append((first_flag_instr, self._LOOP, num_of_loops, first_length_instr))
                flags_instr.pop(0)
                lengths_instr.pop(0)
                num_of_instructions -= 1
            # else, if first instruction is a long delay:
            else:
                # add a dummy instruction with length min_instruction_length to begin loop, then subtract min_instruction_length from original long_delay length
                lengths_instr[0] -= min_instruction_length
                seq.append('%s, LOOP, %s, %f ns' %('{0:024b}'.format(0 + self._ON), num_of_loops, min_instruction_length))
                instructions.append((0, self._LOOP, num_of_loops, min_instruction_length))
  
        instructions_range = range(num_of_instructions)
        for inst in instructions_range:
            flag_instr = flags_instr[inst]
            length_instr = lengths_instr[inst]

            # wait event
            if length_instr == 0.0:
                seq.append('0, WAIT, 0, 0 ns')
                instructions.append((flag_instr, self._WAIT, 0, length_instr))
                
            elif length_instr > (2 ** 8)*cycles_to_ns:
                
                # LONG_DELAY
                # Disable short-pulse feature
                flag_instr += self._ON
                # number of cycles per LONG_DELAY_TIMESTEP
                cycles_per_LD = round(LONG_DELAY_TIMESTEP * sec2ns / cycles_to_ns)
                # how many long delays to make up length_instr? find that quotient
                long_delay_int = int((length_instr/sec2ns)// LONG_DELAY_TIMESTEP)
                # how much time remaining after that?
                remaining_time = length_instr - long_delay_int*LONG_DELAY_TIMESTEP*sec2ns
                
                if (abs(remaining_time - LONG_DELAY_TIMESTEP*sec2ns) < cycles_to_ns):
                    # making sure number of continue cycles is a good value
                    # if remaining_time is equal to LONG_DELAY_TIMESTEP to within one cycle, add one long delay instruction
                    # else, if remaining_time is equal to zero to within one cyce, set remaining_time equal to zero. 
                    # These situations most likely occur because of rounding errors
                    long_delay_int += 1
                    remaining_time -= LONG_DELAY_TIMESTEP*sec2ns
                elif (abs(remaining_time - 0) < cycles_to_ns):
                    remaining_time = 0.0
                if long_delay_int > 1:
                    seq.append('%s, LONG_DELAY, %s, %f ns' %('{0:024b}'.format(flag_instr), str(long_delay_int), LONG_DELAY_TIMESTEP*sec2ns))
                    instructions.append((flag_instr, self._LONG_DELAY, long_delay_int, LONG_DELAY_TIMESTEP*sec2ns))
                else:
                    seq.append('%s, CONTINUE, %s, %f ns' %('{0:024b}'.format(flag_instr), str(0), LONG_DELAY_TIMESTEP*sec2ns))
                    instructions.append((flag_instr, self._CONTINUE, 0, LONG_DELAY_TIMESTEP*sec2ns))      
                if remaining_time > 0:
                    seq.append('%s, CONTINUE, %s, %f ns' %('{0:024b}'.format(flag_instr), str(0),  remaining_time))
                    instructions.append((flag_instr, self._CONTINUE, 0, remaining_time))
            
            elif (length_instr >= min_instruction_length and length_instr <= (2 ** 8)*cycles_to_ns):  
                # this is a regular instruction
                # Disable short-pulse feature
                flag_instr += self._ON
                long_delay_int = 0
                continue_cycles = length_instr
                seq.append('%s, CONTINUE, %s, %f ns' %('{0:024b}'.format(flag_instr), str(0), length_instr))      
                instructions.append((flag_instr, self._CONTINUE, 0, length_instr))
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
                    bnc_pulse_bits = self._ONE_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 2.5*cycles_to_ns):
                    bnc_pulse_bits = self._TWO_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 3.5*cycles_to_ns):
                    bnc_pulse_bits = self._THREE_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 4.5*cycles_to_ns):
                    bnc_pulse_bits = self._FOUR_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 5*cycles_to_ns):
                    bnc_pulse_bits = self._FIVE_PERIOD
                    inst_len = min_instruction_length
                elif (short_pulse_len < 5.5*cycles_to_ns):
                    bnc_pulse_bits = self._FIVE_PERIOD
                    inst_len = min_instruction_length + 1*cycles_to_ns
                elif (short_pulse_len < 6*cycles_to_ns):
                    bnc_pulse_bits = self._ON
                    inst_len = min_instruction_length + 1*cycles_to_ns
                elif (short_pulse_len < 7*cycles_to_ns):
                    bnc_pulse_bits = self._ON
                    inst_len = min_instruction_length + 2*cycles_to_ns 
                elif (short_pulse_len < 8*cycles_to_ns):
                    bnc_pulse_bits = self._ON
                    inst_len = min_instruction_length + 3*cycles_to_ns
                if inst < num_of_instructions-1:
                    # if next low time is shorter than LONG_DELAY, incorporate this low time into the short-pulse instruction and then remove next low time
                    if lengths_instr[inst+1] < LONG_DELAY_TIMESTEP*sec2ns - short_pulse_len:
                        inst_len = lengths_instr[inst+1] + short_pulse_len 
                        lengths_instr.pop(inst+1)
                        flags_instr.pop(inst+1)
                        num_of_instructions -= 1
                        instructions_range.pop(-1)
                    # else, next low time is a LONG_DELAY. In this case, subtract the mandatory low time of the short-pulse instruction from the next low time
                    else:
                        lengths_instr[inst+1] -= (min_instruction_length - short_pulse_len)

                seq.append('%s, CONTINUE, %s, %f ns' %('{0:024b}'.format(flag_instr+bnc_pulse_bits), str(0), inst_len))
                instructions.append((flag_instr + bnc_pulse_bits, self._CONTINUE, 0, inst_len))
    
        # end of the instruction loop
            
        if inf_loop :
            seq.append('%s, BRANCH, 0, %f ns' % ('{0:024b}'.format(last_flag_instr), last_length_instr))
            instructions.append((last_flag_instr, self._BRANCH, 'start', last_length_instr))
        else:
            seq.append('%s, END_LOOP, 0, %f ns' % ('{0:024b}'.format(last_flag_instr), last_length_instr))
            instructions.append((last_flag_instr, self._END_LOOP, 'start', last_length_instr))
        
        # Check for bad instructions (instructions s.t. length < 5 clock cycles of PB board)
        for inst in instructions:
            if inst[3] < min_instruction_length:
                print 'Bad instruction found! Stopping sequence...'
                print inst[3]
                found_bad_instruction = True
                break
        
        
        return instructions, seq, run_time, found_bad_instruction
 