import pickle
import sys
import SpinCorePulseBlaster

params = sys.argv
run_time = params[0]
clock_freq = params[1]
libraryFileName = 'spinapi64.dll'
scpb = SpinCorePulseBlaster(libraryFile = libraryFileName)
try:
    spcb.close()
except RuntimeError:
    pass
scpb.init()
scpb.setclock(clock_freq)
spcb.stop()
spcb.start()
time.sleep(float(run_time))
spcb.stop()
spcb.close()




