import sys,qdarkstyle
from time import time
from PyQt5 import QtGui,QtCore
import PyQt5.QtWidgets as qw 
import pyqtgraph as pg
import numpy as np

from Control_Parameters import CtrlParamTree
from Brooks0254_BuildUp import Brooks0254, MassFlowController
from PressureGauge_BuildUp import PressureGauge
from DummyPressureThread import DummyThread

class MainControlWindow(qw.QMainWindow):
    def __init__(self, demoMode = False):
        super().__init__()
        self.demoMode = demoMode
        self.setWindowTitle('Control Panel')

        self.resize(1280,720) # non-maximized state
        # self.resize(2560, 1440)  # for home monitor
        if self.demoMode == False:
            self.showMaximized()

        self.initUI()

        if self.demoMode == True:
            print('Skipping MFC initialize')
            print('Skipping pressure gauge initialize')

            self.dummy = DummyThread(delay = 1)
            self.dummy.newData.connect(self.cryoVac_grp.update_plot)

            self.stopButton.clicked.connect(self.abort_processes)
        else:
            self.initThreads()

           
           ## connect UI items to running functions
            self.mfcButton.clicked.connect(self.setupMFCs)
            self.mks925Button.clicked.connect(self.mks902.setupGauge)
            self.mks902Button.clicked.connect(self.mks925.setupGauge)
            # self.changeTempButton.clicked.connect(lambda: self.ls335.changeSetpoint(float(self.tempInput.text())))
            self.changeTempButton.clicked.connect(self.sendTempSignal)

            self.mks902.newData.connect(self.cryoVac_grp.update_plot)
            self.mks925.newData.connect(self.rxnVac_grp.update_plot)
            self.ls335.rxnTemp.connect(self.rxnTemp_grp.update_plot)
            self.ls335.cryoTemp.connect(self.cryoTemp_grp.update_plot)

        # self.log_process()

        self.show()

    def sendTempSignal(self):
        ## reads setpoint from the line edit input box, then uses the wrapper function to pass that value to the controller
        self.ls335.setpoint = float(self.tempInput.text())
        self.ls335.ramp_rate = float(self.tempRampInput.text())
        self.ls335.changeSetpoint()
        self.ls335.changeRamp()

    def initThreads(self):
        
        if not self.demoMode:
            ## TODO: finish this area... all 4 logging plots need to have threads periodically getting data for them, plus an update function
            self.mks902 = PressureGauge('ASRL3:INSTR')
            self.mks902.newData.connect(self.rxnVac_plot.addData)
            self.mks925 = PressureGauge('ASRL5:INSTR')

            self.ls335 = Temperaturecontroller()

            self.brooks0254 = Brooks0254('ASRL2:INSTR')

    def abort_processes(self):
        ## in practice would set flows to zero
        if self.timer is not None:
            self.timer.stop()
        self.logging_timer.stop()
        if not self.demoMode:
            self.brooks0254.closeAll()

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


        self.purgeButton = qw.QPushButton("Fill with Ar")
        self.stopButton = qw.QPushButton("Stop All")
        self.purgePressureInput = qw.QLineEdit('700')
        self.purgePressureInput.setValidator(QtGui.QIntValidator())
        self.ppiLabel = qw.QLabel('Fill Pressure:')
        # self.purgeButton.clicked.connect(self.run_purge_process)
        # self.stopButton.clicked.connect(self.abort_process)


        self.doseH2SButton = qw.QPushButton("Dose with H2S")
        self.doseH2Button = qw.QPushButton("Dose with H2")
    
        self.doseH2SInput = qw.QLineEdit('10')
        self.doseH2SInput.setValidator(QtGui.QIntValidator())
        self.doseH2SLabel = qw.QLabel('H2S Dose Volume:')
        self.doseH2SRateLabel = qw.QLabel('H2S Dose Rate:')
        self.doseH2SRateInput = qw.QLineEdit('10')
        self.doseH2SRateInput.setValidator(QtGui.QIntValidator())


        self.doseH2Input = qw.QLineEdit('10')
        self.doseH2Input.setValidator(QtGui.QIntValidator())
        self.doseH2Label = qw.QLabel('H2 Dose Volume:')
        self.doseH2RateLabel = qw.QLabel('H2 Dose Rate:')
        self.doseH2RateInput = qw.QLineEdit('10')
        self.doseH2RateInput.setValidator(QtGui.QIntValidator())

        # self.doseH2SButton.clicked.connect(self.plotDosing)
    
        self.tree = CtrlParamTree()
        self.mfcButton = qw.QPushButton("Re-initialize MFCs")
        self.mks925Button = qw.QPushButton("Re-initialize MKS925 (Pirani)")
        self.mks902Button = qw.QPushButton("Re-initialize MKS902B (Piezo)")

        self.changeTempButton = qw.QPushButton("Enter Setpoint, Ramp Rate ")
        self.tempLabel = qw.QLabel("Cryo Setpoint (K)")
        self.tempInput = qw.QLineEdit('300.0')
        self.tempInput.setValidator(QtGui.QDoubleValidator())
        self.tempRateLabel = qw.QLabel("Cryo Ramp Rate (K/min)")
        self.tempRateInput = qw.QLineEdit('10.0')
        self.tempRateInput.setValidator(QtGui.QDoubleValidator())
        
        '''
        Some notes on the grid layout: 
        Because the buttons are small relative to the plots, the plots span many rows
        Used setColumnStretch based on what looks right visually, seems a little funky.

        '''
        ## Fix the row widths to be more uniform
        for r in range(24):
            layout.setRowMinimumHeight(r,1)
        
        layout.setColumnStretch(0,1)
        layout.setColumnStretch(1,2)
        layout.setColumnStretch(2,2)
        layout.setColumnStretch(3,3)
        
        layout.setContentsMargins(1,0,1,0)
        ## Add widgets to layout grid w/ row, col, rowspan, colspan
        ## Left Column:
        layout.addWidget(self.mfcButton,0,0,1,1)
        layout.addWidget(self.mks925Button,1,0,1,1)
        layout.addWidget(self.mks902Button,2,0,1,1)
        layout.addWidget(self.tree,3,0,13,1)

        ## Top middle buttons and inputs (start at col 1, row 0)
        layout.addWidget(self.purgeButton,0,1,1,1)
        layout.addWidget(self.stopButton,0,2,1,1)

        layout.addWidget(self.ppiLabel,1,1,1,1)
        layout.addWidget(self.purgePressureInput,2,1,1,1)

        layout.addWidget(self.doseH2SButton,3,1,1,1)
        layout.addWidget(self.doseH2SLabel,4,1,1,1)
        layout.addWidget(self.doseH2SInput,5,1,1,1)
        layout.addWidget(self.doseH2SRateLabel,6,1,1,1)
        layout.addWidget(self.doseH2SRateInput,7,1,1,1)
        
        layout.addWidget(self.doseH2Button,8,1,1,1)
        layout.addWidget(self.doseH2Label,9,1,1,1)
        layout.addWidget(self.doseH2Input,10,1,1,1)
        layout.addWidget(self.doseH2RateLabel,11,1,1,1)
        layout.addWidget(self.doseH2RateInput,12,1,1,1)

        layout.addWidget(self.changeTempButton,3,2,1,1)
        layout.addWidget(self.tempLabel,4,2,1,1)
        layout.addWidget(self.tempInput,5,2,1,1)
        layout.addWidget(self.tempRateLabel,6,2,1,1)
        layout.addWidget(self.tempRateInput,7,2,1,1)

        ## current process plot middle bottom (start at row 13, col 1)
        layout.addWidget(self.currentProcessPlot_grp,13,1,11,2)

        ## Right Hand column of plots
        layout.addWidget(self.cryoTemp_grp,0,3,6,1)
        layout.addWidget(self.cryoVac_grp,6,3,6,1)
        layout.addWidget(self.rxnTemp_grp,12,3,6,1)
        layout.addWidget(self.rxnVac_grp,18,3,6,1)

class BoxedPlot(qw.QWidget):

    def __init__(self, plot_title, color):
        super().__init__()
        masterLayout = qw.QVBoxLayout()
        self.pen = pg.mkPen(color, width=1.25)

        layout = qw.QVBoxLayout()
        self.group = qw.QGroupBox(plot_title)
        self.plot = pg.PlotWidget()
        self.plot.getPlotItem().showGrid(x=True, y=True, alpha=1)
        if "qdarkstyle" in sys.modules:
            self.plot.setBackground((25, 35, 45))

        self.group.setLayout(layout)
        layout.addWidget(self.plot)
        masterLayout.addWidget(self.group)

        self.setLayout(masterLayout)
        
class LoggingPlot(qw.QWidget):
    def __init__(self, plot_title, color):
        super().__init__()
        masterLayout = qw.QVBoxLayout()
        self.pen = pg.mkPen(color, width=1.25)

        layout = qw.QVBoxLayout()
        self.group = qw.QGroupBox(plot_title)
        self.plot = pg.PlotWidget()
        self.plot.getPlotItem().showGrid(x=True, y=True, alpha=1)
        if "qdarkstyle" in sys.modules:
            self.plot.setBackground((25, 35, 45))

        self.group.setLayout(layout)
        layout.addWidget(self.plot)
        masterLayout.addWidget(self.group)

        self.setLayout(masterLayout)

    def update_plot(self,new_data):
        xdata,ydata = self.trace.getData()
        xdata = np.append(xdata,time())
        ydata = np.append(ydata,new_data)
        self.trace.setData(x=xdata, y=ydata)
        self.plot.getViewBox().autoRange()

if __name__ == "__main__":
    # import pyvisa # if not demoMode

    app = qw.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    window = MainControlWindow(demoMode = True)
    
    sys.exit(app.exec())

