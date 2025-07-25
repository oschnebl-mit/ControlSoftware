import sys,qdarkstyle
import time as t
from PyQt5 import QtGui,QtCore
import PyQt5.QtWidgets as qw 
import pyqtgraph as pg
import numpy as np
import logging

from Instruments import PressureGauge, DAQ, Brooks0254

class PressureLoggingThread(QtCore.QThread):
    new_rxn_pressure_data = QtCore.pyqtSignal(float)
    new_cryo_pressure_data = QtCore.pyqtSignal(float)
    new_flow_data = QtCore.pyqtSignal(float)

    def __init__(self,logger, rxnGauge, cryoGauge,b0254,delay=30):
        super().__init__()
        self.logger = logger
        self.delay=delay

        self.rxnPressure = rxnGauge
        self.cryoPressure = cryoGauge
        self.b0254 = b0254

    def run(self):
        self.running = True
        while self.running:
            self.new_rxn_pressure_data.emit(self.rxnPressure.get_pressure())
            self.new_cryo_pressure_data.emit(self.cryoPressure.get_pressure())
            if self.b0254 != 'Brooks0254':
                meas = self.b0254.MFC2.get_measured_values()
                self.new_flow_data.emit(meas[0])
        QtCore.QThread.msleep(self.delay*1000)

class DoseThread(QtCore.QThread):
    new_flow_data = QtCore.pyqtSignal(float)
    def __init__(self,logger,MFC,rate,volume,target_pressure,alarm_pressure,delay=10):
        super().__init__()
        self.logger = logger
        self.MFC = MFC
        self.rate = rate
        self.vol = volume
        self.pressure = target_pressure
        self.alarm = alarm_pressure

    def run(self):
        self.running= True

        self.timeout = self.vol/self.rate ## should be in minutes for scc / sccm
        self.MFC.set_sccm(self.rate)
        self.logger.info(f'Setting Ar to {self.rate} sccm and waiting for {self.timeout} min')
        for n in self.timeout*60/10:
            pv,tot,time = self.MFC.get_measured_values()
            self.new_flow_data.emit(pv)
            QtCore.QThread.msleep(10*1000)
        self.MFC.set_sccm(0.0)
        self.logger.info(f'Setting Ar to 0 sccm')
        self.running = False


class SimpleControlWindow(qw.QMainWindow):
    def __init__(self,logger):
        ''' For simple testing of MFCs and DAQ'''

        super().__init__()
        self.logger = logger
        self.resize(1280,720) # non-maximized state

        self.initUI()
        self.initInstruments()
        if self.mks902 != 'MKS902':
            self.start_logging() ## if both gauges connect, start logging pressure and displaying it
        self.show()

    def start_logging(self):
        self.logging_thread = PressureLoggingThread(self.logger,self.mks902,self.mks925,self.b0254)
        self.logging_thread.new_cryo_pressure_data.connect(self.updateCryoPressure)
        self.logging_thread.new_rxn_pressure_data.connect(self.updateRxnPressure)
        if self.b0254 != 'Brooks0254':
            self.logging_thread.new_flow_data.connect(self.updateFlow)
        else:
            print('Only updating pressure, not flow')
        self.logging_thread.start()

    def updateCryoPressure(self,new_data):
        self.cryoPressure.setText(str(new_data))

    def updateRxnPressure(self,new_data):
        self.rxnPressure.setText(str(new_data))

    def updateFlow(self,new_data):
        self.flow.setText(str(new_data))

    def abort(self):
        self.daq.close_relay0()
        self.daq.close_relay1()
        self.daq.close_relay2()
        self.b0254.MFC2.set_sccm(0)
    
    def setAr(self):
        self.rate = float(self.rateInput.text())
        self.b0254.MFC2.set_sccm(self.rate)
        self.logger.info(f'Setting Ar to {self.rate} sccm')

    def doseAr(self):
        self.rate = float(self.drateInput.text())
        self.vol = float(self.dvolInput.text())
        self.target_pressure = float(self.dpressInput.text())
        self.alarm_pressure = float(self.dalarmInput.text())

        self.dose_thread = DoseThread(self.logger,self.b0254.MFC2, self.rate,self.vol,self.target_pressure,self.alarm_pressure)
        self.logging_thread.new_flow_data.disconnect(self.updateFlow)
        self.dose_thread.new_flow_data.connect(self.updateFlow)
        self.dose_thread.start()


    def closeEvent(self,event):
       ## doesn't account for only some instruments being on 
        self.logging_thread.running = False
        self.logger.info(f'Closing serial connections and GUI window.')
        self.daq.close_connections()
        self.b0254._connection.close()
        self.mks902._connection.close()
        self.mks925._connection.close()
        event.accept()

    def initInstruments(self):
        try:
            self.b0254 = Brooks0254(False, self.logger,    'ASRL8::INSTR') ## 
            self.setRateButton.clicked.connect(self.setAr)
            self.doseArButton.clicked.connect(self.doseAr)
            self.abortButton.clicked.connect(self.abort)
        except:
            self.b0254 = 'Brooks0254'
            print("Failed to connect to Brooks0254 MFC controller.")
        try:
            self.daq = DAQ(False,self.logger)
            self.testDAQ0Button.clicked.connect(self.toggle_relay0)
            self.testDAQ1Button.clicked.connect(self.toggle_relay1)
            self.testDAQ2Button.clicked.connect(self.toggle_relay2)
        except:
            self.daq = 'DAQ'
            print("Failed to connect to DAQ")
        try:
            self.mks925 = PressureGauge(False,self.logger, 'COM5') ## 
        except:
            self.mks925 = 'MKS925'
            print("Failed to connect to MKS925.")
        try:
            self.mks902 = PressureGauge(False,self.logger,'COM3') ##
        except:
            self.mks902 = 'MKS902'
            print("Failed to connect to MKS902 gauge.")

    def toggle_relay0(self):
        if self.daq.relay0.read():
            self.logger.info('relay0 is open, closing relay')
            self.daq.close_relay0()
            # self.testDAQ0Button.setChecked(False)
        else:
            self.logger.info('relay0 is closed, opening relay')
            self.daq.open_relay0()
            # self.testDAQ0Button.setChecked(True)

    def toggle_relay1(self):
        if self.daq.relay1.read():
            self.logger.info('relay1 is open, closing relay')
            self.daq.close_relay1()
            # self.testDAQ1Button.setChecked(False)
        else:
            self.logger.info('relay1 is closed, opening relay')
            self.daq.open_relay1()
            # self.testDAQ1Button.setChecked(True)

    def toggle_relay2(self):
        if self.daq.relay2.read():
            self.logger.info('relay2 is open, closing relay')
            self.daq.close_relay2()
        else:
            self.logger.info('relay2 is closed, opening relay')
            self.daq.open_relay2()

    def initUI(self):
         ## Create an empty box to hold all the following widgets
        self.mainbox = qw.QWidget()
        self.setCentralWidget(self.mainbox)  # Put it in the center of the main window
        layout = qw.QGridLayout()  # All the widgets will be in a grid in the main box
        self.mainbox.setLayout(layout)  # set the layout

        self.abortButton = qw.QPushButton("Stop All")
        self.abortButton.setStyleSheet("background-color: red")

        self.testDAQ0Button = qw.QPushButton("Toggle DAQ Relay 0")
        self.testDAQ0Button.setCheckable(True)
        self.testDAQ1Button = qw.QPushButton("Toggle DAQ Relay 1")
        self.testDAQ1Button.setCheckable(True)
        self.testDAQ2Button = qw.QPushButton("Toggle DAQ Relay 2")
        self.testDAQ2Button.setCheckable(True)

        self.setRateButton = qw.QPushButton("Set Ar sccm")
        self.rateInput = qw.QLineEdit("1.0")
        self.rateInput.setValidator(QtGui.QDoubleValidator())

        ## d for dose box
        self.dbox = qw.QWidget()
        masterLayout = qw.QVBoxLayout()
        dlayout = qw.QVBoxLayout()
        dgroup = qw.QGroupBox("Dose Ar")
        dgroup.setLayout(dlayout)
        self.drateLabel = qw.QLabel('Ar rate')
        self.drateInput = qw.QLineEdit("0.0")
        self.drateInput.setValidator(QtGui.QDoubleValidator())
        self.dvolLabel = qw.QLabel('Ar volume')
        self.dvolInput = qw.QLineEdit("0.0")
        self.dvolInput.setValidator(QtGui.QDoubleValidator())
        self.dpressLabel = qw.QLabel('Target Pressure')
        self.dpressInput = qw.QLineEdit("0.0")
        self.dpressInput.setValidator(QtGui.QDoubleValidator())
        self.dalarmLabel = qw.QLabel('Alarm Pressure')
        self.dalarmInput = qw.QLineEdit('0.0')
        self.dalarmInput.setValidator(QtGui.QDoubleValidator())
        
        dlayout.addWidget(self.drateLabel)
        dlayout.addWidget(self.drateInput)
        dlayout.addWidget(self.dvolLabel)
        dlayout.addWidget(self.dvolInput)
        dlayout.addWidget(self.dpressLabel)
        dlayout.addWidget(self.dpressInput)
        dlayout.addWidget(self.dalarmLabel)
        dlayout.addWidget(self.dalarmInput)

        masterLayout.addWidget(dgroup)
        self.dbox.setLayout(masterLayout)

        self.doseArButton = qw.QPushButton("Dose Ar")

        self.rxnPressure = qw.QLabel('0.0')
        self.cryoPressure = qw.QLabel('0.0')

        self.rpressBox = qw.QWidget()
        masterLayoutrp = qw.QVBoxLayout()
        rplayout = qw.QVBoxLayout()
        rpgroup = qw.QGroupBox('Rxn Pressure')
        rpgroup.setLayout(rplayout)
        rplayout.addWidget(self.rxnPressure)
        masterLayoutrp.addWidget(rpgroup)
        self.rpressBox.setLayout(masterLayoutrp)

        self.cpressBox = qw.QWidget()
        masterLayoutcp = qw.QVBoxLayout()
        cplayout = qw.QVBoxLayout()
        cpgroup = qw.QGroupBox('Cryo Pressure')
        cpgroup.setLayout(cplayout)
        cplayout.addWidget(self.cryoPressure)
        masterLayoutcp.addWidget(cpgroup)
        self.cpressBox.setLayout(masterLayoutcp)

        self.flow = qw.QLabel('0.0')
        self.flowBox = qw.QWidget()
        masterLayoutflow = qw.QVBoxLayout()
        flowLayout = qw.QVBoxLayout()
        flowgroup = qw.QGroupBox('Measured Flow')
        flowgroup.setLayout(flowLayout)
        flowLayout.addWidget(self.flow)
        masterLayoutflow.addWidget(flowgroup)
        self.flowBox.setLayout(masterLayoutflow)

        # self.rpresslabel = qw.QLabel('Rxn Pressure')
        # self.cpresslabel = qw.QLabel('Cryo Pressure')
    

        for r in range(10):
            layout.setRowMinimumHeight(r,1)
        # layout.setContentsMargins(1,1,1,1)
        ## Add widgets to layout grid w/ row, col, rowspan, colspan
        layout.addWidget(self.testDAQ0Button,   0,0,1,1)
        layout.addWidget(self.testDAQ1Button,   1,0,1,1)
        layout.addWidget(self.testDAQ2Button,   2,0,1,1)

        layout.addWidget(self.rateInput,        0,1,1,1)
        layout.addWidget(self.setRateButton,    0,2,1,1)

        layout.addWidget(self.dbox,             1,1,6,1)
        layout.addWidget(self.doseArButton,     2,2,1,1)

        layout.addWidget(self.abortButton,      0,3,1,1)
        layout.addWidget(self.flowBox,          1,2,1,1)
        layout.addWidget(self.rpressBox,        2,3,2,1)
        layout.addWidget(self.cpressBox,        5,3,2,1)
        # layout.addWidget(self.rpresslabel,      0,3,1,1)
        # layout.addWidget(self.rxnPressure,      1,3,1,1)
        # layout.addWidget(self.cpresslabel,      2,3,1,1)
        # layout.addWidget(self.cryoPressure,     3,3,1,1)
        


if __name__ == "__main__":
    # import pyvisa # if not demoMode
    timestr = t.strftime('%Y%m%d-%H%M%S')
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename=f'logs/CryoControlTest_{timestr}.log',level=logging.DEBUG)
    logger.addHandler(logging.NullHandler())
    app = qw.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    window = SimpleControlWindow(logger = logger)
    
    sys.exit(app.exec())

