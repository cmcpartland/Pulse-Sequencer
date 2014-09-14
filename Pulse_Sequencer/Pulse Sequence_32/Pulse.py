class PulseTrain:
    def __init__(self, time_on=1e-6, width=1e-7, separation=0, pulses_in_train=1):
        self.time_on = time_on
        self.width = width
        self.separation = separation
        self.pulses_in_train = pulses_in_train
    