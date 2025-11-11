import sys,qdarkstyle, os
import time as t
from PyQt5 import QtGui,QtCore
import PyQt5.QtWidgets as qw 
import pyqtgraph as pg
import numpy as np
import logging
from Control_Parameters import CryoTree
from Plots import LoggingPlot, BoxedPlot
# from Control_Parameters import CtrlParamTree, ProcessTree
# from Brooks0254_BuildUp import Brooks0254, MassFlowController
# from PressureGauge_BuildUp import PressureGauge
from DummyPressureThread import DummyThread, NotAsDumbThread
from Threads import LoggingThread, PurgeThread, DoseThread
from Instruments import PressureGauge, DAQ, Brooks0254
from lakeshore import Model335
import lakeshore

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"]= "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"


class MainControlWindow(qw.QMainWindow):
    def __init__(self, logger, max_points,testing = False):
        ## Add log_path eventually
        super().__init__()
        self.testing = testing
        self.logger = logger
        self.setWindowTitle('Control Panel')
        self.max_points = max_points

        self.resize(1280,720) # non-maximized state
        # self.resize(2560, 1440)  # for home monitor
        # if self.testing == False:
        # self.showMaximized()

        self.initUI()

        self.logging_delay = int(self.logInput.text())
        self.logInput.returnPressed.connect(self.updateLogInterval)

        self.initThreads()

        ## connect logging plots, if testing the logging thread will give dummy data
        self.logging_thread.new_cryo_pressure_data.connect(self.cryoVac_grp.update_plot)
        self.logging_thread.new_rxn_pressure_data.connect(self.rxnVac_grp.update_plot)
        self.logging_thread.new_cryo_temp_data.connect(self.cryoTemp_grp.update_plot)
        self.logging_thread.new_rxn_temp_data.connect(self.rxnTemp_grp.update_plot)
        self.logging_thread.new_flow_data.connect(self.updateFlow)

        self.logButton.clicked.connect(self.toggle_logging)
        self.setCryoButton.clicked.connect(self.change_cryo)
        self.abortButton.clicked.connect(self.abortAll)

        
        self.show()
    # def stop_logging(self):
    #     self.logging_thread.running = False

    def toggle_logging(self):
        if self.logging_thread.running:
            self.logging_thread.running = False
            print('pause logging')
        else:
            print('start logging')
            self.logging_thread.start()

    def toggle_relay0(self):
        if self.daq.relay0.read():
            self.logger.info('relay0 is open, closing relay')
            self.daq.close_relay0()

        else:
            self.logger.info('relay0 is closed, opening relay')
            self.daq.open_relay0()

    def toggle_relay1(self):
        if self.daq.relay1.read():
            self.logger.info('relay1 is open, closing relay')
            self.daq.close_relay1()

        else:
            self.logger.info('relay1 is closed, opening relay')
            self.daq.open_relay1()

    def toggle_relay2(self):
        if self.daq.relay2.read():
            self.logger.info('relay2 is open, closing relay')
            self.daq.close_relay2()
        else:
            self.logger.info('relay2 is closed, opening relay')
            self.daq.open_relay2()

    def updateFlow(self,new_data):
        (Ar_sccm,H2S_sccm) = new_data
        self.Arflow.setText(str(Ar_sccm))
        self.H2Sflow.setText(str(H2S_sccm))
        # self.flow.setText(str(new_data))
        # old_total = float(self.vol.text())
        # new_total = old_total + self.logging_delay/60*new_data
        # self.vol.setText(str(new_total))

    def updateLogInterval(self):
        self.logging_delay = int(self.logInput.text())
        self.logging_thread.delay = self.logging_delay
        print(f'Updating log interval to {self.logging_delay}s')

   
    def initThreads(self):
       ## Initialize instruments and logging thread and process thread
       ## If testing, don't error out if failed to make connections
        if self.testing:
            try:
                self.mks902 = PressureGauge(self.testing,self.logger,'COM3') ##
            except:
                self.mks902 = 'MKS902'
                print("Failed to connect to MKS902 gauge.")
            try:
                self.b0254 = Brooks0254(self.testing,self.logger,    'ASRL8::INSTR') ## 
                self.setArRateButton.clicked.connect(self.setAr)
                self.setH2SRateButton.clicked.connect(self.setH2S)
            except:
                self.b0254 = 'Brooks0254'
                print("Failed to connect to Brooks0254 MFC controller.")
            try:
                self.ls335 = Model335(baud_rate=57600)
                self.setCryoButton.clicked.connect(self.change_cryo)
            except:
                self.ls335 = 'Model335'
                print("Failed to connect to Lakeshore cryo controller.")
            try:
                self.daq = DAQ(self.testing,self.logger)
                self.testDAQ0Button.clicked.connect(self.toggle_relay0)
                self.testDAQ1Button.clicked.connect(self.toggle_relay1)
                self.testDAQ2Button.clicked.connect(self.toggle_relay2)
                self.testDAQ0Button.setChecked(self.daq.relay0.read())
                self.testDAQ1Button.setChecked(self.daq.relay1.read())
                self.testDAQ2Button.setChecked(self.daq.relay2.read())
            except:
                self.daq = 'DAQ'
                print("Failed to connect to DAQ")
            try:
                self.mks925 = PressureGauge(self.testing,self.logger, 'COM5') ## not set yet
            except:
                self.mks925 = 'MKS925'
                print("Failed to connect to MKS925.")

        else:
            try:
                self.ls335 = Model335(57600)
                self.setCryoButton.clicked.connect(self.change_cryo)

                self.mks902 = PressureGauge(self.testing,self.logger,'COM3') 
                self.mks925 = PressureGauge(self.testing,self.logger,'COM5')

                self.daq = DAQ(self.testing,self.logger)
                self.testDAQ0Button.clicked.connect(self.toggle_relay0)
                self.testDAQ1Button.clicked.connect(self.toggle_relay1)
                self.testDAQ2Button.clicked.connect(self.toggle_relay2)
    
                self.b0254 = Brooks0254(self.testing,self.logger, 'ASRL8::INSTR') ## 
                self.setArRateButton.clicked.connect(self.setAr)
                self.setH2SRateButton.clicked.connect(self.setH2S)
                
            except (OSError,Exception) as e:
                self.logger.exception(e)
                print("Failed to connect to instrument")
                self.close()


        
        self.logging_thread = LoggingThread(self.logger,self.ls335,self.b0254,self.mks902,self.mks925,self.save_csv.isChecked(),self.logging_delay,self.testing) 
        self.purge_thread = PurgeThread(self.testing, self.logger, self.b0254,self.mks925,self.daq)
        self.dose_thread = DoseThread(self.testing, self.logger, self.b0254,self.mks925,self.daq, self.ls335)

    def setAr(self):
        self.ArRate = float(self.ArRateInput.text())
        self.b0254.MFC2.set_sccm(self.ArRate)
        self.logger.info(f'Setting Ar to {self.ArRate} sccm')

    def setH2S(self):
        self.H2SRate = float(self.H2SRateInput.text())
        self.b0254.MFC1.set_sccm(self.H2SRate)
        self.logger.info(f'Setting H2S to {self.H2SRate} sccm')
       
    
    def runPurge(self):
        # t1 = t.time()
        ## get plot ready
        self.currentProcessPlot.clear() #only needed if not the first run
        self.currentProcessPlot_grp.group.setTitle("Purge Process") # use class func for QGroupBox
        self.currentProcessPlot.setLabel('left','Pressure', units='Torr')
        self.currentProcessPlot_grp.trace = pg.PlotCurveItem(pen=self.pressurePen,symbol='o',color='#08F7FE')
        self.currentProcessPlot.addItem(self.currentProcessPlot_grp.trace)
        self.purge_thread.new_pressure.connect(self.currentProcessPlot_grp.update_plot)
        self.purge_thread.message.connect(self.currentProcessPlot_grp.message.setText)
        self.purge_thread.finished.connect(self.purgeFinished)
        t2 = t.time()
        # print(f'Plot init time = {t2-t1}')
        ## get thread ready
        volume = self.processTree.getPurgeValue('Batch Volume')
        rate = self.processTree.getPurgeValue('Batch Rate')
        lowP = self.processTree.getPurgeValue('Low Pressure')
        highP = self.processTree.getPurgeValue('High Pressure')
        cycles = self.processTree.getPurgeValue('No. Cycles')
        ## setup function passes parameters from tree into thread, start creates a new thread so the gui doesn't freeze
        self.purge_thread.setup(volume,rate,lowP,highP, cycles = cycles)
        self.purge_thread.start()
        t3 = t.time()
        # print(f'Thread run time = {t3-t2}')

    def purgeFinished(self):
        # print('begin finish function')
        self.currentProcessPlot_grp.message.setText("Purge process finished")
        self.purge_thread.running = False
        ## thread.quit() and thread.exit() don't seem to do anything
        # print(f'Time to thread quit = {t.time()-t3}')

    def runH2SDose(self):
        # get plot ready
        self.currentProcessPlot.clear()
        self.currentProcessPlot_grp.group.setTitle("Dose Process")
        self.currentProcessPlot.setLabel('left',"Pressure", units='Torr')
        self.currentProcessPlot.setLabel('bottom',"Temperature",units='K')
        self.currentProcessPlot_grp.trace = pg.ScatterPlotItem(symbol='o',size=10,color='b')
        self.currentProcessPlot_grp.last_point = pg.ScatterPlotItem(symbol='+',size=30,color='#08F7FE')
        self.currentProcessPlot.addItem(self.currentProcessPlot_grp.trace)
        self.currentProcessPlot.addItem(self.currentProcessPlot_grp.last_point)
        self.dose_thread.new_data.connect(self.currentProcessPlot_grp.update_xy)
        self.dose_thread.finished.connect(self.doseFinished)
        # setup and run thread
        volume = self.processTree.getH2SDoseValue('Batch Volume')
        rate = self.processTree.getH2SDoseValue('Batch Rate')
        pressure = self.processTree.getH2SDoseValue('Cut-off Pressure')
        self.dose_thread.setup('H2S',volume,rate,pressure)
        self.dose_thread.start()
        

    def runArDose(self):
        # get plot ready
        self.currentProcessPlot.clear()
        self.currentProcessPlot_grp.group.setTitle("Dose Process")
        self.currentProcessPlot.setLabel('left',"Pressure", units='Torr')
        self.currentProcessPlot.setLabel('bottom',"Temperature",units='K')
        self.currentProcessPlot_grp.trace = pg.ScatterPlotItem(symbol='o',size=10,color='b')
        self.currentProcessPlot_grp.last_point = pg.ScatterPlotItem(symbol='+',size=30,color='#08F7FE')
        self.currentProcessPlot.addItem(self.currentProcessPlot_grp.trace)
        self.currentProcessPlot.addItem(self.currentProcessPlot_grp.last_point)
        self.dose_thread.new_data.connect(self.currentProcessPlot_grp.update_xy)
        self.dose_thread.finished.connect(self.doseFinished)
        # setup and run thread - 
        volume = self.processTree.getArDoseValue('Batch Volume')
        rate = self.processTree.getArDoseValue('Batch Rate')
        pressure = self.processTree.getArDoseValue('Cut-off Pressure')
        # dose thread should use Ar MFC
        self.dose_thread.setup('Ar',volume,rate,pressure)
        self.dose_thread.start()

    def doseFinished(self):
        self.currentProcessPlot_grp.message.setText('Dose process finished')
        self.dose_thread.running = False

    def change_cryo(self):
        loop = self.cryoTree.getCryoValue('Control Loop')
        if self.cryoTree.getCryoValue('Ramp Enable'):
            ramp_enable = 1
        else:
            ramp_enable = 0
        ramp_rate = self.cryoTree.getCryoValue('Ramp Rate (K/min)')
        setpoint = self.cryoTree.getCryoValue('Setpoint (K)')
        try:
            self.ls335.set_setpoint_ramp_parameter(loop,ramp_enable,ramp_rate)
        except lakeshore.generic_instrument.InstrumentException as ex:
            self.logger.debug(f"Lakeshore error: {ex}")
            print(f'Failed to change ramp parameter to enabled={ramp_enable}, rate={ramp_rate}')
        self.ls335.set_control_setpoint(loop, setpoint)
        self.logger.info(f'Setting cryostat loop {loop} to {setpoint} K at rate of {ramp_rate} K/min')



    def initUI(self):
        ### # Dedicated colors which look "good"
        # colors = ['#08F7FE', '#FE53BB', '#F5D300', '#00ff41', '#FF0000', '#9467bd', ]
        
        ## Create an empty box to hold all the following widgets
        self.mainbox = qw.QWidget()
        self.setCentralWidget(self.mainbox)  # Put it in the center of the main window
        layout = qw.QGridLayout()  # All the widgets will be in a grid in the main box
        self.mainbox.setLayout(layout)  # set the layout

        self.cryoTemp_grp = LoggingPlot('Cryo Temperature',"#FF035B",self.max_points)
        self.cryoVac_grp = LoggingPlot('Cryo Vacuum','#08F7FE',self.max_points)
        self.rxnVac_grp = LoggingPlot('Process Pressure','#08F7FE',self.max_points)
        self.rxnTemp_grp = LoggingPlot('Process Temperature','#FF035B',self.max_points)
        self.cryoTemp_plot = self.cryoTemp_grp.plot
        self.cryoVac_plot = self.cryoVac_grp.plot
        self.rxnVac_plot = self.rxnVac_grp.plot
        self.rxnTemp_plot = self.rxnTemp_grp.plot

        self.pressurePen = pg.mkPen(color='#FE53BB',width=2)
        self.flowPen = pg.mkPen(color='#F5D300',width=2)
        self.tempPen = pg.mkPen(color='#08F7FE',width=2)

        for plt in [self.cryoTemp_plot,self.cryoVac_plot,self.rxnTemp_plot,self.rxnVac_plot]:
            plt.setAxisItems({'bottom':pg.DateAxisItem()})

        self.cryoVac_plot.setXLink(self.cryoTemp_plot)
        self.rxnVac_plot.setXLink(self.rxnTemp_plot)
        self.rxnTemp_plot.setXLink(self.cryoTemp_plot)

        # self.currentProcessPlot_grp = BoxedPlot('Current Process','#08F7FE')
        # self.currentProcessPlot = self.currentProcessPlot_grp.plot
        # self.cp2 = None

        self.save_csv = qw.QCheckBox('Save to csv')
        self.logInput = qw.QLineEdit('30')
        self.logInput.setValidator(QtGui.QIntValidator())
        ## TODO: write function to update interval when this value changes
        self.logLabel = qw.QLabel(' Interval (sec):')
        self.logButton = qw.QPushButton("Start Logging")
        self.logButton.setCheckable(True)
        # self.logButton.setChecked(False)
        self.abortButton = qw.QPushButton("Stop Process")
        self.abortButton.setShortcut('Ctrl+Q')

        self.setArRateButton = qw.QPushButton("Set Ar sccm")
        self.ArRateInput = qw.QLineEdit("1.0")
        self.ArRateInput.setValidator(QtGui.QDoubleValidator())
        self.setH2SRateButton = qw.QPushButton("Set H2S sccm")
        self.H2SRateInput = qw.QLineEdit("1.0")
        self.H2SRateInput.setValidator(QtGui.QDoubleValidator())

        self.Arflow = qw.QLabel('0.0')
        self.Arflow_units = qw.QLabel('sccm Ar')
        # self.vol = qw.QLabel('0.0')
        # self.vol_units = qw.QLabel('cm3')
        self.H2Sflow = qw.QLabel('0.0')
        self.H2Sflow_units = qw.QLabel('sccm H2S')
        self.flowBox = qw.QWidget()
        masterLayoutflow = qw.QVBoxLayout()
        flowLayout = qw.QGridLayout()
        flowgroup = qw.QGroupBox('Measured Flow')
        flowgroup.setLayout(flowLayout)
        flowLayout.addWidget(self.Arflow,       0,0,1,1)
        flowLayout.addWidget(self.H2Sflow,        1,0,1,1)
        flowLayout.addWidget(self.Arflow_units, 0,1,1,1)
        flowLayout.addWidget(self.H2Sflow_units,  1,1,1,1)
        masterLayoutflow.addWidget(flowgroup)
        self.flowBox.setLayout(masterLayoutflow)

        plotlayout = qw.QVBoxLayout()
        self.plotgroup = qw.QWidget()
        plotlayout.addWidget(self.cryoTemp_grp)
        plotlayout.addWidget(self.rxnTemp_grp)
        plotlayout.addWidget(self.rxnVac_grp)
        plotlayout.addWidget(self.cryoVac_grp)
        self.plotgroup.setLayout(plotlayout)

        self.testDAQ0Button = qw.QPushButton("Toggle DAQ Relay 0")
        self.testDAQ0Button.setCheckable(True)
        self.testDAQ1Button = qw.QPushButton("Toggle DAQ Relay 1")
        self.testDAQ1Button.setCheckable(True)
        self.testDAQ2Button = qw.QPushButton("Toggle DAQ Relay 2")
        self.testDAQ2Button.setCheckable(True)

        self.setCryoButton = qw.QPushButton("Change Cryo Setpoint")
        self.cryoTree = CryoTree()

        '''
        Some notes on the grid layout: 
        Because the buttons are small relative to the plots, the plots span many rows
        Used setColumnStretch based on what looks right visually, seems a little funky.

        '''
        ## Fix the row widths to be more uniform
        for r in range(9):
            # layout.setRowMinimumHeight(r,1)
            layout.setRowStretch(r,1)
        # for c in range(4):
        #     layout.setColumnStretch(c,1)
        layout.setColumnStretch(0,1)
        layout.setColumnStretch(1,1)
        layout.setColumnStretch(2,1)
        layout.setColumnStretch(3,3)
        
        layout.setContentsMargins(1,0,1,0)
        ## Add widgets to layout grid w/ row, col, rowspan, colspan
        ## Left Column:
        layout.addWidget(self.logLabel,        0,0,1,1)
        layout.addWidget(self.logInput,        1,0,1,1)
        layout.addWidget(self.logButton,       2,0,1,1)
        layout.addWidget(self.save_csv,        3,0,1,1)
        layout.addWidget(self.testDAQ0Button,  4,0,1,1)
        layout.addWidget(self.testDAQ1Button,  5,0,1,1)
        layout.addWidget(self.testDAQ2Button,  6,0,1,1)
        layout.addWidget(self.setCryoButton,   7,0,1,1)
        layout.addWidget(self.cryoTree,        8,0,3,2)

        ### Middle Column
        layout.addWidget(self.abortButton,       0,1,1,1)
        layout.addWidget(self.ArRateInput,       1,1,1,1)
        layout.addWidget(self.setArRateButton,   1,2,1,1)
        layout.addWidget(self.H2SRateInput,      2,1,1,1)
        layout.addWidget(self.setH2SRateButton,  2,2,1,1)
        layout.addWidget(self.flowBox,           3,1,2,2)


        
        ## current process plot middle bottom (start at row 8, col 1)
        # layout.addWidget(self.currentProcessPlot_grp,8,1,10,2)

        ## Right Hand column of plots
        layout.addWidget(self.plotgroup,       0, 3,10,1)
        # layout.addWidget(self.cryoTemp_grp,    0, 3,1,2)
        # layout.addWidget(self.cryoVac_grp,     2, 3,3,2)
        # layout.addWidget(self.rxnTemp_grp,     5, 3,3,2)
        # layout.addWidget(self.rxnVac_grp,      8, 3,3,2)

    def abortAll(self):
        ## Stop all processes (except logging) and close all valves
        ## any other safety things? change cryo?
        self.purge_thread.running = False
        self.dose_thread.running = False
        # self.currentProcessPlot_grp.group.setTitle("Process aborted")
        #self.process_thread.running=False
        # self.daq.close_connections()
        if self.testing:
            print('Aborting all')

        self.b0254.closeAll()
        self.daq.close_relay0()
        self.daq.close_relay1()
        self.daq.close_relay2()

    def closeEvent(self,event):
        if self.testing:
            print("trying to close gracefully")
        self.purge_thread.running = False
        self.dose_thread.running = False
        self.logging_thread.running = False
        self.logger.info(f'Closing serial connections and GUI window.')
        self.mks902._connection.close()
        self.mks925._connection.close()
        if self.b0254 != 'Brooks0254':
            self.b0254._connection.close()
        if self.ls335 != 'Model335':
            self.ls335.disconnect_usb()
        self.daq.close_connections()
        event.accept()



if __name__ == "__main__":
    # import pyvisa # if not demoMode
    timestr = t.strftime('%Y%m%d-%H%M%S')
    logger = logging.getLogger(__name__)

    log_file = os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"), f"CryoControlTest_{timestr}.log")

    logging.basicConfig(filename=log_file,level=logging.DEBUG)
    logger.addHandler(logging.NullHandler())
    app = qw.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    font = QtGui.QFont()
    font.setPointSize(12)   # try 12–14 instead of default ~8–9
    app.setFont(font)
    window = MainControlWindow(logger = logger,max_points=1000, testing = True)
    
    sys.exit(app.exec())

