from time import time, sleep,strftime
from PyQt5 import QtCore
import numpy as np
import csv
# import pandas as pd

class LoggingThread(QtCore.QThread):
    ''' Periodically asks for data from pressure gauge, furnace, and MFCS. Passes measured data and overpressure alarm to main window'''
    new_rxn_temp_data = QtCore.pyqtSignal(float)
    new_cryo_temp_data = QtCore.pyqtSignal(float)
    new_flow_data = QtCore.pyqtSignal(tuple) ## not sure how I'll handle gases yet
    new_rxn_pressure_data = QtCore.pyqtSignal(float)
    new_cryo_pressure_data = QtCore.pyqtSignal(float)

    def __init__(self,logger,log_path,cryoControl, mfcControl, rxnGauge, cryoGauge,save_csv,delay=30,testing = False):
        super().__init__()
        self.logger = logger
        self.log_path = log_path
        self.testing = testing
        self.delay=delay
        self.save_csv = save_csv
        # print(self.save_csv)

        if not self.testing:
            self.cryoControl = cryoControl
            self.rxnPressure = rxnGauge
            self.cryoPressure = cryoGauge
            self.mfcControl = mfcControl

        elif self.testing:
            try:
                self.cryoControl = cryoControl
                cryo_temp = float(cryoControl.query('KRDG? A',check_errors=False))
                print(f'Successfully connected to Lakeshore 335, read temp {cryo_temp}')
            except (OSError,AttributeError) as e:
                self.logger.exception(e)
            try:
                self.rxnPressure = rxnGauge
                pressure = self.rxnPressure.get_pressure()
                print('Successfully connected to MKS902 piezo, read pressure = ', pressure)
            except (OSError, AttributeError) as e:
                self.logger.exception(e)
            try:
                self.cryoPressure = cryoGauge
                pressure = self.cryoPressure.get_pressure()
                print('Successfully connected to MKS925 pirani, read pressure = ', pressure)
            except (OSError, AttributeError) as e:
                self.logger.exception(e)

            try:
                self.b0254 = mfcControl
                sccm, tot, time = self.b0254.MFC2.get_measured_values()
                print(f'Successfully connected to B0254, read MFC2 at {sccm} sccm')
            except(OSError, AttributeError) as e:
                self.logger.exception(e)
                self.b0254 = 'Brooks0254'
            
            timestr = strftime('%Y%m%d-%H%M%S')
            self.log_path = f'logs/CryoTest_{timestr}.csv'
            
        self.running = False

    def run(self):
        self.running=True
        row = 0
        while self.running:
            if self.testing:
                rng = np.random.default_rng()
                try:
                    cryo_pressure = self.cryoPressure.get_pressure()
                    self.new_cryo_pressure_data.emit(cryo_pressure)
                    self.new_rxn_pressure_data.emit(self.rxnPressure.get_pressure())
                    log_dict = {
                        'Time':strftime('%H:%M:%S'),
                        'DateTime':strftime('%Y%m%d-%H%M%S'),
                        'Reaction Pressure':self.rxnPressure.get_pressure(),
                        'Cryo Pressure':self.cryoPressure.get_pressure(),
                        }
                except (OSError,AttributeError,TypeError) as e:
                    print("failed to log pressure")
                    self.logger.exception(e)
                    self.new_cryo_pressure_data.emit(1*rng.random())
                    self.new_rxn_pressure_data.emit(0.1*rng.random())
                if self.cryoControl != 'Model335':
                    try:
                        cryo_temp = float(self.cryoControl.query('KRDG? A',check_errors=False))
                        rxn_temp = float(self.cryoControl.query("KRDG? B", check_errors=False))
                        self.new_cryo_temp_data.emit(cryo_temp)
                        self.new_rxn_temp_data.emit(rxn_temp)
                        log_dict['Cryo Temperature'] = cryo_temp
                        log_dict['Reaction Temperature'] = rxn_temp
                    except Exception as e:
                        print("failed to log temperatures")
                        self.new_cryo_temp_data.emit(170+rng.random())
                        self.new_rxn_temp_data.emit(200+rng.random())

                    # elif self.cryoControl == 'Model335':
                    #     ## because pressure and temperature share x axis, wonder if this needs data to udpate
                    #     self.new_cryo_temp_data.emit(0.0)
                    #     self.new_rxn_temp_data.emit(0.0)
                if self.b0254 != 'Brooks0254':
                    try:
                        Ar_sccm, tot, time = self.b0254.MFC2.get_measured_values()
                        log_dict['Ar sccm'] = Ar_sccm
                        H2S_sccm, tot, time = self.b0254.MFC1.get_measured_values()
                        log_dict['H2S sccm'] = H2S_sccm
                        self.new_flow_data.emit((Ar_sccm,H2S_sccm))
                    except(OSError,AttributeError,TypeError) as e:
                        print("failed to log flows")
                        self.new_flow_data.emit((10*rng.random(),rng.random()))
                   
                if self.save_csv:
                    # print(f"try to save to csv at {self.log_path}")
                    with open(self.log_path,'a',newline='') as csvfile:
                        w = csv.DictWriter(csvfile, log_dict.keys())
                        if row == 0:
                            w.writeheader()
                        w.writerow(log_dict)
                        row +=1 
                
            else:
                self.new_cryo_pressure_data.emit(self.cryoPressure.get_pressure())
                self.new_rxn_pressure_data.emit(self.rxnPressure.get_pressure())
                log_dict = {
                    'Time':strftime('%H%M%S'),
                    'DateTime':strftime('%Y%m%d-%H%M%S'),
                    'Reaction Pressure':self.rxnPressure.get_pressure(),
                    'Cryo Pressure':self.cryoPressure.get_pressure(),
                    }
                if self.cryoControl != 'Model335':
                    cryo_temp = float(self.cryoControl.query('KRDG? A',check_errors=False))
                    rxn_temp = float(self.cryoControl.query("KRDG? B", check_errors=False))
                    self.new_cryo_temp_data.emit(cryo_temp)
                    self.new_rxn_temp_data.emit(rxn_temp)
                    log_dict['Cryo Temperature'] = cryo_temp
                    log_dict['Reaction Temperature'] = rxn_temp
                if self.b0254 != 'Brooks0254':
                    Ar_sccm, tot, time = self.b0254.MFC2.get_measured_values()
                    log_dict['Ar sccm'] = Ar_sccm
                    H2S_sccm, tot, time = self.b0254.MFC1.get_measured_values()
                    log_dict['H2S sccm'] = H2S_sccm
                    self.new_flow_data.emit((Ar_sccm,H2S_sccm))

                if self.save_csv:
                    # print(f"trying to write to csv at {self.log_path}")
                    with open(self.log_path,'a',newline='') as csvfile:
                            w = csv.DictWriter(csvfile, log_dict.keys())
                            if row == 0:
                                w.writeheader()
                            w.writerow(log_dict)
                            row +=1 
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

    
    def setup(self,init_volume, init_rate, low_pressure, high_pressure, alarm_pressure, timeout = None, cycles = 3):
        self.volume = init_volume
        self.rate = init_rate
        self.low_pressure = low_pressure
        self.high_pressure = high_pressure
        self.alarm_pressure = alarm_pressure
        self.timeout = timeout
        self.cycles = cycles

    def run(self):
        '''TODO: add flow measurements, some way to check that batch volume gets close enough to desired pressure'''      
        self.running = True
          
        if self.timeout == None:
            self.timeout = self.volume/self.rate 

        if self.testing:
            testing_message = f'Would run pump/purge for {self.cycles} cycles with timeout of {self.timeout}'
            self.message.emit(testing_message)
            self.logger.info(testing_message)
            # print(testing_message)
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
                self.DAQ.open_relay1()
                self.DAQ.open_relay2()
                message = f'On cycle {c+1}. Starting open to pump, waiting for {self.low_pressure} Torr'
                self.logger.info(message)
                self.message.emit(message)
                self.wait_for_pressure(self.low_pressure,self.timeout)
                self.DAQ.close_relay2()
                ## purge with Ar second
                self.DAQ.open_relay0()
                # self.MFC.MFC1.start_batch(self.volume, self.rate)
                ## simple control means high pressure should be close but not too close to actual desired high
                self.MFC.MFC2.set_sccm(self.rate)
                message = f'On cycle {c+1}. Starting Ar purge at {self.rate}sccm for {self.volume}scc, waiting for {self.high_pressure} Torr'
                self.logger.info(message)
                self.message.emit(message)
                self.wait_for_pressure(self.high_pressure,self.alarm_pressure, self.timeout)
                self.MFC.MFC2.set_sccm(0)
                self.DAQ.close_relay0()

    def wait_for_pressure(self,pressure,alarm_pressure=None,timeout = None, delay = 10, tolerance = 5):
        ''' wait until pressure within 5% of given pressure, checking at intervals of delay (s) '''
        self.waiting = True
        time = 0
        while self.waiting:
            if not self.running:
                break
            measured_pressure = self.PGauge.getPressure()
            self.new_pressure.emit(measured_pressure)
            if measured_pressure >= alarm_pressure:
                self.DAQ.close_relay0()
                self.MFC.close_all()
                self.running=False ## stop thread because something went wrong
                break
            elif timeout != None and timeout < time:
                self.logger.error(f'Reached timeout waiting for pressure {pressure}')
                # self.running=False
                break ## this will allow the function to continue, which is good if it got close, bad if pressure gets too high
            elif 100*abs(measured_pressure - pressure)/pressure <= tolerance:
                self.waiting = False
                break
            else:
                sleep(delay)
                time += delay/60 # total time in min, delay is in seconds 
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
    
    def setup(self,gas_name,init_volume, init_rate, target_pressure, alarm_pressure, timeout = None):
        self.volume = init_volume
        self.rate = init_rate
        self.pressure = target_pressure
        self.alarm_pressure = alarm_pressure
        self.timeout = timeout
        self.gas_name = gas_name
        if not self.testing:
            if self.gas_name == 'Ar':
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
            self.DAQ.open_relay0()
            self.DAQ.open_relay1()
            self.active_MFC.set_sccm(self.rate)
            self.logger.info(message)
            self.message.emit(message)
            self.wait_for_pressure(self.pressure)
            self.active_MFC.set_sccm(0.0)
            self.DAQ.close_relay0()
            self.DAQ.close_relay1()
    

    def wait_for_pressure(self,pressure,timeout = None, delay = 10, tolerance = 5):
        ''' wait until pressure within 5% of given pressure, checking at intervals of delay (s) '''
        self.waiting = True
        time = 0
        while self.waiting:
            if not self.running:
                break
            measured_pressure = self.PGauge.get_pressure()
            self.new_data.emit(measured_pressure)
            if measured_pressure >= self.alarm_pressure:
                self.DAQ.close_relay1()
                self.active_MFC.set_sccm(0)
                self.running=False
                break
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
                
