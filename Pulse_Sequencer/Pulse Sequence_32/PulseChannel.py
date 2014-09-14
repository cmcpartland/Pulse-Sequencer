from PulseTrain import PulseTrain

class PulseChannel:
    def __init__(self, num_of_pulse_trains=0, delay_on=0.0, delay_off=0.0, pulse_channel_index=0):
        self.num_pulses= 0
        self.delay_on = delay_on
        self.delay_off = delay_off
        self.num_of_pulse_trains = num_of_pulse_trains
        self.pulse_trains = []
        self.pulse_channel_index = pulse_channel_index
        self.latest_channel_event = 0
        self.first_channel_event = 0
    
    def addPulseTrain(self, time_on=1e-6, width=1e-7, separation=0.0, pulses_in_train=1):
        #add this pulse to the current pulse channel
        self.num_of_pulse_trains += 1
        if self.num_of_pulse_trains != 1:
            pulse_train = PulseTrain(time_on=time_on, width=width, separation=separation, 
                                     pulses_in_train=pulses_in_train)
        else:
            pulse_train = PulseTrain(time_on=time_on, width=width, separation=separation, pulses_in_train=pulses_in_train)
        self.pulse_trains.append(pulse_train)
        self.num_pulses += int(pulse_train.pulses_in_train)
        self.setLatestChannelEvent()
        self.setFirstChannelEvent()

    def deletePulseTrain(self, index):
        if self.num_of_pulse_trains > 0:
            pulse_train = self.pulse_trains.pop(index)
            self.num_of_pulse_trains -= 1
            self.setLatestChannelEvent()
            self.setFirstChannelEvent()
            return True
        else:
            return False
            
    def setFirstChannelEvent(self):
        if self.num_of_pulse_trains > 1:
            self.first_channel_event = sorted(self.pulse_trains, key=lambda x: x.first_pulse_train_event)[0].first_pulse_train_event
        elif self.num_of_pulse_trains == 1:
            self.first_channel_event = self.pulse_trains[0].first_pulse_train_event
        else:
            self.first_channel_event = 0
                
    def setLatestChannelEvent(self):
        self.latest_channel_event = 0
        for i in range(self.num_of_pulse_trains):
            if self.pulse_trains[i].latest_pulse_train_event > self.latest_channel_event:
                self.latest_channel_event = self.pulse_trains[i].latest_pulse_train_event