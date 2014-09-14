import numpy as np

class PulseTrain:
    def __init__(self, time_on=1e-6, width=1e-7, separation=0.0, pulses_in_train=1, pulse_train_index=0):
        self.time_on = time_on
        self.width = width
        self.separation = separation
        self.pulses_in_train = pulses_in_train
        self.pulse_on_times = []
        if self.pulses_in_train == 1 or self.pulses_in_train == 0:
            self.separation = 0.0
        for i in range(int(pulses_in_train)):
            self.pulse_on_times.append(time_on + i*(self.width+self.separation))
        self.pulse_widths = [width]*int(pulses_in_train)
        
        self.latest_pulse_train_event = np.amax(np.array(self.pulse_on_times)) + width
        self.first_pulse_train_event = np.amin(np.array(self.pulse_on_times))
    