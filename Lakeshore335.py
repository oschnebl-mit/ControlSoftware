from lakeshore import Model335
from pyqtgraph.Qt import QtCore

''' Lakeshore docs on this specific model's python driver: https://lake-shore-python-driver.readthedocs.io/en/latest/model_335.html
'''

class TemperatureControlThread(QtCore.QThread):
    '''TODO (eventually): make a calibration function
    '''

    rxnTemp = QtCore.pyqtSignal(float)
    cryoTemp = QtCore.pyqtSignal(float)

    setpoint = QtCore.pyqtSignal(float)

    def __init__(self,baud_rate,setpoint,ramp_rate,ramp_bool = True, loop = 1):
        super().__init__()
        self.temperatureController = Model335(baud_rate)
        self.setpoint = setpoint
        self.ramp_rate = ramp_rate
        self.ramp_bool = ramp_bool

        self.loop = loop

    def run(self):
        ''' 
        This thread should automatically read both temps every [delay] s, but also handle commands
        My thought with having 1 thread is to avoid cloggin the serial communication channel
        '''
        self.running = True

        while self.running:
            ## periodically read temperature
            [tempA,tempB] = self.temperatureController.get_all_kelvin_readings()
            self.rxnTemp.emit(tempB)
            self.cryoTemp.emit(tempA)

            self.setpoint.emit(self.temperatureController.get_control_setpoint(self.loop))

    def changeSetpoint(self):
        # set_control_setpoint function takes int for which heater and float for value
        # need to have units setup
        self.temperatureController.set_control_setpoint(self.loop,self.setpoint)

    def changeRamp(self):
        '''built in ramp function takes output loop as int, ramp_enable as bool, rate_value as float
        This wrapper is just meant to pass values from the control panel
        '''
        self.temperatureController.set_setpoint_ramp_parameter(self.loop,self.ramp_bool,self.ramp_rate)


