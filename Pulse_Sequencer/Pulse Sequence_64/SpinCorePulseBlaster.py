import ctypes
import traceback

# A class to creat a SpinCorePulseBlaster object. This class directly uses the functions provided by the spinapi .dll file.
# Use this class to initialize the board, send instructions to it, start/stop the sequence, close the board, etc...
class SpinCorePulseBlaster(object):

# constants defined by spincore
    _PULSE_PROGRAM  = 0
    _CONTINUE       = 0
    _STOP           = 1
    _LOOP           = 2
    _END_LOOP       = 3
    _LONG_DELAY     = 7
    _BRANCH         = 6
    _ALL_FLAGS_ON   = 0x1FFFFF
    _ON             = 0xE00000
    _ONE_PERIOD     = 0x200000
    _TWO_PERIOD     = 0x400000
    _THREE_PERIOD   = 0x600000
    _FOUR_PERIOD    = 0x800000
    _FIVE_PERIOD    = 0xA00000
    _SIX_PERIOD     = 0xC00000 

    def __init__(self, libraryFile='spinapi64.dll', libraryHeader='spinapi.h'):
            self.libraryFile = libraryFile
            self.libraryHeader = libraryHeader
            
            try:
                self._dll = ctypes.cdll.LoadLibrary(libraryFile)
            except OSError:
                #logger.error('Unable to load the pulseblaster library in current path')
                raise
    
    # Check if the command has given an error. If so, print and return the error's description. 
    def chk(self, error):
        """a simple error checking routine"""
        self._dll.pb_get_error.restype = ctypes.c_char_p
        recent_error = self._dll.pb_get_error()
        if error != 0:
            print recent_error
            return recent_error
        else:
            return None
            
    
    # Initialize the PB board. 
    def init(self):
        return self.chk(self._dll.pb_init())

    # Set the clock of the PB board. NOTE: This does not actually set the clock of the PB board. The PB board must
    # be told what its frequency is. setclock() must be called after init()
    def setclock(self,clockrate):
        # newer version of spinapi uses function pb_core_clock, older versions use pb_set_clock 
        #  or set_clock, need to write a more compatible function here.
        try: 
            getattr(self._dll,'pb_core_clock')
        except (AttributeError, NameError):
            return self.chk(self._dll.pb_set_clock(ctypes.c_double(clockrate)))
           # print 'pb set clock loaded'
        else:
            return self.chk(self._dll.pb_core_clock(ctypes.c_double(clockrate)))
            #print 'pb core clock loaded'
    
    # Start programming the PB board. 
    def start_programming(self):
        try: 
            getattr(self._dll,'pb_start_programming')
        except (AttributeError, NameError):
            return self.chk(self._dll.start_programming(self._PULSE_PROGRAM))
           # print 'start programming loaded'
        else:
            return self.chk(self._dll.pb_start_programming(self._PULSE_PROGRAM))
            # print 'pb start programming loaded'
            
    # Send instructions to the PB board.
    # returns address of current instruction to be used for branching. returns negative number in case of failed instruction
    def send_instruction(self, flags, inst, inst_data, length):
        try:
            getattr(self._dll, 'pb_inst_pbonly')
        except (AttributeError, NameError):
            print 'Function pb_inst_pbonly not found.'
        else:
            address = self._dll.pb_inst_pbonly(ctypes.c_uint(flags), ctypes.c_int(inst), ctypes.c_int(inst_data), ctypes.c_double(length))
            return address
    
    # Stop programming the PB board. 
    def stop_programming(self):
        try: 
            getattr(self._dll,'pb_stop_programming')
        except (AttributeError,NameError):
            return self.chk(self._dll.stop_programming(self._PULSE_PROGRAM))
        else:
            return self.chk(self._dll.pb_stop_programming(self._PULSE_PROGRAM))
            
    # Stop the pulse sequence. Note that stop() or reset() must be called before start()
    def stop(self):
        return self.chk(self._dll.pb_stop())

    def reset(self):
        return self.chk(self._dll.pb_reset())
    # Start the pulse sequence.
    def start(self):
        return self.chk(self._dll.pb_start())
    
    # Get the current version of SpinAPI being used by the board.
    # not currently working. 
    def get_version(self):
        return str(self._dll.pb_get_version())
        
    # Get the current status of the board. The status functiong provided by the spinapi .dll file
    # returns a series of bits that can be translated into english.
    def status(self):
        result = ''.join(list(bin(self._dll.pb_read_status()))[2:])
        if len(result) < 4:
            result = result.zfill(4)
        result = list(result)
        status = ''
        if len(result) == 4:
            if result[-1] == '1':
                status += 'Stopped '
            if result[-2] == '1':
                status += 'Reset '
            if result[-3] == '1':
                status += 'Running '
            if result[-4] == '1':
                status += 'Waiting'
            return status
        else:
            return 'Status not understood'
                

    def close(self):
        return self.chk(self._dll.pb_close())

    
    
        