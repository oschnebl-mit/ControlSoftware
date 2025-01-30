import sys,qdarkstyle,pyvisa
from time import time
from PyQt5 import QtGui,QtCore
import PyQt5.QtWidgets as qw 
import pyqtgraph as pg
import numpy as np

from Control_Parameters import BrooksParamTree
from Brooks0254_BuildUp import Brooks0254, MassFlowController

# from TubeFurnaceFillGui import TubeFillWindow

class MainControlWindow(qw.QMainWindow):
    def __init__(self, pyvisaConnection):
        super().__init__()
        self.setWindowTitle('Control Panel')

        self.resize(1280, 720)  # Non- maximized size
        # self.showMaximized()
        
        ## Create an empty box to hold all the following widgets
        self.mainbox = qw.QWidget()
        self.setCentralWidget(self.mainbox)  # Put it in the center of the main window
        layout = qw.QGridLayout()  # All the widgets will be in a grid in the main box
        self.mainbox.setLayout(layout)  # set the layout

        self.temp_plot = pg.PlotWidget()
        self.highVac_plot = pg.PlotWidget()
        self.rxnVac_plot = pg.PlotWidget()
        self.rxnTemp_plot = pg.PlotWidget()

        # font=QtGui.QFont()
        # font.setPixelSize(45)
        # for plt in [self.temp_plot,self.highVac_plot,self.rxnVac_plot]:
        #     plt.getAxis("left").tickFont = font

        self.pressurePen = pg.mkPen(color='#00ff41',width=3)
        self.flowPen = pg.mkPen(color='#F5D300',width=3)
        self.tempPen = pg.mkPen(color='#08F7FE',width=3)

        self.temp_plot.setLabel('left',"Temperature",units="K",color='#08F7FE',**{'font-size': '12pt'})
        self.highVac_plot.setLabel('left',"High Vac Pressure",units = "Torr",color='#00ff41',**{'font-size': '12pt'})
        self.rxnTemp_plot.setLabel('left',"Process Temperature",units="K",color='#08F7FE',**{'font-size': '12pt'})
        self.rxnVac_plot.setLabel('left',"Process Pressure",units = "Torr",color='#00ff41',**{'font-size': '12pt'})

        self.highVac_plot.setXLink(self.temp_plot)
        self.rxnVac_plot.setXLink(self.rxnTemp_plot)

        self.rxnVac_plot.setLabel('bottom',"Time",units='min',color='#e0e0e0',**{'font-size':'12pt'})

        self.currentProcessPlot = pg.PlotWidget()
        self.cp2 = None

        self.purgeButton = qw.QPushButton("Fill with Ar")
        self.stopButton = qw.QPushButton("Stop All")
        self.purgePressureInput = qw.QLineEdit()
        self.purgePressureInput.setText('700')
        self.purgePressureInput.setValidator(QtGui.QIntValidator())
        self.ppiLabel = qw.QLabel('Fill Pressure:')
        self.purgeButton.clicked.connect(self.run_purge_process)
        self.stopButton.clicked.connect(self.abort_process)

        self.buttonGroup = qw.QHBoxLayout()
        self.purgeGroup = qw.QVBoxLayout()
        self.buttonGroup.addWidget(self.purgeButton)
        self.buttonGroup.addWidget(self.stopButton)
        self.purgeGroup.addLayout(self.buttonGroup)
        self.purgeGroup.addWidget(self.ppiLabel)
        self.purgeGroup.addWidget(self.purgePressureInput)

        self.doseButtonGroup = qw.QHBoxLayout()
        self.doseH2SButton = qw.QPushButton("Dose with H2S")
        self.doseH2Button = qw.QPushButton("Dose with H2")
        self.doseButtonGroup.addWidget(self.doseH2SButton)
        self.doseButtonGroup.addWidget(self.doseH2Button)
        self.purgeGroup.addLayout(self.doseButtonGroup)

        self.doseH2SInput = qw.QLineEdit()
        self.doseH2SInput.setText('10')
        self.doseH2SInput.setValidator(QtGui.QIntValidator())
        self.doseH2SLabel = qw.QLabel('H2S Dose Volume:')

        self.doseH2Input = qw.QLineEdit()
        self.doseH2Input.setText('10')
        self.doseH2Input.setValidator(QtGui.QIntValidator())
        self.doseH2Label = qw.QLabel('H2 Dose Volume:')

        self.doseLabelGroup = qw.QHBoxLayout()
        self.doseLabelGroup.addWidget(self.doseH2Label)
        self.doseLabelGroup.addWidget(self.doseH2SLabel)

        self.doseInputGroup = qw.QHBoxLayout()
        self.doseInputGroup.addWidget(self.doseH2Input)
        self.doseInputGroup.addWidget(self.doseH2SInput)

        self.purgeGroup.addLayout(self.doseLabelGroup)
        self.purgeGroup.addLayout(self.doseInputGroup)

        self.doseH2SButton.clicked.connect(self.plotDosing)
        

        ## Add widgets to layout grid w/ row, col, rowspan, colspan
        layout.addLayout(self.purgeGroup,0,0,2,1)
        layout.addWidget(self.currentProcessPlot,2,0,2,2)

        layout.addWidget(self.temp_plot,0,2,1,1)
        layout.addWidget(self.highVac_plot,1,2,1,1)
        layout.addWidget(self.rxnTemp_plot,2,2,1,1)
        layout.addWidget(self.rxnVac_plot,3,2,1,1)

        self.tree = BrooksParamTree()
        self.mfcButton = qw.QPushButton("Re-initialize MFCs")
        self.treeGroup = qw.QVBoxLayout()
        self.treeGroup.addWidget(self.mfcButton)
        self.treeGroup.addWidget(self.tree)
        
        layout.addLayout(self.treeGroup,0,1,1,1)
        
        layout.setContentsMargins(25,11,12,30)

        if pyvisaConnection == None:
            print('Skipping MFC initialize')
        else:
            self.brooks0254 = Brooks0254(pyvisaConnection, deviceAddress='29751')
            self.mfcButton.clicked.connect(self.setupMFCs)

        self.show()

        ########## making plots zoomable #############
        ## first add fake data
        i=0
        for plt in [self.highVac_plot,self.rxnVac_plot,self.temp_plot,self.rxnTemp_plot,]:
            plt.setMouseEnabled(y=None)
            if i < 2:
                plt.plot(y=np.random.normal(size=100),pen=self.pressurePen)
            else:
                plt.plot(y=np.random.normal(size=100),pen=self.tempPen)
            i+=1

    def abort_process(self):
        ## in practice would set flows to zero
        self.timer.stop()

    def setupMFCs(self):
        gf1 = self.tree.getParamValue('MFC 1 Setup Parameters','Gas Factor')
        gf2 = self.tree.getParamValue('MFC 2 Setup Parameters','Gas Factor')
        gf3 = self.tree.getParamValue('MFC 3 Setup Parameters','Gas Factor')
        self.brooks0254.setupMFCs([gf1,gf2,gf3])

    def run_purge_process(self):
        self.currentProcessPlot.clear()
        if self.cp2 is not None:
            self.cp2.clear()
        
        self.currentProcessPlot.setLabel('left',"Pressure",units = 'Torr',color='#00ff41',**{'font-size': '14pt'})
        
        ### for second trace #######
        self.cp2 = pg.ViewBox()
        self.currentProcessPlot.showAxis('right')
        self.currentProcessPlot.scene().addItem(self.cp2)
        self.currentProcessPlot.getAxis('right').linkToView(self.cp2)
        self.cp2.setXLink(self.currentProcessPlot)
        self.currentProcessPlot.setLabel('right',"Ar Flow",units='sccm',color='#F5D300',**{'font-size':'14pt'})

        self.updateViews()
        self.currentProcessPlot.getViewBox().sigResized.connect(self.updateViews)
        #################

        self.tube_pressure_trace = self.currentProcessPlot.plot(pen=self.pressurePen)
        self.sccm_Ar_trace = pg.PlotCurveItem(pen=self.flowPen)
        self.cp2.addItem(self.sccm_Ar_trace)


        self.tube_pressure_data = [0]
        self.sccm_Ar_data=[0]
        self.time_data = [0]
        self.t0 = time()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot_purging)
        self.timer.start(1000)

    def updateViews(self):
            self.cp2.setGeometry(self.currentProcessPlot.getViewBox().sceneBoundingRect())
            self.cp2.linkedViewChanged(self.currentProcessPlot.getViewBox(), self.cp2.XAxis)

    def update_plot_purging(self):
        self.stopPressure = int(self.purgePressureInput.text())
        tcurr = time() - self.t0
        actual_tube_pressure = self.tube_pressure_data[-1]
        if actual_tube_pressure >= self.stopPressure:
            Ar_flow = 0
            self.timer.stop()
        elif tcurr <= 5:
            Ar_flow = 10
        elif tcurr > 5:
            Ar_flow = 100
        
        self.tube_pressure_data.append(actual_tube_pressure+Ar_flow)
        self.sccm_Ar_data.append(Ar_flow)
        self.time_data.append(tcurr)
        
        self.tube_pressure_trace.setData(self.time_data, self.tube_pressure_data)
        self.sccm_Ar_trace.setData(self.time_data,self.sccm_Ar_data)

    def plotDosing(self):
        # m_h2s = 34.076 #amu
        m_h2s = 5.657e-26 # kg
        Ah2s = 4.43681	
        Bh2s = 829.439	
        Ch2s = -25.412

        def Antoine(A,B,C,T):
            log10P = A - (B / (T + C))
            return 10**log10P

        self.currentProcessPlot.clear()
        if self.cp2 is not None:
            self.cp2.clear()
        
        self.currentProcessPlot.setLabel('left',"Pressure",units = 'Torr',color='#3f51b5',**{'font-size': '14pt'})
        self.currentProcessPlot.setLabel('bottom',"Temperature",units='K',color='#3f51b5',**{'font-size': '14pt'})
        Trange = np.linspace(180,212)
        self.calcVaporPressure = Antoine(Ah2s,Bh2s,Ch2s,Trange)
        self.calcVaporPressureTrace = self.currentProcessPlot.plot(Trange,self.calcVaporPressure,pen='#3f51b5')
        self.actualPressureTrace = pg.ScatterPlotItem(pen='#52be80',symbol='o')
        self.currentProcessPlot.addItem(self.actualPressureTrace)
        
        self.tcurr = 0
        self.actualTemp = 180
        self.actualVaporPressure = 0.1
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot_dosing)
        self.timer.start(1000)

    def update_plot_dosing(self):
        while self.tcurr <=10:
            self.actualVaporPressure = self.actualVaporPressure*1.2
            self.actualTemp += 1
            self.actualPressureTrace.setData(x=[self.actualTemp],y=[self.actualVaporPressure])
            tcurr += 1
        self.timer.stop()


    # def launch_tube_fill_window(self):
        # '''Not using for now'''
        # self.new_window = TubeFillWindow()
        # self.new_window.show()

hometest = True

if __name__ == "__main__":
    app = qw.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    if hometest == False:
        rm = pyvisa.ResourceManager()
        brooks = rm.open_resource('ASRL4::INSTR',read_termination='\r',write_termination='\r')
        window = MainControlWindow(brooks)
    else:
        window = MainControlWindow(pyvisaConnection=None)

    sys.exit(app.exec())
