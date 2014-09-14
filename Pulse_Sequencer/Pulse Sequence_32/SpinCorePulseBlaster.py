import ctypes
import traceback

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
    
    def chk(self, error):
        """a simple error checking routine"""
        self._dll.pb_get_error.restype = ctypes.c_char_p
        recent_error = self._dll.pb_get_error()
        if error != 0:
            print recent_error
            #logger.error('PulseBlaster error: ' + err_str + ''.join(traceback.format_stack()))

            raise RuntimeError('PulseBlaster error: ' + recent_error + "".join(traceback.format_stack()))
        return recent_error
    
    def pb_init(self):
        self.chk(self._dll.pb_init())

    def pb_close(self):
        self.chk(self._dll.pb_close())
    
    def pb_start(self):
        self.chk(self._dll.pb_start())
    
    def pb_stop(self):
        self.chk(self._dll.pb_stop())

    def pb_reset(self):
        self.chk(self._dll.pb_reset())
        
    def pb_get_version(self):
        return self._dll.pb_get_version()
        
    def pb_status(self):
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
                
            
        #return bin(self._dll.pb_read_status())
        
    def pb_setclock(self,clockrate):
        # newer version of spinapi uses function pb_core_clock, older versions use pb_set_clock 
        #  or set_clock, need to write a more compatible function here.
        try: 
            getattr(self._dll,'pb_core_clock')
        except (AttributeError, NameError):
            self.chk(self._dll.pb_set_clock(ctypes.c_double(clockrate)))
           # print 'pb set clock loaded'
        else:
            self.chk(self._dll.pb_core_clock(ctypes.c_double(clockrate)))
            #print 'pb core clock loaded'
    
    def pb_start_programming(self):
        try: 
            getattr(self._dll,'pb_start_programming')
        except (AttributeError, NameError):
            self.chk(self._dll.start_programming(self._PULSE_PROGRAM))
           # print 'start programming loaded'
        else:
            self.chk(self._dll.pb_start_programming(self._PULSE_PROGRAM))
            # print 'pb start programming loaded'
            
    def pb_stop_programming(self):
        try: 
            getattr(self._dll,'pb_stop_programming')
        except (AttributeError,NameError):
            self.chk(self._dll.stop_programming(self._PULSE_PROGRAM))
        else:
            self.chk(self._dll.pb_stop_programming(self._PULSE_PROGRAM))
    
    # returns address of current instruction to be used for branching. returns negative number in case of failed instruction
    def pb_send_instruction(self, flags, inst, inst_data, length):
        try:
            getattr(self._dll, 'pb_inst_pbonly')
        except (AttributeError, NameError):
            print 'Function pb_inst_pbonly not found.'
        else:
            address = self._dll.pb_inst_pbonly(ctypes.c_uint(flags), ctypes.c_int(inst), ctypes.c_int(inst_data), ctypes.c_double(length))
            return address
    
    
        