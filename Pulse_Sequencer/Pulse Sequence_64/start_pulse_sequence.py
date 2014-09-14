from SpinCorePulseBlaster import *
import time
import sys
import struct

# This script will initiailize the PB board and begin running whatever instructions have been loaded onto it. 
input_params = sys.argv
clock = float(input_params[1])
run_time = float(input_params[2])

print 'clock: ', clock
print 'run_time: ', run_time

if struct.calcsize("P") * 8 == 64:
    libraryFileName = 'spinapi64.dll'
else:
    libraryFileName = 'spinapi.dll'
pb = SpinCorePulseBlaster(libraryFile = libraryFileName)
try:
    pb.close()
except RuntimeError:
    print 'Board already closed'

if pb.init() == None:
    print 'Board initialized'
if pb.setclock(clock) == None:
    print 'PB clock set to: %f MHz'% clock
pb.stop()
if pb.start() == None:
    print 'Pulse sequence started, running for %f seconds' % run_time
time.sleep(run_time)
pb.stop()
if pb.close() == None:
    print 'Board closed'
print 'Pulse sequence finished'

