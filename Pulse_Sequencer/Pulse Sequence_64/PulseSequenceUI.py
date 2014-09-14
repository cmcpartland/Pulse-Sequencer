# Import necessary libraries
import subprocess
import sys
import numpy as np
import pickle
import time
import ctypes
import traceback
from PulseSequence import PulseSequence
from PulseTrain import PulseTrain
from SpinCorePulseBlaster import *
import struct
print 'Python Version: ', struct.calcsize("P") * 8, 'bit'

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
        
        # MPL toolbar
        self.mpl_toolbar = NavigationToolbar(self.canvas, self.ui.widgetMPLPlot)
        self.mpl_toolbar.setParent(self.ui.widgetMPLToolbar)

        vboxPlot = QVBoxLayout()
        vboxPlot.addWidget(self.canvas)  # the matplotlib canvas
        vboxToolbar = QVBoxLayout()
        vboxToolbar.addWidget(self.mpl_toolbar) # the matplotlib toolbar
        
        self.ui.widgetMPLPlot.setLayout(vboxPlot)
        self.ui.widgetMPLToolbar.setLayout(vboxToolbar)
        
        self.ui.mplwidgetPulseSeq = self.canvas
        
        self.error_message = QErrorMessage(parent=self)
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
        self.connect(self.ui.pushButtonClosePB, SIGNAL("clicked()"), lambda: self.communicate_with_pb('Close'))
        self.connect(self.ui.pushButtonSendSequence, SIGNAL("clicked()"), lambda: self.communicate_with_pb('Send sequence'))
        self.connect(self.ui.pushButtonStartSequence, SIGNAL("clicked()"), lambda: self.communicate_with_pb('Start sequence'))
        self.connect(self.ui.pushButtonStopSequence, SIGNAL("clicked()"), lambda: self.communicate_with_pb('Stop sequence'))
        self.connect(self.ui.pushButtonGetStatus, SIGNAL("clicked()"), lambda: self.communicate_with_pb('Get status'))
        
        self.connect(self.ui.pushButtonClearMessages, SIGNAL("clicked()"), self.ui.textEditMessages.clear)
        
        # Set validators for pulse train attributes
        vTimeOn = QDoubleValidator(self.ui.lineEditTimeOn)
        vTimeOn.setRange(12.5e-09, 10000.0, 9)
        vDouble = QDoubleValidator(self.ui.lineEditPulseWidth)
        vDouble.setRange(2.5e-09, 10000.0, 9)
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
        self.connect(self.communicate_with_pb_thread, SIGNAL("New command."), self.update_command)
        self.connect(self.communicate_with_pb_thread, SIGNAL("New status."), self.update_status)
        
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
        clock_cycle = 1e03/(float(self.ui.lineEditPBClockFrequency.text()))
        self.pulse_sequence.wait_events[self.ui.comboBoxWaitEvents.currentIndex()] = round((float(self.ui.lineEditWaitTime.text())*1e09)/clock_cycle)*clock_cycle*1e-09
        self.ui.lineEditWaitTime.setText(str(round((float(self.ui.lineEditWaitTime.text())*1e09)/clock_cycle)*clock_cycle*1e-09))
        instructions, seq, run_time, found_bad_instruction = self.pulse_sequence.convertSequenceToInstructions(self.ui.checkBoxInfiniteLoop.isChecked(), 
                                                                self.ui.spinBoxNumberOfLoops.value())
        if found_bad_instruction:
            self.error_message.showMessage('Sequence includes a bad instruction! The time between the beginning of any two pulses on any two channels must be at least 5 PulseBlaster clock cycles. Recommend undoing last action.')
        self.plot_sequence()

        
    def addWaitEvent(self):
        clock_cycle = 1e03/(float(self.ui.lineEditPBClockFrequency.text()))
        self.pulse_sequence.addWaitEvent(round((float(self.ui.lineEditWaitTime.text())*1e09)/clock_cycle)*clock_cycle*1e-09)
        self.ui.lineEditWaitTime.setText(str(round((float(self.ui.lineEditWaitTime.text())*1e09)/clock_cycle)*clock_cycle*1e-09))
        self.ui.comboBoxWaitEvents.addItem(str(self.pulse_sequence.num_of_wait_events-1))
        self.ui.comboBoxWaitEvents.setCurrentIndex(self.pulse_sequence.num_of_wait_events-1)
        instructions, seq, run_time, found_bad_instruction = self.pulse_sequence.convertSequenceToInstructions(self.ui.checkBoxInfiniteLoop.isChecked(), 
                                                                self.ui.spinBoxNumberOfLoops.value())
        if found_bad_instruction:
            self.error_message.showMessage('Sequence includes a bad instruction! The time between the beginning of any two pulses on any two channels must be at least 5 PulseBlaster clock cycles. Recommend undoing last action.')
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
        
    def changePulseTrainIndex(self):
        if self.currentChannel.num_of_pulse_trains > 0:
            new_index = self.ui.comboBoxPulseTrainIndex.currentIndex()
            
            self.currentPulseTrain = self.currentChannel.pulse_trains[new_index]
           
            self.ui.lineEditTimeOn.setText(str(self.currentChannel.pulse_trains[new_index].time_on))
            self.ui.lineEditPulseWidth.setText(str(self.currentChannel.pulse_trains[new_index].width))
            self.ui.lineEditPulseSeparation.setText(str(self.currentChannel.pulse_trains[new_index].separation))
            self.ui.lineEditPulsesInTrain.setText(str(self.currentChannel.pulse_trains[new_index].pulses_in_train))
    
    # When editing or adding pulse trains to the sequence, time_on, width, and separation values are rounded to the
    # nearest clock cycle, the resolution of the PB
    def EditPulseTrain(self):
        clock_cycle = 1e03/(float(self.ui.lineEditPBClockFrequency.text()))
        if self.currentChannel.num_of_pulse_trains > 0:
            pulse_train_index = self.ui.comboBoxPulseTrainIndex.currentIndex()
            old_pulse_train = self.currentChannel.pulse_trains[pulse_train_index]
            self.currentChannel.pulse_trains[pulse_train_index] = PulseTrain(time_on = round((float(self.ui.lineEditTimeOn.text())*1e09)/clock_cycle)*clock_cycle*1e-09, width = round((float(self.ui.lineEditPulseWidth.text())*1e09)/clock_cycle)*clock_cycle*1e-09,
                                                    separation = round((float(self.ui.lineEditPulseSeparation.text())*1e09)/clock_cycle)*clock_cycle*1e-09, pulses_in_train = int(self.ui.lineEditPulsesInTrain.text())) 
            if not self.currentChannel.has_coincident_events():
                self.currentPulseTrain = self.currentChannel.pulse_trains[pulse_train_index]
                self.currentChannel.setLatestChannelEvent()
                self.pulse_sequence.setLatestSequenceEvent()
                self.currentChannel.setFirstChannelEvent()
                self.pulse_sequence.setFirstSequenceEvent()
                
                # check to see if added pulse will give a bad instruction to PulseBlaster
                instructions, seq, run_time, found_bad_instruction = self.pulse_sequence.convertSequenceToInstructions(self.ui.checkBoxInfiniteLoop.isChecked(), 
                                                                self.ui.spinBoxNumberOfLoops.value())
                if found_bad_instruction:
                    #self.currentChannel.pulse_trains[pulse_train_index] = old_pulse_train
                    #self.currentPulseTrain = self.currentChannel.pulse_trains[pulse_train_index]  
                    #self.currentChannel.setLatestChannelEvent()
                    #self.pulse_sequence.setLatestSequenceEvent()
                    #self.currentChannel.setFirstChannelEvent()
                    #self.pulse_sequence.setFirstSequenceEvent()
                    #self.changePulseTrainIndex()
                    
                    self.error_message.showMessage('This will create a bad instruction! The time between the beginning of any two pulses on any two channels must be at least 5 PulseBlaster clock cycles. Recommend undoing last action.')
                self.plot_sequence()
                self.changePulseTrainIndex()
            else:
                self.currentChannel.pulse_trains[pulse_train_index] = old_pulse_train
                self.changePulseTrainIndex()
                sle.plot_sequence()
                self.error_message.showMessage('Pulses overlap!. Changes have been discarded.')
            
    def addPulseTrain(self):
        clock_cycle = 1e03/(float(self.ui.lineEditPBClockFrequency.text()))
        if self.ui.lineEditTimeOn.hasAcceptableInput() and self.ui.lineEditPulseWidth.hasAcceptableInput() and self.ui.lineEditPulseSeparation and self.ui.lineEditPulsesInTrain.hasAcceptableInput:
            self.currentChannel.addPulseTrain(round((float(self.ui.lineEditTimeOn.text())*1e09)/clock_cycle)*clock_cycle*1e-09,
                                    round((float(self.ui.lineEditPulseWidth.text())*1e09)/clock_cycle)*clock_cycle*1e-09,
                                    round((float(self.ui.lineEditPulseSeparation.text())*1e09)/clock_cycle)*clock_cycle*1e-09,
                                    int(self.ui.lineEditPulsesInTrain.text()))
                                    
            if not self.currentChannel.has_coincident_events():

                self.currentChannel.setLatestChannelEvent()
                self.pulse_sequence.setLatestSequenceEvent()
                self.currentChannel.setFirstChannelEvent()
                self.pulse_sequence.setFirstSequenceEvent()
                self.ui.comboBoxPulseTrainIndex.addItem(str(self.currentChannel.num_of_pulse_trains-1))
                self.ui.comboBoxPulseTrainIndex.setCurrentIndex(self.currentChannel.num_of_pulse_trains-1)
                self.currentPulseTrain = self.currentChannel.pulse_trains[self.currentChannel.num_of_pulse_trains-1]
                # check to see if added pulse will give a bad instruction to PulseBlaster
                instructions, seq, run_time, found_bad_instruction = self.pulse_sequence.convertSequenceToInstructions(self.ui.checkBoxInfiniteLoop.isChecked(), 
                                                                self.ui.spinBoxNumberOfLoops.value())
                self.plot_sequence()
                if found_bad_instruction:
                    self.error_message.showMessage('This will create a bad instruction! The time between the beginning of any two pulses on any two channels must be at least 5 PulseBlaster clock cycles. Recommend undoing last action.')
                    #self.deletePulseTrain()
            else:
                self.deletePulseTrain()
                self.error_message.showMessage('Pulses overlap! Pulse train has not been added.')
            
    
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
        self.ui.textEditLoadFile.setText(QFileDialog.getOpenFileName(filter='pickle Files (*.pkl)'))
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
        self.ui.textEditSaveFile.setText(QFileDialog.getSaveFileName(filter='pickle Files (*.pkl)'))
    def save_ps(self):
        file_name = self.ui.textEditSaveFile.toPlainText()
        self.save_ps_thread.input(self.pulse_sequence, file_name)
    def update_save_status(self, status):
        self.ui.textEditSaveStatus.setText(status)

    def plot_sequence(self):
        self.plot_ps_thread.input(self.pulse_sequence, self.ui.mplwidgetPulseSeq, float(self.ui.lineEditPBClockFrequency.text()))

    def communicate_with_pb(self, command):
        self.command = command
        if self.command == 'Initialize':
            self.communicate_with_pb_thread.initialize(self.ui.lineEditPBClockFrequency.text())
        elif self.command == 'Close':
            self.communicate_with_pb_thread.close()
        elif self.command == 'Send sequence':
            self.communicate_with_pb_thread.send_sequence(self.pulse_sequence, str(self.ui.lineEditPBClockFrequency.text()), self.ui.checkBoxInfiniteLoop.isChecked(), 
                                                            self.ui.doubleSpinBoxRunTime.value(), self.ui.spinBoxNumberOfLoops.value())
        elif self.command == 'Start sequence':
            self.communicate_with_pb_thread.start_sequence()
        elif self.command == 'Stop sequence':
            self.communicate_with_pb_thread.stop_sequence()
        elif self.command == 'Get status':
            self.communicate_with_pb_thread.get_status()
        
            
    def update_messages(self, message):
        self.ui.textEditMessages.append(message)
    def update_command(self, command):
        self.ui.lineEditCommand.setText(command)
    def update_status(self, status):
        self.ui.lineEditStatus.setText(status)
        
class Communicate_with_PB(QThread):
    import time
    def __init__(self, parent=None):
        QThread.__init__(self,parent)
        self.exiting = False
        self.initialized = False
        self.running_timer = QTimer()
        self.running_timer.timeout.connect(self.stop_sequence)
        self.sequence_sent_recently = False
    
    #An error-checking function:
    def check(self, error):
        if not error == None:
            self.emit(SIGNAL("New message."), 'PulseBlaster error: ' + error)
            raise RuntimeError()
            
    def initialize(self, clock_freq):
        self.clock_freq = clock_freq
        if struct.calcsize("P") * 8 == 64:
            libraryFileName = 'spinapi64.dll'
        else:
            libraryFileName = 'spinapi.dll'
        print '%s being used' % libraryFileName
        try:
            test = ctypes.cdll.LoadLibrary(libraryFileName)
        except OSError :
            print 'Necessary dll could not be loaded: ', libraryFileName
            raise 
        else:
            self.pb = SpinCorePulseBlaster(libraryFile = libraryFileName)
            self.emit(SIGNAL("New message."), '\nClosing Pulse Blaster in case already initialized...')
            try: 
                self.check(self.pb.close())
            except RuntimeError:
                pass
            self.emit(SIGNAL("New command."), 'Initialize PulseBlaster')
            self.emit(SIGNAL("New message."), '\nInitializing:')
            self.check(self.pb.init())
            self.emit(SIGNAL("New message."), 'Pulse Blaster board succesfully initiated.')
            self.initialized = True
            self.check(self.pb.setclock(float(self.clock_freq)))
            self.emit(SIGNAL("New message."), 'PB clock frequency: %s Mhz' %self.clock_freq)
            version = self.pb.get_version()
            self.emit(SIGNAL("New message."), 'Pulse Blaster version: %s' %version)
            # PB must be 'stopped' or 'reset' before the pulse sequence can ever be started
            
            #self.running_timer.setSingleShot(True)
    
    def send_sequence(self, pulse_sequence, clock_freq, inf_loop, user_run_time, num_of_loops):
        self.emit(SIGNAL("New command."), 'Send Sequence to PulseBlaster')
        if self.initialized:
            self.pulse_sequence = pulse_sequence
            self.clock_freq = clock_freq
            self.inf_loop = inf_loop
            self.run_time = user_run_time
            self.num_of_loops = num_of_loops
            instructions, seq, single_run_time, found_bad_instruction = self.pulse_sequence.convertSequenceToInstructions(self.inf_loop, self.num_of_loops)
            
            if not self.inf_loop:
                self.run_time = self.num_of_loops * single_run_time
            
            self.emit(SIGNAL("New message."), '\nSequence:')
            self.emit(SIGNAL("New message."), str('\t'+'\n\t'.join(map(str, seq))+ '\n'))
            if found_bad_instruction:
                self.emit(SIGNAL("New message."), 'Bad instruction found!\nWARNING: PulseBlaster output will not match form genereated on PulseBlaster Sequence Generator.')
            self.emit(SIGNAL("New message."), '\nSending sequence to PulseBlaster:')
            if not self.inf_loop:
                self.emit(SIGNAL("New message."), 'Number of loops: %g' %self.num_of_loops)
            
            self.emit(SIGNAL("New message."), 'Loop sequence run time: %f s' %self.run_time)

            self.emit(SIGNAL("New status."), self.pb.status())
            
            self.check(self.pb.stop())
            self.pb.start_programming()
            
            flags, op_code, inst_data, length = instructions.pop(0)
            start = self.pb.send_instruction(flags, op_code, inst_data, length)
            final_flags, final_op_code, final_inst_data, final_length = instructions.pop(-1)
            for instruction in instructions:
                flags, op_code, inst_data, length = instruction
                self.pb.send_instruction(flags, op_code, inst_data, length)
            
            #if inf_loop:
            final_inst_data = start
            self.pb.send_instruction(final_flags, final_op_code, final_inst_data, final_length)
            
            self.pb.stop_programming()
            self.emit(SIGNAL("New message."), 'Programming finished.')
            self.emit(SIGNAL("New status."), self.pb.status())
            self.sequence_sent_recently = True
        else:
            self.emit(SIGNAL("New message."), 'PulseBlaster not initialized.')
    
    def start_sequence(self):
        self.emit(SIGNAL("New command."), 'Start Pulse Sequence')
        if self.initialized:
                if self.sequence_sent_recently:
                    self.emit(SIGNAL("New message."), '\nStarting pulse sequence:')
                    self.emit(SIGNAL("New message."), 'Loop sequence run time: %f s' %self.run_time)
                else:
                    self.emit(SIGNAL("New message."), '\nStarting pulse sequence...')
                # Before starting, pb_stop() or pb_reset() must be called
                
                self.check(self.pb.start())
                self.emit(SIGNAL("New status."), self.pb.status())
                if self.sequence_sent_recently:
                    # running_timer will call self.pb.stop() when it timeouts
                    self.running_timer.start(self.run_time*1e03)
                
                # If PB is sent a wait instruction, check PB every 1 second to see if the board has been triggered. Else, add 1 second to total run time
                #start_time = time.time()
                #current_time = start_time
                #while current_time < start_time + run_time:
                #    status = self.pb.status()
                #    if 'Waiting' in status:
                #            time.sleep(1)
                #            self.emit(SIGNAL("New message."), '\tStatus: %s' %status)
                #            run_time += 1
                #    else:
                #        time.sleep(run_time/100.0)
                #    current_time = time.time()
                #time.sleep(run_time)
        else:
            self.emit(SIGNAL("New message."), 'PulseBlaster not initialized.')
    
    def stop_sequence(self):
        self.emit(SIGNAL("New command."), 'Stop Pulse Sequence')
        if self.initialized:
            self.running_timer.stop()
            self.emit(SIGNAL("New message."), '\nStopping sequence:')
            self.check(self.pb.stop())
            self.emit(SIGNAL("New message."), 'Sequence stopped.')
        else:
            self.emit(SIGNAL("New message."),'PulseBlaster not initialized.')
            
    def close(self):
        self.emit(SIGNAL("New command."), 'Close PulseBlaster')
        if self.initialized:
            self.running_timer.stop()
            self.check(self.pb.stop())
            self.emit(SIGNAL("New message."), '\nClosing PulseBlaster:')
            try:
                self.check(self.pb.close())
            except RuntimeError:
                pass
            else:
                self.emit(SIGNAL("New message."), 'PulseBlaster closed.')
                self.initialized = False
        else:
            self.emit(SIGNAL("New message."), 'PulseBlaster not initialized.')
    
    def get_status(self):
        if self.initialized:
            self.emit(SIGNAL("New status."), self.pb.status())
        else:
            self.emit(SIGNAL("New status."), 'PulseBlaster not initialized.')

# A class used to plot the pulse sequence.
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
    
        
# A class used to load a PulseSequence object from a .pkl file.   
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
                data = pickle.load(load_file)
                date_modified = data[0]
                ps = data[1]
                self.emit(SIGNAL("Load attempted."), "Pulse sequence successfully loaded. Last modified %s." % date_modified)
                self.emit(SIGNAL("Initiate loaded pulse sequence."), ps)
            except:
                self.emit(SIGNAL("Load attempted."), "Unexpected error occurred. Pulse sequence not loaded.")
            load_file.close()

# A class used to save the current PulseSequence Object to a .pkl file. 
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
                pickle.dump([time.asctime(), self.pulse_sequence], save_file)
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
