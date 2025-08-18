import sys,qdarkstyle
import time as t
from PyQt5 import QtGui,QtCore
import PyQt5.QtWidgets as qw 
import pyqtgraph as pg
import numpy as np
import logging
from Control_Parameters import CryoTree
# from Control_Parameters import CtrlParamTree, ProcessTree
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


        self.resize(1280,720) # non-maximized state
        # self.resize(2560, 1440)  # for home monitor
        if self.testing == False:
            self.showMaximized()

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

    def updateFlow(self,new_data):
        self.flow.setText(str(new_data))
        old_total = float(self.vol.text())
        new_total = old_total + self.logging_delay/60*new_data
        self.vol.setText(str(new_total))

    def updateLogInterval(self):
        self.logging_delay = int(self.logInput.text())
        self.logging_thread.delay = self.logging_delay
        print(f'Updating log interval to {self.logging_delay}s')

    def abortAll(self):
        ## Stop all processes (except logging) and close all valves
        ## any other safety things? change cryo?
        self.purge_thread.running = False
        self.dose_thread.running = False
        self.currentProcessPlot_grp.group.setTitle("Process aborted")
        #self.process_thread.running=False
        self.daq.close_connections()
        if not self.testing:
            self.b0254.closeAll()
            self.daq.close_relay1()
            self.daq.close_relay2()

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
                self.setRateButton.clicked.connect(self.setAr)
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

                self.mks902 = PressureGauge(self.logger,'COM3') 
                self.mks925 = PressureGauge(self.logger,'COM5')

                self.daq = DAQ(self.logger,self.testing)
                self.testDAQ0Button.clicked.connect(self.toggle_relay0)
                self.testDAQ1Button.clicked.connect(self.toggle_relay1)
                self.testDAQ2Button.clicked.connect(self.toggle_relay2)
    
                self.b0254 = Brooks0254(self.logger, 'ASRL8::INSTR') ## 
                # self.mfcButton.clicked.connect(self.setupMFCs)
                
            except OSError as e:
                self.logger.exception(e)

        
        self.logging_thread = LoggingThread(self.logger,self.ls335,self.b0254,self.mks902,self.mks925,self.save_csv.isChecked(),self.logging_delay,self.testing) 
        self.purge_thread = PurgeThread(self.testing, self.logger, self.b0254,self.mks925,self.daq)
        self.dose_thread = DoseThread(self.testing, self.logger, self.b0254,self.mks925,self.daq, self.ls335)

    def setAr(self):
        self.rate = float(self.rateInput.text())
        self.b0254.MFC2.set_sccm(self.rate)
        self.logger.info(f'Setting Ar to {self.rate} sccm')
       
    
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
        ramp_enable = self.cryoTree.getCryoValue('Control Loop')
        ramp_rate = self.cryoTree.getCryoValue('Ramp Rate (K/min)')
        setpoint = self.cryoTree.getCryoValue('Setpoint (K)')
        self.ls335.set_setpoint_ramp_parameter(loop,ramp_enable,ramp_rate)
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

        self.save_csv = qw.QCheckBox('Save to csv')
        self.logInput = qw.QLineEdit('30')
        self.logInput.setValidator(QtGui.QIntValidator())
        ## TODO: write function to update interval when this value changes
        self.logLabel = qw.QLabel('Logging Interval (sec):')
        self.logButton = qw.QPushButton("Start Logging")
        self.logButton.setCheckable(True)
        # self.logButton.setChecked(False)
        self.abortButton = qw.QPushButton("Stop Process")

        self.setRateButton = qw.QPushButton("Set Ar sccm")
        self.rateInput = qw.QLineEdit("1.0")
        self.rateInput.setValidator(QtGui.QDoubleValidator())

        self.flow = qw.QLabel('0.0')
        self.flow_units = qw.QLabel('sccm')
        self.vol = qw.QLabel('0.0')
        self.vol_units = qw.QLabel('cm3')
        self.flowBox = qw.QWidget()
        masterLayoutflow = qw.QVBoxLayout()
        flowLayout = qw.QGridLayout()
        flowgroup = qw.QGroupBox('Measured Flow')
        flowgroup.setLayout(flowLayout)
        flowLayout.addWidget(self.flow,       0,0,1,1)
        flowLayout.addWidget(self.vol,        1,0,1,1)
        flowLayout.addWidget(self.flow_units, 0,1,1,1)
        flowLayout.addWidget(self.vol_units,  1,1,1,1)
        masterLayoutflow.addWidget(flowgroup)
        self.flowBox.setLayout(masterLayoutflow)


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
        for r in range(21):
            layout.setRowMinimumHeight(r,1)
        
        layout.setColumnStretch(0,1)
        layout.setColumnStretch(1,2)
        layout.setColumnStretch(2,2)
        layout.setColumnStretch(3,3)
        
        layout.setContentsMargins(1,0,1,0)
        ## Add widgets to layout grid w/ row, col, rowspan, colspan
        ## Left Column:
        layout.addWidget(self.logLabel,        0,0,1,1)
        layout.addWidget(self.logInput,        1,0,1,1)
        layout.addWidget(self.logButton,       2,0,1,1)
        layout.addWidget(self.save_csv,        3,0,1,1)
        layout.addWidget(self.setCryoButton,   4,0,1,1)
        layout.addWidget(self.cryoTree,        5,0,10,1)

        ### Middle Column
        layout.addWidget(self.rateInput,       1,1,1,1)
        layout.addWidget(self.setRateButton,   1,2,1,1)
        layout.addWidget(self.flowBox,         2,1,2,2)
        layout.addWidget(self.testDAQ0Button,  4,2,1,1)
        layout.addWidget(self.testDAQ1Button,  5,2,1,1)
        layout.addWidget(self.testDAQ2Button,  6,2,1,1)

        
        ## current process plot middle bottom (start at row 8, col 1)
        layout.addWidget(self.currentProcessPlot_grp,8,1,10,2)

        ## Right Hand column of plots
        layout.addWidget(self.cryoTemp_grp,    0, 3,5,1)
        layout.addWidget(self.cryoVac_grp,     5, 3,5,1)
        layout.addWidget(self.rxnTemp_grp,     10,3,5,1)
        layout.addWidget(self.rxnVac_grp,      15,3,5,1)

    def closeEvent(self,event):
        if self.testing:
            print("trying to close gracefully")
       
        self.logger.info(f'Closing serial connections and GUI window.')
        self.mks902._connection.close()
        self.mks925._connection.close()
        self.b0254._connection.close()
        self.ls335.disconnect_usb()
        self.daq.close_connections()
        event.accept()


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
        self.pen = pg.mkPen(color, width=1)
        self.brush = pg.mkBrush(color)
        layout = qw.QVBoxLayout()
        self.group = qw.QGroupBox(plot_title)
        self.plot = pg.PlotWidget()
        # self.trace = pg.PlotCurveItem(pen=self.pen)
        self.trace = pg.PlotDataItem(pen=self.pen,symbol='o',symbolBrush=self.brush) ## trying this to have points and lines
        self.plot.addItem(self.trace)
        # self.trace.setSkipFiniteCheck(True)
        self.plot.getPlotItem().showGrid(x=True, y=True, alpha=0.5)
        if "qdarkstyle" in sys.modules:
            self.plot.setBackground((25, 35, 45))

        self.group.setLayout(layout)
        layout.addWidget(self.plot)
        masterLayout.addWidget(self.group)

        self.setLayout(masterLayout)

    def update_plot(self,new_data):
        xdata,ydata = self.trace.getData()
        # print(xdata,ydata)
        if xdata is None:
            xdata = np.array([t.time()])
            ydata = np.array([new_data])
        else:
            xdata = np.append(xdata,t.time())
            ydata = np.append(ydata,new_data)
        # print(xdata,ydata)
        self.trace.setData(x=xdata, y=ydata)
        # self.plot.getViewBox().autoRange()


if __name__ == "__main__":
    # import pyvisa # if not demoMode
    timestr = t.strftime('%Y%m%d-%H%M%S')
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename=f'logs/CryoControlTest_{timestr}.log',level=logging.DEBUG)
    logger.addHandler(logging.NullHandler())
    app = qw.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    window = MainControlWindow(logger = logger, testing = True)
    
    sys.exit(app.exec())

