from time import time, sleep
from PyQt5 import QtCore
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

        self.running = False

    def run(self):
        self.running=True
        while self.running:
            if self.testing:
                self.new_rxn_temp_data.emit(200)
                self.new_cryo_temp_data.emit(170)
                # self.new_flow_data.emit(0)
                self.new_rxn_pressure_data.emit(1)
                self.new_cryo_pressure_data.emit(0.1)
            else:
                [cryo_temp, rxn_temp] = self.cryoControl.get_all_kelvin_reading()
                log_dict = {
                    'Reaction Pressure':self.rxnGauge.getPressure(),
                    'Cryo Pressure':self.cryoGauge.getPressure(),
                    'Reaction Temperature':rxn_temp_temp,
                    'Cryo Temperature':cryo_temp
                }
                self.new_rxn_pressure_data.emit(log_dict['Reaction Pressure'])
                self.new_cryo_pressure_data.emit(log_dict['Cryo Pressure'])
                self.new_cryo_temp_data.emit(cryo_temp)
                self.new_rxn_temp_data.emit(rxn_temp)

                ## adding code to save measured values to a csv as well
                df = pd.DataFrame([log_dict])
                df.to_csv(self.log_path,mode='a' if self.log_path.exists() else 'w',header=not self.log_path.exists(),index=False)
                ###
            QtCore.QThread.msleep(self.delay*1000)



class PurgeProcess(QtCore.QThread):

    message = QtCore.pyqtSignal(str)

    def __init__(self,testing,logger,mfc,pgauge, DAQ):
        ''' Takes reaction gauge, MFC, and relays '''
        super().__init__()
        self.testing = testing
        self.logger = logger
        self.MFC = mfc ## really the MFC controller
        self.PGauge = pgauge
    
    def run(self,init_volume, init_rate, low_pressure, high_pressure, timeout = None, cycles = 3):
        '''TODO: plot data as you go, some way to check that batch volume gets close enough to desired pressure'''            

        if timeout == None:
            timeout = init_volume/init_rate 
        for c in range(cycles):
            self.DAQ.open_relay1()
            self.MFC.MFC1.start_batch(init_volume, init_rate)
            message = f'On cycle {c+1}. Starting Ar purge at {init_rate}sccm for {init_volume}scc, waiting for {high_pressure} Torr'
            self.logger.info(message)
            self.message.emit(message)
            self.wait_for_pressure(high_pressure, timeout)
            self.DAQ.close_relay1()
            self.DAQ.open_relay2()
            message = f'On cycle {c+1}. Starting opening to pump, waiting for {low_pressure} Torr'
            self.logger.info(message)
            self.message.emit(message)
            self.wait_for_pressure(low_pressure)
            self.DAQ.close_relay2()

    def wait_for_pressure(self,pressure,timeout = None, delay = 10, tolerance = 5):
        ''' wait until pressure within 5% of given pressure, checking at intervals of delay (s) '''
        self.waiting = True
        time = 0
        while self.waiting:
            measured_pressure = self.PGauge.getPressure()
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

                
