import sys,qdarkstyle
import time as t
from PyQt5 import QtGui,QtCore
import PyQt5.QtWidgets as qw 
import pyqtgraph as pg
import numpy as np
import logging

from Control_Parameters import CtrlParamTree, ProcessTree
# from Brooks0254_BuildUp import Brooks0254, MassFlowController
# from PressureGauge_BuildUp import PressureGauge
from DummyPressureThread import DummyThread, NotAsDumbThread
from Threads import LoggingThread, PurgeThread, DoseThread
from Instruments import PressureGauge, DAQ, Brooks0254
from lakeshore import Model335

class MainControlWindow(qw.QMainWindow):
    def __init__(self, logger, testing = False):
        ## Add log_path eventually
        super().__init__()
        self.testing = testing
        self.logger = logger
        self.setWindowTitle('Control Panel')


        # self.resize(1280,720) # non-maximized state
        self.resize(2560, 1440)  # for home monitor
        if self.testing == False:
            self.showMaximized()

        self.initUI()

        self.logging_delay = int(self.logInput.text())
        self.logInput.returnPressed.connect(self.updateLogInterval)


        if self.testing:
            print('Skipping MFC initialize')
            print('Skipping pressure gauge initialize')

            # self.dummy = DummyThread(delay = 3000)
            # self.dummy.newData.connect(self.cryoVac_grp.update_plot)
            # self.dummy.start()

            self.initThreads()

        else:
            self.initThreads()

           ## connect UI items to running functions
            self.mfcButton.clicked.connect(self.setupMFCs)
            self.mks925Button.clicked.connect(self.mks902.setupGauge)
            self.mks902Button.clicked.connect(self.mks925.setupGauge)
            # self.changeTempButton.clicked.connect(lambda: self.ls335.changeSetpoint(float(self.tempInput.text())))
            self.changeTempButton.clicked.connect(self.sendTempSignal)

        ## connect logging plots, if testing the logging thread will give dummy data
        self.logging_thread.new_cryo_pressure_data.connect(self.cryoVac_grp.update_plot)
        self.logging_thread.new_rxn_pressure_data.connect(self.rxnVac_grp.update_plot)
        self.logging_thread.new_cryo_temp_data.connect(self.cryoTemp_grp.update_plot)
        self.logging_thread.new_rxn_temp_data.connect(self.rxnTemp_grp.update_plot)

        self.logButton.clicked.connect(self.logging_thread.start)
        self.stop_log_button.clicked.connect(self.stop_logging)
        self.purgeButton.clicked.connect(self.runPurge)
        self.abortButton.clicked.connect(self.abortAll)
        self.doseH2SButton.clicked.connect(self.runH2SDose)
        
        self.show()
    def stop_logging(self):
        self.logging_thread.running = False

    def handleLogging(self):
        if self.logging_thread.running == False:
        # if self.logButton.isChecked == False: # not sure which one (or both?) to use as condition
            self.logging_thread.running = True
        else:
            self.logging_thread.running = False
    def updateLogInterval(self):
        self.logging_delay = int(self.logInput.text())
        self.logging_thread.delay = self.logging_delay

    def sendDemoSignal(self):
        # Testing out thread functon
        self.nadt.setpoint = float(self.tempInput.text())
        self.nadt.updateCryoSetpoint()

    def sendTempSignal(self):
        ## reads setpoint from the line edit input box, then uses the wrapper function to pass that value to the controller
        self.ls335.setpoint = float(self.tempInput.text())
        self.ls335.ramp_rate = float(self.tempRampInput.text())
        self.ls335.changeSetpoint()
        self.ls335.changeRamp()

    def abortAll(self):
        ## Stop all processes (except logging) and close all valves
        ## any other safety things? change cryo?
        self.purge_thread.running = False
        self.dose_thread.running = False
        self.currentProcessPlot_grp.group.setTitle("Process aborted")
        #self.process_thread.running=False
        if not self.testing:
            self.b0254.closeAll()
            self.daq.close_relay1()
            self.daq.close_relay2()

    def initThreads(self):
       ## Initialize instruments and logging thread and process thread
        if self.testing:
            try:
                self.mks902 = PressureGauge(self.logger,'ASRL3::INSTR') ##
            except:
                self.mks902 = 'MKS902'
            try:
                self.b0254 = Brooks0254(self.logger,    'ASRL4::INSTR') ## 
            except:
                self.b0254 = 'Brooks0254'
            try:
                self.ls335 = Model335(57600)
                self.daq = DAQ(self.logger)
                self.mks925 = PressureGauge('ASRL6::INSTR') ## not set yet
            except:
                self.ls335 = 'Model335'
                self.daq = 'DAQ'
                self.mks925 = 'MKS925'

        else:
            try:
                self.ls335 = Model335(57600)
                self.daq = DAQ(self.logger)
                self.mks902 = PressureGauge('ASRL3::INSTR') 
                self.mks925 = PressureGauge('ASRL6::INSTR') ## not set yet
                self.b0254 = Brooks0254('ASRL4::INSTR') ## 
            except OSError as e:
                self.logger.exception(e)

        
        self.logging_thread = LoggingThread(self.logger,self.ls335,self.b0254,self.mks902,self.mks925,self.logging_delay,self.testing) 
        self.purge_thread = PurgeThread(self.testing, self.logger, self.b0254,self.mks925,self.daq)
        self.dose_thread = DoseThread(self.testing, self.logger, self.b0254,self.mks925,self.daq, self.ls335)

       
    
    def runPurge(self):
        # t1 = t.time()
        ## get plot ready
        self.currentProcessPlot.clear() #only needed if not the first run
        self.currentProcessPlot_grp.group.setTitle("Purge Process") # use class func for QGroupBox
        self.currentProcessPlot.setLabel('left','Pressure', units='Torr')
        self.currentProcessPlot_grp.trace = pg.PlotCurveItem(pen=self.pressurePen,symbol='o')
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

    def doseFinished(self):
        self.currentProcessPlot_grp.message.setText('Dose process finished')
        self.dose_thread.running = False

    def initUI(self):
        ### # Dedicated colors which look "good"
        # colors = ['#08F7FE', '#FE53BB', '#F5D300', '#00ff41', '#FF0000', '#9467bd', ]
        
        ## Create an empty box to hold all the following widgets
        self.mainbox = qw.QWidget()
        self.setCentralWidget(self.mainbox)  # Put it in the center of the main window
        layout = qw.QGridLayout()  # All the widgets will be in a grid in the main box
        self.mainbox.setLayout(layout)  # set the layout

        self.cryoTemp_grp = LoggingPlot('Cryo Temperature','#08F7FE')
        self.cryoVac_grp = LoggingPlot('Cryo Vacuum','#08F7FE')
        self.rxnVac_grp = LoggingPlot('Process Pressure','#08F7FE')
        self.rxnTemp_grp = LoggingPlot('Process Temperature','#08F7FE')
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

        self.currentProcessPlot_grp = BoxedPlot('Current Process','#08F7FE')
        self.currentProcessPlot = self.currentProcessPlot_grp.plot
        self.cp2 = None


       
        self.logInput = qw.QLineEdit('30')
        self.logInput.setValidator(QtGui.QIntValidator())
        ## TODO: write function to update interval when this value changes
        self.logLabel = qw.QLabel('Logging Interval (s):')
        self.logButton = qw.QPushButton("Start Logging")
        self.stop_log_button = qw.QPushButton("Stop Logging")
        
        # self.logButton.clicked.connect(self.handleLogging)
        # self.logButton.setCheckable(True)
        # self.logButton.setChecked(False)

        self.doseH2SButton = qw.QPushButton("Dose with H2S")
        self.doseH2Button = qw.QPushButton("Dose with H2")
        self.purgeButton = qw.QPushButton("Run purge") 
        self.abortButton = qw.QPushButton("Stop Process")

        self.ctrlTree = CtrlParamTree()
        self.mfcButton = qw.QPushButton("Re-initialize MFCs")
        self.mks925Button = qw.QPushButton("Re-initialize MKS925 (Pirani)")
        self.mks902Button = qw.QPushButton("Re-initialize MKS902B (Piezo)")

        self.processTree = ProcessTree()

        
        '''
        Some notes on the grid layout: 
        Because the buttons are small relative to the plots, the plots span many rows
        Used setColumnStretch based on what looks right visually, seems a little funky.

        '''
        ## Fix the row widths to be more uniform
        for r in range(16):
            layout.setRowMinimumHeight(r,1)
        
        layout.setColumnStretch(0,1)
        layout.setColumnStretch(1,2)
        layout.setColumnStretch(2,2)
        layout.setColumnStretch(3,3)
        
        layout.setContentsMargins(1,0,1,0)
        ## Add widgets to layout grid w/ row, col, rowspan, colspan
        ## Left Column:
        layout.addWidget(self.mfcButton,       0,0,1,1)
        layout.addWidget(self.mks925Button,    1,0,1,1)
        layout.addWidget(self.mks902Button,    2,0,1,1)
        layout.addWidget(self.ctrlTree,        3,0,13,1)

        ## Top middle buttons and inputs (start at col 1, row 0)
        layout.addWidget(self.processTree,     0,1,8,1)

        layout.addWidget(self.logLabel,        0,2,1,1)
        layout.addWidget(self.logInput,        1,2,1,1)

        layout.addWidget(self.logButton,       2,2,1,1)
        layout.addWidget(self.stop_log_button, 3,2,1,1)
        layout.addWidget(self.purgeButton,     4,2,1,1)
        layout.addWidget(self.doseH2SButton,   5,2,1,1)
        layout.addWidget(self.doseH2Button,    6,2,1,1)
        layout.addWidget(self.abortButton,     7,2,1,1)

        ## current process plot middle bottom (start at row 8, col 1)
        layout.addWidget(self.currentProcessPlot_grp,9,1,7,2)

        ## Right Hand column of plots
        layout.addWidget(self.cryoTemp_grp,0,3,4,1)
        layout.addWidget(self.cryoVac_grp,4,3,4,1)
        layout.addWidget(self.rxnTemp_grp,8,3,4,1)
        layout.addWidget(self.rxnVac_grp,12,3,4,1)


class BoxedPlot(qw.QWidget):
    def __init__(self, plot_title, color):
        super().__init__()
        masterLayout = qw.QVBoxLayout()
        self.pen = pg.mkPen(color, width=2)

        layout = qw.QVBoxLayout()
        self.group = qw.QGroupBox(plot_title)
        self.plot = pg.PlotWidget()
        self.plot.getPlotItem().showGrid(x=True, y=True, alpha=1)
        if "qdarkstyle" in sys.modules:
            self.plot.setBackground((25, 35, 45))
        self.group.setLayout(layout)
        self.message = qw.QLabel("Inactive")
        layout.addWidget(self.message)
        layout.addWidget(self.plot)
        masterLayout.addWidget(self.group)

        self.setLayout(masterLayout)
    
    # def set_title(self,new_title):


    def update_plot(self,new_data):
        # print(f'Add to plot {new_data}')
        xdata,ydata = self.trace.getData()
        xdata = np.append(xdata,t.time())
        ydata = np.append(ydata,new_data)
        self.trace.setData(x=xdata, y=ydata)
        # self.plot.getViewBox().autoRange()

    def update_xy(self,new_data,emphasize_last=True):
        # instead of time series updates x-y data
        xdata,ydata = self.trace.getData()
        xdata = np.append(xdata,new_data[0])
        ydata = np.append(ydata,new_data[1])
        self.trace.setData(x=xdata,y=ydata)
        if emphasize_last:
            self.last_point.setData(x=[new_data[0]],y=[new_data[1]])
        
class LoggingPlot(qw.QWidget):
    def __init__(self, plot_title, color):
        super().__init__()
        masterLayout = qw.QVBoxLayout()
        self.pen = pg.mkPen(color, width=2)
        layout = qw.QVBoxLayout()
        self.group = qw.QGroupBox(plot_title)
        self.plot = pg.PlotWidget()
        self.trace = pg.PlotCurveItem(pen=self.pen)
        self.plot.addItem(self.trace)
        # self.trace.setSkipFiniteCheck(True)
        self.plot.getPlotItem().showGrid(x=True, y=True, alpha=1)
        if "qdarkstyle" in sys.modules:
            self.plot.setBackground((25, 35, 45))

        self.group.setLayout(layout)
        layout.addWidget(self.plot)
        masterLayout.addWidget(self.group)

        self.setLayout(masterLayout)

    def update_plot(self,new_data):
        xdata,ydata = self.trace.getData()
        # print(xdata,ydata)
        xdata = np.append(xdata,t.time())
        ydata = np.append(ydata,new_data)
        self.trace.setData(x=xdata, y=ydata)
        # self.plot.getViewBox().autoRange()


if __name__ == "__main__":
    # import pyvisa # if not demoMode
    timestr = t.strftime('%Y%m%d-%H%M%S')
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename=f'logs/CryoControlTest_{timestr}.log',level=logging.INFO)
    logger.addHandler(logging.NullHandler())
    app = qw.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    window = MainControlWindow(logger = logger, testing = True)
    
    sys.exit(app.exec())

