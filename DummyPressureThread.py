import re, pyvisa
from pyqtgraph.Qt import QtCore
import numpy as np

class DummyThread(QtCore.QThread):
    '''
    Thread that periodically reads from pressure gauge via serial communication
    '''
    newData = QtCore.pyqtSignal(object)

    def __init__(self,delay=10):
        '''instrument is string (e.g. 'ASRL3::INSTR') and device Address is string of 5 ints
        '''
        super().__init__()
        self.delay = delay
        print(f"Initialized dummy thread with delay: {self.delay}")
    def run(self):
        self.running = True
        rng = np.random.default_rng()
        while self.running:
            try:
                self.output = 749+rng.random()
                self.newData.emit(self.output)
                print(f"emit: {self.output}")
                QtCore.QThread.msleep(self.delay)
            except Exception as e:
                print(str(e))
                pass

class NotAsDumbThread(QtCore.QThread):
    '''Want to test some things about QThread'''

    newData = QtCore.pyqtSignal(float)

    def __init__(self,setpoint=300,delay=10):
        super().__init__()
        self.delay = delay
        self.running = True
        self.setpoint = setpoint
        print(f"Initialized NAD thread with delay: {self.delay}")

    def run(self):
        self.running = True
        rng = np.random.default_rng()
        while self.running:
            try:
                self.output = 100 + rng.random()
                self.newData.emit(self.output)
                print(f"emit: {self.output}")
                QtCore.QThread.msleep(self.delay)
            except Exception as e:
                print(str(e))
                pass

    def updateCryoSetpoint(self):
        temp = self.setpoint
        print(f"Would update cryo setpoint to {temp} K")