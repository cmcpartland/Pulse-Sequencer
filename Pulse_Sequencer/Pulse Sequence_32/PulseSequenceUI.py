# Import necessary libraries
import subprocess
import sys
import numpy as np
import pickle
import time
from PulseSequence import PulseSequence
from PulseTrain import PulseTrain

from matplotlib.backends.backend_qt4agg import (FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QTAgg as NavigationToolbar)
from matplotlib.figure import Figure

from PyQt4.QtCore import * 
from PyQt4.QtGui import *

from GUI_Sub_Folder.GUI import Ui_MainWindow



class MyForm(QMainWindow):
    
    def __init__(self, parent = None):
        
        # standard GUI code
        QWidget.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.canvas = FigureCanvas(self.ui.mplwidgetPulseSeq.figure)
        self.canvas.setParent(self.ui.widgetMPLPlot)
        #self.canvas.setFocusPolicy(Qt.StrongFocus)
        #self.canvas.setFocus()
        
        # MPL toolbar
        self.mpl_toolbar = NavigationToolbar(self.canvas, self.ui.widgetMPLPlot)
        self.mpl_toolbar.setParent(self.ui.widgetMPLToolbar)
        
        #self.canvas.mpl_connect('key_press_event', self.on_key_press)

        vboxPlot = QVBoxLayout()
        vboxPlot.addWidget(self.canvas)  # the matplotlib canvas
        vboxToolbar = QVBoxLayout()
        vboxToolbar.addWidget(self.mpl_toolbar) # the matplotlib toolbar
        
        self.ui.widgetMPLPlot.setLayout(vboxPlot)
        self.ui.widgetMPLToolbar.setLayout(vboxToolbar)
        
        self.ui.mplwidgetPulseSeq = self.canvas

        self.pulse_sequence = PulseSequence()
        
        # Connect the buttons
        self.connect(self.ui.comboBoxChannel, SIGNAL("currentIndexChanged(int)"), self.changeChannel)
        self.connect(self.ui.comboBoxPulseTrainIndex, SIGNAL("currentIndexChanged(int)"), self.changePulseTrainIndex)
        self.connect(self.ui.lineEditTimeOn, SIGNAL("returnPressed()"), self.EditPulseTrain)
        self.connect(self.ui.lineEditPulseWidth, SIGNAL("returnPressed()"), self.EditPulseTrain)
        self.connect(self.ui.lineEditPulseSeparation, SIGNAL("returnPressed()"), self.EditPulseTrain)
        self.connect(self.ui.lineEditPulsesInTrain, SIGNAL("returnPressed()"), self.EditPulseTrain)
        self.connect(self.ui.pushButtonAddPulse, SIGNAL("clicked()"), self.addPulseTrain)
        self.connect(self.ui.pushButtonDeletePulse, SIGNAL("clicked()"), self.deletePulseTrain)
        self.connect(self.ui.pushButtonChooseSaveFile, SIGNAL("clicked()"), self.choose_save_file)
        self.connect(self.ui.pushButtonSavePS, SIGNAL("clicked()"), self.save_ps)
        self.connect(self.ui.pushButtonLoadPS, SIGNAL("clicked()"), self.load_ps)
        self.connect(self.ui.pushButtonChooseLoadFile, SIGNAL("clicked()"), self.choose_load_file)
        self.connect(self.ui.comboBoxWaitEvents, SIGNAL("currentIndexChanged(int)"), self.changeWaitEventIndex)
        self.connect(self.ui.pushButtonAddWait, SIGNAL("clicked()"), self.addWaitEvent)
        self.connect(self.ui.pushButtonDeleteWait, SIGNAL("clicked()"), self.deleteWaitEvent)
        self.connect(self.ui.lineEditWaitTime, SIGNAL("returnPressed()"), self.editWaitEvent)
        
        
        self.connect(self.ui.pushButtonInitializePB, SIGNAL("clicked()"), lambda: self.communicate_with_pb('Initialize'))
        self.connect(self.ui.pushButtonStartSequence, SIGNAL("clicked()"), lambda: self.communicate_with_pb('Start sequence'))
        self.connect(self.ui.pushButtonClearMessages, SIGNAL("clicked()"), self.ui.textEditMessages.clear)
        
        # Set validators for pulse train attributes
        vTimeOn = QDoubleValidator(self.ui.lineEditTimeOn)
        vTimeOn.setRange(12.5e-09, 10000.0, 7)
        vDouble = QDoubleValidator(self.ui.lineEditPulseWidth)
        vDouble.setRange(2.5e-09, 10000.0, 7)
        vDouble.setNotation(1)
        self.ui.lineEditTimeOn.setValidator(vTimeOn)
        self.ui.lineEditPulseWidth.setValidator(vDouble)
        self.ui.lineEditPulseSeparation.setValidator(vDouble)  
        self.ui.lineEditPBClockFrequency.setValidator(vDouble)
        self.ui.lineEditWaitTime.setValidator(vDouble)
        vInt = QIntValidator(1, 1000, self.ui.lineEditPulsesInTrain)
        self.ui.lineEditPulsesInTrain.setValidator(vInt)
        
        # Create threads
        self.save_ps_thread = Save_pulse_sequence()
        self.load_ps_thread = Load_pulse_sequence()
        self.plot_ps_thread = Plot_pulse_sequence()
        self.communicate_with_pb_thread = Communicate_with_PB()
        
        # Connect the threads
        self.connect(self.save_ps_thread, SIGNAL("Save attempted."), self.update_save_status)
        self.connect(self.load_ps_thread, SIGNAL("Load attempted."), self.update_load_status)
        self.connect(self.load_ps_thread, SIGNAL("Initiate loaded pulse sequence."), self.initiate_loaded_ps)
        self.connect(self.communicate_with_pb_thread, SIGNAL("New message."), self.update_messages)
        
        # Populate pulse sequence with channels:
        for i in xrange(21):
            self.pulse_sequence.addChannel()
            self.currentChannel = self.pulse_sequence.channels[i]
            self.ui.comboBoxChannel.addItem(str(self.currentChannel.pulse_channel_index))
        self.ui.comboBoxChannel.setCurrentIndex(0)
        self.changeChannel()

    def changeChannel(self):
        self.currentChannel = self.pulse_sequence.channels[self.ui.comboBoxChannel.currentIndex()]
        self.ui.comboBoxPulseTrainIndex.clear()
        if self.currentChannel.num_of_pulse_trains > 0:
            self.ui.comboBoxPulseTrainIndex.addItems(map(str, range(self.currentChannel.num_of_pulse_trains)))
            self.ui.comboBoxPulseTrainIndex.setCurrentIndex(0)
            self.changePulseTrainIndex()
        else:
            self.ui.lineEditTimeOn.setText('1e-06')
            self.ui.lineEditPulseWidth.setText('1e-07')
            self.ui.lineEditPulseSeparation.setText('0.0')
            self.ui.lineEditPulsesInTrain.setText('1')
            self.ui.lineEditTimeOn.selectAll()
            self.ui.lineEditPulseWidth.selectAll()
            self.ui.lineEditPulseSeparation.selectAll()
            self.ui.lineEditPulsesInTrain.selectAll()
            
    def changeWaitEventIndex(self):
        if self.pulse_sequence.num_of_wait_events > 0:
            self.ui.lineEditWaitTime.setText(str(self.pulse_sequence.wait_events[int(self.ui.comboBoxWaitEvents.currentIndex())]))

    def editWaitEvent(self):
        self.pulse_sequence.wait_events[self.ui.comboBoxWaitEvents.currentIndex()] = float(self.ui.lineEditWaitTime.text())
        self.plot_sequence()
        
    def addWaitEvent(self):
        self.pulse_sequence.addWaitEvent(str(self.ui.lineEditWaitTime.text()))
        self.ui.comboBoxWaitEvents.addItem(str(self.pulse_sequence.num_of_wait_events-1))
        self.ui.comboBoxWaitEvents.setCurrentIndex(self.pulse_sequence.num_of_wait_events-1)
        self.plot_sequence()
    
    def deleteWaitEvent(self):
        if self.pulse_sequence.num_of_wait_events > 0:
            self.pulse_sequence.deleteWaitEvent(self.ui.comboBoxWaitEvents.currentIndex())
            self.ui.comboBoxWaitEvents.removeItem(self.pulse_sequence.num_of_wait_events)
            if self.pulse_sequence.num_of_wait_events > 0:
                self.ui.lineEditWaitTime.setText(str(self.pulse_sequence.wait_events[int(self.ui.comboBoxWaitEvents.currentIndex())]))
            else:
                self.ui.lineEditWaitTime.clear()
            self.plot_sequence()
            
    #def addChannel(self):  
    #    if self.pulse_sequence.num_of_channels < self.pulse_sequence._CHANNELS:
    #        self.pulse_sequence.addChannel()
    #        self.currentChannel = self.pulse_sequence.channels[-1]
    #        self.ui.comboBoxChannel.addItem(str(self.currentChannel.pulse_channel_index))
    #        self.ui.comboBoxChannel.setCurrentIndex(self.pulse_sequence.num_of_channels-1)
    #        self.plot_ps_thread.input(self.pulse_sequence, self.ui.mplwidgetPulseSeq)
        
    
    #def deleteChannel(self):
    #    if self.pulse_sequence.num_of_channels > 0:
    #        index = self.ui.comboBoxChannel.currentIndex()
    #        if (self.pulse_sequence.deleteChannel(index)):
    #            if self.pulse_sequence.num_of_channels == 0:
    #                self.ui.comboBoxChannel.clear()
    #                self.ui.comboBoxPulseTrainIndex.clear()
    #            else:
    #                if index == 0:
    #                    self.currentChannel = self.pulse_sequence.channels[index]
    #                    self.ui.comboBoxChannel.removeItem(index)
    #                    self.ui.comboBoxChannel.setCurrentIndex(index)
    #                else:
    #                    self.currentChannel = self.pulse_sequence.channels[index-1]
    #                    self.ui.comboBoxChannel.removeItem(index)
    #                    self.ui.comboBoxChannel.setCurrentIndex(index-1)
    #            self.plot_ps_thread.input(self.pulse_sequence, self.ui.mplwidgetPulseSeq)
        
    def changePulseTrainIndex(self):
        if self.currentChannel.num_of_pulse_trains > 0:
            new_index = self.ui.comboBoxPulseTrainIndex.currentIndex()
            
            self.currentPulseTrain = self.currentChannel.pulse_trains[new_index]
           
            self.ui.lineEditTimeOn.setText(str(self.currentChannel.pulse_trains[new_index].time_on))
            self.ui.lineEditPulseWidth.setText(str(self.currentChannel.pulse_trains[new_index].width))
            self.ui.lineEditPulseSeparation.setText(str(self.currentChannel.pulse_trains[new_index].separation))
            self.ui.lineEditPulsesInTrain.setText(str(self.currentChannel.pulse_trains[new_index].pulses_in_train))
        
    def EditPulseTrain(self):
        if self.currentChannel.num_of_pulse_trains > 0:
            pulse_train_index = self.ui.comboBoxPulseTrainIndex.currentIndex()
            self.currentChannel.pulse_trains[pulse_train_index] = PulseTrain(time_on = float(self.ui.lineEditTimeOn.text()), width = float(self.ui.lineEditPulseWidth.text()),
                                                separation = float(self.ui.lineEditPulseSeparation.text()), pulses_in_train = int(self.ui.lineEditPulsesInTrain.text())) 
                                                #pulse_train_index = self.currentPulseTrain.pulse_train_index)
            self.currentPulseTrain = self.currentChannel.pulse_trains[pulse_train_index]
            self.currentChannel.setLatestChannelEvent()
            self.pulse_sequence.setLatestSequenceEvent()
            self.currentChannel.setFirstChannelEvent()
            self.pulse_sequence.setFirstSequenceEvent()
            self.plot_sequence()
            
    def addPulseTrain(self):
        if self.ui.lineEditTimeOn.hasAcceptableInput() and self.ui.lineEditPulseWidth.hasAcceptableInput() and self.ui.lineEditPulseSeparation and self.ui.lineEditPulsesInTrain.hasAcceptableInput:
            self.currentChannel.addPulseTrain(float(self.ui.lineEditTimeOn.text()),
                                        float(self.ui.lineEditPulseWidth.text()),
                                        float(self.ui.lineEditPulseSeparation.text()),
                                        int(self.ui.lineEditPulsesInTrain.text()))
            self.currentPulseTrain = self.currentChannel.pulse_trains[self.currentChannel.num_of_pulse_trains-1]
            self.ui.comboBoxPulseTrainIndex.addItem(str(self.currentChannel.num_of_pulse_trains-1))
            self.ui.comboBoxPulseTrainIndex.setCurrentIndex(self.currentChannel.num_of_pulse_trains-1)
            self.currentChannel.setLatestChannelEvent()
            self.pulse_sequence.setLatestSequenceEvent()
            self.currentChannel.setFirstChannelEvent()
            self.pulse_sequence.setFirstSequenceEvent()
            self.plot_sequence()
            
    
    def deletePulseTrain(self):
        if self.pulse_sequence.num_of_channels > 0 and self.currentChannel.num_of_pulse_trains > 0:
            index = self.ui.comboBoxPulseTrainIndex.currentIndex()
            if (self.currentChannel.deletePulseTrain(index)):
                self.ui.comboBoxPulseTrainIndex.removeItem(self.currentChannel.num_of_pulse_trains)
                if index == 0:
                    self.ui.comboBoxPulseTrainIndex.setCurrentIndex(0)
                else:
                    self.ui.comboBoxPulseTrainIndex.setCurrentIndex(index-1)
                self.changePulseTrainIndex()
                self.currentChannel.setLatestChannelEvent()
                self.pulse_sequence.setLatestSequenceEvent()
                self.currentChannel.setFirstChannelEvent()
                self.pulse_sequence.setFirstSequenceEvent()
                self.plot_sequence()
                    
    

 
    def choose_load_file(self):
        self.ui.textEditLoadFile.setText(QFileDialog.getOpenFileName())
    def load_ps(self):
        file_name = self.ui.textEditLoadFile.toPlainText()
        self.load_ps_thread.input(file_name)
    def update_load_status(self, status):
        self.ui.textEditLoadStatus.setText(status)
    
    def initiate_loaded_ps(self, pulse_sequence):
        self.pulse_sequence = pulse_sequence
        channels = map(str, range(self.pulse_sequence.num_of_channels))
        self.ui.comboBoxChannel.clear()
        self.ui.comboBoxChannel.addItems(map(str, self.pulse_sequence.pulse_channel_indices))
        if self.pulse_sequence.num_of_wait_events > 0:
            self.ui.comboBoxWaitEvents.addItems(map(str, range(self.pulse_sequence.num_of_wait_events)))
            self.ui.lineEditWaitTime.setText(str(self.pulse_sequence.wait_events[0]))
        self.plot_ps_thread.input(self.pulse_sequence, self.ui.mplwidgetPulseSeq, float(self.ui.lineEditPBClockFrequency.text()))
        
    def choose_save_file(self):
        self.ui.textEditSaveFile.setText(QFileDialog.getSaveFileName()) 
    def save_ps(self):
        file_name = self.ui.textEditSaveFile.toPlainText()
        self.save_ps_thread.input(self.pulse_sequence, file_name)
    def update_save_status(self, status):
        self.ui.textEditSaveStatus.setText(status)

    def plot_sequence(self):
        self.plot_ps_thread.input(self.pulse_sequence, self.ui.mplwidgetPulseSeq, float(self.ui.lineEditPBClockFrequency.text()))

    def communicate_with_pb(self, command):
        self.communicate_with_pb_thread.input(self.pulse_sequence, command, 
                                                str(self.ui.lineEditPBClockFrequency.text()), self.ui.checkBoxInfiniteLoop.isChecked(),
                                                self.ui.doubleSpinBoxRunTime.value(), self.ui.spinBoxNumberOfLoops.value())
    def update_messages(self, message):
        self.ui.textEditMessages.append(message)
        
class Communicate_with_PB(QThread):
    def __init__(self, parent=None):
        QThread.__init__(self,parent)
        self.exiting = False
    
    def input(self, pulse_sequence, command, clock_freq, inf_loop, run_time, num_of_loops):
        self.pulse_sequence = pulse_sequence
        self.command = command
        self.clock_freq = clock_freq
        self.inf_loop = inf_loop
        self.run_time = run_time
        self.num_of_loops = num_of_loops
        self.start()
        
    def run(self):
        # if 'start sequence' is chosen, first check for bad instructions. If there are no bad instructions, start PB
        found_bad_instruction = False
        if self.command == 'Start sequence':
            instructions, seq, run_time, found_bad_instruction = self.pulse_sequence.convertSequenceToBinaryInstructions(self.inf_loop, self.num_of_loops)
            if found_bad_instruction:
                self.emit(SIGNAL("New message."), '\nSequence:')
                self.emit(SIGNAL("New message."), str('\t'+'\n\t'.join(map(str, seq))+ '\n'))
                self.emit(SIGNAL("New message."), 'Bad instruction found! Stopping sequence...')
            else:
                self.expected_response = 'Starting sequence'
        elif self.command == 'Initialize': self.expected_response = 'Initializing'
        if not found_bad_instruction:
            try:
                p = subprocess.Popen(['C:\\Python27-64\\pythonw','SCPBCommunicator.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except OSError:
                print "Specified file failed to open."
            else:
                p.stdin.write(self.command+"\n")
                p.stdin.flush()
                subprocess_response = p.stdout.readline().strip()
                self.emit(SIGNAL("New message."), subprocess_response + '...')
                if subprocess_response == self.expected_response:
                    if self.command == 'Start sequence':
                        if self.inf_loop:
                            run_time = self.run_time
                        sequence_data = [instructions, self.clock_freq, self.inf_loop, run_time, self.num_of_loops]   
                        pickled_data = pickle.dumps(sequence_data).replace("\n", "\\()")
                        p.stdin.write(pickled_data + "\n")
                        p.stdin.flush()
                        self.emit(SIGNAL("New message."), '\nSequence:')
                        self.emit(SIGNAL("New message."), str('\t'+'\n\t'.join(map(str, seq))+ '\n'))
                    while True:
                        nextline = p.stdout.readline().rstrip()
                        if nextline == '' and p.poll() != None:
                            self.emit(SIGNAL("New message."), 'Process finished and/or terminated.\n')
                            # stderr has no data until EOF of the subprocess is reached. Wait until subprocess is finished to read errors.
                            err = p.stderr.read()
                            if err != '':
                                self.emit(SIGNAL("New message."), "\nERROR!\n%s" %err)  
                            break
                        if nextline != '':
                            self.emit(SIGNAL("New message."), nextline)  
                else:
                    self.emit(SIGNAL("New message."), 'Communication to subprocess failed.')
                    err = p.stderr.read()
                    if err != '':
                        self.emit(SIGNAL("New message."), "\nERROR!\n%s" %err)  
            
class Plot_pulse_sequence(QThread):
    def __init__(self, parent=None):
        QThread.__init__(self,parent)
        self.exiting=False
    
    def input(self, pulse_sequence, plot, clock_freq):    
        self.pulse_sequence = pulse_sequence
        self.plot = plot
        self.clock_freq = clock_freq
        self.reset_plot()
        if self.pulse_sequence.num_of_channels == 0:
            self.reset_plot()
        else:
            self.start()

    
    def run(self):
        self.axes.set_ylabel("Channel")
        self.axes.set_xlabel("Time (s)")
        for channel in self.pulse_sequence.channels:
            pulse_on_times = []
            pulse_widths = []
            if channel.num_of_pulse_trains > 0:
                for i in range(channel.num_of_pulse_trains):
                    pulse_on_times += channel.pulse_trains[i].pulse_on_times
                    pulse_widths += channel.pulse_trains[i].pulse_widths
                num_of_channel_events = len(pulse_on_times)*2
                channel_event_times = np.zeros(num_of_channel_events)
                event_flags = np.zeros(num_of_channel_events)
                for i in range(len(pulse_on_times)):
                    channel_event_times[2*i] = pulse_on_times[i]
                    event_flags[2*i] = 1
                    channel_event_times[2*i+1] = pulse_on_times[i] + pulse_widths[i]
                    event_flags[2*i+1] = 0
                sorted_indices = np.argsort(channel_event_times)
                sorted_event_times = np.insert(channel_event_times[sorted_indices], 0, 0)
                sorted_event_flags = np.insert(event_flags[sorted_indices]/2., 0, 0) + channel.pulse_channel_index
                
                # Add extra event at end that shows all channels being off, makes the plot look nicer.
                sorted_event_times = np.append(sorted_event_times, self.pulse_sequence.latest_sequence_event)
                sorted_event_flags = np.append(sorted_event_flags, channel.pulse_channel_index)
                last_pulse_width = sorted_event_times[-2]-sorted_event_times[-3]
                cycle = 1e-06/self.clock_freq
                added_time = 0
                if last_pulse_width < 5*cycle:
                    sorted_event_times = np.append(sorted_event_times, self.pulse_sequence.latest_sequence_event + 5*cycle - last_pulse_width)
                    added_time = 5*cycle - last_pulse_width
                    sorted_event_flags = np.append(sorted_event_flags, channel.pulse_channel_index)
                
                self.axes.step(sorted_event_times, sorted_event_flags, where='post')
                self.axes.set_ylim((-.5, channel.pulse_channel_index+1))
                self.axes.set_xlim(0, self.pulse_sequence.latest_sequence_event + added_time + (sorted_event_times[-1] - sorted_event_times[-2])/5.0)
        for wait_event in self.pulse_sequence.wait_events:
            self.axes.axvline(x=float(wait_event), ymin = -.5, ymax=channel.pulse_channel_index+1, color='black')
        time.sleep(.1)
        self.plot.draw()
            
    def reset_plot(self):
        self.plot.figure.clear()

        # Creates the new plot and is defined to self.axes. (Note: If one does not need to clear the plot, if colorbars are never used, this does not have to be done
        # All one needs to do to create a plot is "self.ui.mplwidgetPlot.axes" used equivalently to "self.axes" above and a new subplot does not have to be defined, as
        # done below.)
        self.axes = self.plot.figure.add_subplot(111)
        self.plot.figure.subplots_adjust(bottom=0.15)
    
        
        
class Load_pulse_sequence(QThread):
    def __init__(self, parent = None):
        QThread.__init__(self,parent)
        self.exiting=False
    
    def input(self, file_name):
        self.file_name = file_name
        self.start()
    
    def run(self):
        try:
            load_file = open(self.file_name, 'rb')
        except IOError:
            self.emit(SIGNAL("Load attempted."), "File not found! Pulse sequence could not be loaded.")
        else:
            try:
                ps = pickle.load(load_file)
                self.emit(SIGNAL("Load attempted."), "Pulse sequence successfully loaded.")
                self.emit(SIGNAL("Initiate loaded pulse sequence."), ps)
            except pickle.UnpicklingError:
                self.emit(SIGNAL("Load attempted."), "Unexpected error occurred. Pulse sequence not loaded.")
            load_file.close()
                
class Save_pulse_sequence(QThread):
    def __init__(self, parent = None):
        QThread.__init__(self,parent)
        self.exiting=False
    
    def input(self, pulse_sequence, file_name):
        self.pulse_sequence = pulse_sequence
        self.file_name = file_name
        self.start()
    
    def run(self):
        try:
            save_file = open(self.file_name, 'wb')
        except IOError:
            self.emit(SIGNAL("Save attempted."), "File not found! Pulse sequence could not be saved.")
        else:
            try:
                pickle.dump(self.pulse_sequence, save_file)
                self.emit(SIGNAL("Save attempted."), "Pulse sequence successfully saved.")
            except pickle.PicklingError:
                self.emit(SIGNAL("Save attempted."), "Unexpected error occurred. Pulse sequence not saved.")
            save_file.close()
        
    
     
# The if statement below checks to see if this module is the main module and not being imported by another module
# If it is the main module if runs the following which starts the GUI
# This is here in case it is being imported, then it will not immediately start the GUI upon being imported
if __name__ == "__main__":
    # Opens the GUI
    app = QApplication(sys.argv)
    myapp = MyForm()
    
    # Shows the GUI
    myapp.show()
    
    # Exits the GUI when the x button is clicked
    sys.exit(app.exec_())
