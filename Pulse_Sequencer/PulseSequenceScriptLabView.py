import sys
import time
from PulseSequenceUI import Communicate_with_PB

filename = sys.argv[0]
ps_file = open(filename, 'rb')
data = pickle.load(ps_file)
date_modified = data[0]
pulse_sequence = data[1]
inf_loop = data[2]
run_time = data[3]
num_of_loops = data[4]
clock_freq = data[5]

PB_communicator = Communicate_with_PB()

PB_communicator.initialize(clock_freq)
PB_communicator.send_sequence(ps, clock_freq, inf_loop, run_time, num_of_loops)
PB_communicator.start_sequence()
time.sleep(float(run_time))
PB_communicator.stop_sequence()
PB_communicator.close()



