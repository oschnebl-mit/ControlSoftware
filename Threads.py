from time import time, sleep
from PyQt5 import QtCore
import numpy as np
# import pandas as pd

class LoggingThread(QtCore.QThread):
    ''' Periodically asks for data from pressure gauge, furnace, and MFCS. Passes measured data and overpressure alarm to main window'''
    new_rxn_temp_data = QtCore.pyqtSignal(float)
    new_cryo_temp_data = QtCore.pyqtSignal(float)
    # new_flow_data = QtCore.pyqtSignal(object) ## not sure how I'll handle gases yet
    new_rxn_pressure_data = QtCore.pyqtSignal(float)
    new_cryo_pressure_data = QtCore.pyqtSignal(float)

    def __init__(self,logger,cryoControl, mfcControl, rxnGauge, cryoGauge,delay=30,testing = False):
        super().__init__()
        self.logger = logger
        # self.log_path = log_path
        self.testing = testing
        self.delay=delay

        if not self.testing:
            self.cryoControl = cryoControl
            self.rxnPressure = rxnGauge
            self.cryoPressure = cryoGauge
            self.mfcControl = mfcControl

        elif self.testing:
            try:
                self.rxnPressure = rxnGauge
                self.rxnPressure.test()
                # pressure = self.rxnPressure.get_pressure()
                # self.new_rxn_pressure_data.emit(pressure)
                # print('successfully connected to MKS902, read pressure = ', pressure)
            except (OSError, AttributeError) as e:
                self.logger.exception(e)
            try:
                self.mfcControl = mfcControl
                flow = self.mfcControl.MFC1.get_measured_values()
                
                print('successfully connected to Brooks0254, read values = ', flow)
            except (OSError,AttributeError) as e:
                self.logger.exception(e)
            
            try:
                self.cryoControl = cryoControl
                [cryo_temp,rxn_temp] = self.cryoControl.get_all_kelvin_reading()
                self.new_cryo_temp_data.emit(cryo_temp)
                print(f'Successfully connected to Lakeshore 335. Read temp {cryo_temp}')
            except (OSError,AttributeError) as e:
                self.logger.exception(e)


        self.running = False

    def run(self):
        self.running=True
        while self.running:
            if self.testing:
                rng = np.random.default_rng()
                self.new_rxn_temp_data.emit(200+rng.random())
                self.new_cryo_temp_data.emit(170+rng.random())
                # self.new_flow_data.emit(0)
                self.new_rxn_pressure_data.emit(1*rng.random())
                self.new_cryo_pressure_data.emit(0.1*rng.random())
                print(f'logging cryo temp:{170+rng.random()}')
            else:
                [cryo_temp, rxn_temp] = self.cryoControl.get_all_kelvin_reading()
                log_dict = {
                    'Reaction Pressure':self.rxnGauge.get_pressure(),
                    'Cryo Pressure':self.cryoGauge.get_pressure(),
                    'Reaction Temperature':rxn_temp,
                    'Cryo Temperature':cryo_temp
                }
                self.new_rxn_pressure_data.emit(log_dict['Reaction Pressure'])
                self.new_cryo_pressure_data.emit(log_dict['Cryo Pressure'])
                self.new_cryo_temp_data.emit(cryo_temp)
                self.new_rxn_temp_data.emit(rxn_temp)

                ## adding code to save measured values to a csv as well
                # df = pd.DataFrame([log_dict])
                # df.to_csv(self.log_path,mode='a' if self.log_path.exists() else 'w',header=not self.log_path.exists(),index=False)
                ###
            QtCore.QThread.msleep(self.delay*1000)



class PurgeThread(QtCore.QThread):

    message = QtCore.pyqtSignal(str)
    new_pressure = QtCore.pyqtSignal(float)
    new_flow = QtCore.pyqtSignal(float)

    def __init__(self,testing,logger,mfc,pgauge, DAQ):
        ''' Takes reaction gauge, MFC, and relays '''
        super().__init__()
        self.testing = testing
        self.logger = logger
        self.MFC = mfc ## really the MFC controller
        self.PGauge = pgauge
        self.running = False

    
    def setup(self,init_volume, init_rate, low_pressure, high_pressure, timeout = None, cycles = 3):
        self.volume = init_volume
        self.rate = init_rate
        self.low_pressure = low_pressure
        self.high_pressure = high_pressure
        self.timeout = timeout
        self.cycles = cycles

    def run(self):
        '''TODO: add flow measurements, some way to check that batch volume gets close enough to desired pressure'''      
        self.running = True
          
        if self.timeout == None:
            self.timeout = self.volume/self.rate 

        if self.testing:
            testing_message = f'Would run pump purge for {self.cycles} cycles with timeout of {self.timeout}'
            self.message.emit(testing_message)
            self.logger.info(testing_message)
            print(testing_message)
            for c in range(self.cycles):
                if not self.running:  
                    break  
                self.new_pressure.emit(200+c)
                print(200+c)
                sleep(5)
            self.finished.emit()
        else:
            for c in range(self.cycles):
                if not self.running:
                    break
                ## pump first (assuming we start full of air)
                self.DAQ.open_relay2()
                message = f'On cycle {c+1}. Starting open to pump, waiting for {self.low_pressure} Torr'
                self.logger.info(message)
                self.message.emit(message)
                self.wait_for_pressure(self.low_pressure,self.timeout)
                self.DAQ.close_relay2()
                ## purge with Ar second
                self.DAQ.open_relay1()
                self.MFC.MFC1.start_batch(self.volume, self.rate)
                message = f'On cycle {c+1}. Starting Ar purge at {self.rate}sccm for {self.volume}scc, waiting for {self.high_pressure} Torr'
                self.logger.info(message)
                self.message.emit(message)
                self.wait_for_pressure(self.high_pressure, self.timeout)
                self.DAQ.close_relay1()

    def wait_for_pressure(self,pressure,timeout = None, delay = 10, tolerance = 5):
        ''' wait until pressure within 5% of given pressure, checking at intervals of delay (s) '''
        self.waiting = True
        time = 0
        while self.waiting:
            if not self.running:
                break
            measured_pressure = self.PGauge.getPressure()
            self.new_pressure.emit(measured_pressure)
            if timeout != None and timeout < time:
                self.logger.error(f'Reached timeout waiting for pressure {pressure}')
                break ## this will allow the function to continue, which is good if it got close, bad if pressure gets too high
            elif 100*abs(measured_pressure - pressure)/pressure <= tolerance:
                self.waiting = False
                break
            else:
                sleep(delay)
                time += delay/60 # time in minutes, sleep in seconds
                # QtCore.QThread.msleep(self.delay*1000)

class DoseThread(QtCore.QThread):

    message = QtCore.pyqtSignal(str)
    new_data = QtCore.pyqtSignal(object)
    

    def __init__(self,testing,logger,MFC,pgauge, DAQ, cryo):
        ''' Needs references to reaction gauge, MFC, relays, and cryo controller '''
        super().__init__()
        self.testing = testing
        self.logger = logger
        self.MFC = MFC ## really the MFC controller
        self.PGauge = pgauge
        self.cryo = cryo
        self.DAQ = DAQ
        self.running = False
    
    def setup(self,gas_name,init_volume, init_rate, target_pressure, timeout = None):
        self.volume = init_volume
        self.rate = init_rate
        self.pressure = target_pressure
        self.timeout = timeout
        self.gas_name = gas_name
        if not self.testing:
            if self.gas_name == 'H2S':
                self.active_MFC = self.MFC.MFC2
            elif self.gas_name == 'H2':
                self.active_MFC = self.MFC.MFC3
    
    
    def run(self):
        '''TODO: 
            add flow data, check for batch finished signal
            Add some way to dose "a bit more" if pressure not there'''            
        self.running = True
        if self.timeout == None:
            self.timeout = self.volume/self.rate 

        if self.testing:
            testing_message = f'Would dose {self.volume} scc of {self.gas_name} at {self.rate} sccm'
            self.message.emit(testing_message)
            self.logger.info(testing_message)
            for c in range(10):
                if self.running == False:
                    break
                rng = np.random.default_rng()
                self.new_data.emit((190+c+rng.random(),700+c+2*rng.random()))
                sleep(2)
        else:
            message = f'Beginning {self.gas_name} dose of {self.volume} scc at {self.rate} sccm'
            self.DAQ.open_relay1()
            self.active_MFC.start_batch(self.volume,self.rate)
            self.logger.info(message)
            self.message.emit(message)
            self.wait_for_pressure(self.pressure)
            
            self.DAQ.close_relay1()
    

    def wait_for_pressure(self,pressure,timeout = None, delay = 10, tolerance = 5):
        ''' wait until pressure within 5% of given pressure, checking at intervals of delay (s) '''
        self.waiting = True
        time = 0
        while self.waiting:
            if not self.running:
                break
            measured_pressure = self.PGauge.getPressure()
            measured_temperature = self.cryo.get_all_kelvin_reading()[1]
            self.new_data.emit((measured_temperature,measured_pressure))
            if timeout != None and timeout < time:
                self.logger.error(f'Reached timeout waiting for pressure {pressure}')
                break ## this will allow the function to continue, which is good if it got close, bad if pressure gets too high
            elif 100*abs(measured_pressure - pressure)/pressure <= tolerance:
                self.waiting = False
                break
            else:
                sleep(delay)
                time += delay/60 # time in minutes (scc/sccm), sleep in seconds
                # QtCore.QThread.msleep(self.delay*1000)
                
