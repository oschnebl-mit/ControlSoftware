import sys,qdarkstyle
from time import time
from PyQt5 import QtGui,QtCore
import PyQt5.QtWidgets as qw 
import pyqtgraph as pg
import numpy as np
import pyvisa # if not demoMode


from Control_Parameters import CtrlParamTree
from Brooks0254_BuildUp import Brooks0254, MassFlowController
from PressureGauge_BuildUp import PressureGauge
# from misc_helpers import add_line_glow


# from TubeFurnaceFillGui import TubeFillWindow


class MainControlWindow(qw.QMainWindow):
    def __init__(self, demoMode = False):
        super().__init__()
        self.setWindowTitle('Control Panel')

        self.resize(1280,720) # non-maximized state
        # self.resize(2560, 1440)  # for home monitor
        if demoMode == False:
            self.showMaximized()


        self.init_UI(demoMode)


        if demoMode == True:
            print('Skipping MFC initialize')
            print('Skipping pressure gauge initialize')
        else:
            self.rm = pyvisa.ResourceManager()
            try:
                self.brooksVisaConnection = self.rm.open_resource('ASRL4::INSTR',read_termination='\r',write_termination='\r')
                self.brooks0254 = Brooks0254(self.brooksVisaConnection, deviceAddress='29751')
            except pyvisa.errors.VisaIOError as error:
                print(f'Failed to initialize Brooks0254 controller... Received:{error}')


            try:
                self.MKS902VisaConnection = self.rm.open_resource('ASRL1::INSTR',read_termination='\r',write_termination='\r')
                self.MKS902B = PressureGauge(self.MKS902VisaConnection)
                self.mks925VisaConnection = self.rm.open_resource('ASRL2::INSTR',read_termination='\r',write_termination='\r')
                self.MKS925 = PressureGauge(self.mks925VisaConnection)
            except pyvisa.VisaIOError as error:
                print(f'Failed to initialize pressure gauges... Received: {error}')
            ## even if setup fails, the button should work if not in demo mode
            self.mfcButton.clicked.connect(self.setupMFCs)
            self.mks925Button.clicked.connect(self.setupGauge('925'))
            self.mks902Button.clicked.connect(self.setupGauge('902'))


        self.show()


    def init_UI(self,demoMode):
        ### # Dedicated colors which look "good"
        # colors = ['#08F7FE', '#FE53BB', '#F5D300', '#00ff41', '#FF0000', '#9467bd', ]
        
        ## Create an empty box to hold all the following widgets
        self.mainbox = qw.QWidget()
        self.setCentralWidget(self.mainbox)  # Put it in the center of the main window
        layout = qw.QGridLayout()  # All the widgets will be in a grid in the main box
        self.mainbox.setLayout(layout)  # set the layout


        self.temp_plot = pg.PlotWidget()
        self.highVac_plot = pg.PlotWidget()
        self.rxnVac_plot = pg.PlotWidget()
        self.rxnTemp_plot = pg.PlotWidget()
        # self.rxnTemp_plot = boxedPlot('Process Temperature','#08F7FE')


        self.pressurePen = pg.mkPen(color='#FE53BB',width=2)
        self.flowPen = pg.mkPen(color='#F5D300',width=2)
        self.tempPen = pg.mkPen(color='#08F7FE',width=2)


        self.temp_plot.setLabel('left',"Temperature",units="K",color='#08F7FE',**{'font-size': '12pt'})
        self.highVac_plot.setLabel('left',"High Vac Pressure",units = "Torr",color='#FE53BB',**{'font-size': '12pt'})
        self.rxnTemp_plot.setLabel('left',"Process Temperature",units="K",color='#08F7FE',**{'font-size': '12pt'})
        self.rxnVac_plot.setLabel('left',"Process Pressure",units = "Torr",color='#FE53BB',**{'font-size': '12pt'})


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


        self.doseH2SButton = qw.QPushButton("Dose with H2S")
        self.doseH2Button = qw.QPushButton("Dose with H2")
    
        self.doseH2SInput = qw.QLineEdit()
        self.doseH2SInput.setText('10')
        self.doseH2SInput.setValidator(QtGui.QIntValidator())
        self.doseH2SLabel = qw.QLabel('H2S Dose Volume:')


        self.doseH2Input = qw.QLineEdit()
        self.doseH2Input.setText('10')
        self.doseH2Input.setValidator(QtGui.QIntValidator())
        self.doseH2Label = qw.QLabel('H2 Dose Volume:')


        self.doseH2SButton.clicked.connect(self.plotDosing)
    
        self.tree = CtrlParamTree()
        self.mfcButton = qw.QPushButton("Re-initialize MFCs")
        self.mks925Button = qw.QPushButton("Re-initialize MKS925 (Pirani)")
        self.mks902Button = qw.QPushButton("Re-initialize MKS 902B (piezo)")


        
        ## Add widgets to layout grid w/ row, col, rowspan, colspan
        ## Top left tree and buttons
        layout.addWidget(self.mfcButton,0,0,1,2)
        layout.addWidget(self.mks925Button,1,0,1,2)
        layout.addWidget(self.mks902Button,2,0,1,2)
        layout.addWidget(self.tree,3,0,10,2)


        ## Top middle buttons and inputs (start at col 3, row 0)
        layout.addWidget(self.purgeButton,0,3,1,1)
        layout.addWidget(self.stopButton,0,4,1,1)


        layout.addWidget(self.ppiLabel,1,3,1,1)
        layout.addWidget(self.purgePressureInput,2,3,1,1)


        layout.addWidget(self.doseH2SButton,3,3,1,1)
        layout.addWidget(self.doseH2SLabel,4,3,1,1)
        layout.addWidget(self.doseH2SInput,5,3,1,1)
        
        layout.addWidget(self.doseH2Button,3,4,1,1)
        layout.addWidget(self.doseH2Label,4,4,1,1)
        layout.addWidget(self.doseH2Input,5,4,1,1)

        layout.addWidget(qw.QLabel('Placeholder'),6,3,1,1)
        layout.addWidget(qw.QLabel('Placeholder'),7,3,1,1)
        layout.addWidget(qw.QLabel('Placeholder'),6,4,1,1)
        layout.addWidget(qw.QLabel('Placeholder'),7,4,1,1)


        ## current process plot middle bottom (start at row 7, col 3)
        layout.addWidget(self.currentProcessPlot,7,3,10,7)


        ## Right Hand column of plots
        layout.addWidget(self.temp_plot,0,10,3,15)
        layout.addWidget(self.highVac_plot,3,10,4,15)
        layout.addWidget(self.rxnTemp_plot,7,10,4,15)
        layout.addWidget(self.rxnVac_plot,11,10,4,15)


        
        # layout.setContentsMargins(25,11,12,30)




        if demoMode == True:
            ## add fake data to tracking plots
            i=0
            for plt in [self.highVac_plot,self.rxnVac_plot,self.temp_plot,self.rxnTemp_plot,]:
                # plt.setMouseEnabled(y=None)
                if i < 2:
                    plt.plot(y=np.random.normal(size=100),pen=self.pressurePen)
                else:
                    plt.plot(y=np.random.normal(size=100),pen=self.tempPen)
                i+=1     


        ## updating data with lineglow creates some issues
        # for plt in [self.highVac_plot,self.rxnVac_plot,self.temp_plot,self.rxnTemp_plot,]:
        #     add_line_glow(plt)  


    def abort_process(self):
        ## in practice would set flows to zero
        self.timer.stop()


    def setup925Gauge(self):
        ''' This function is meant to re-initialize either pressure gauge with the values in the parameter tree'''
        unit = self.tree.getPressureParamValue('MKS 925 Setup Parameters','Pressure Unit')
        addr = self.tree.getPressureParamValue('MKS 925 Setup Parameters','Address')
        br = self.tree.getPressureParamValue('MKS 925 Setup Parameters','Baud Rate')
        self.MKS925.set_gauge_params(unit,addr,br)


    def setup925Gauge(self):
        ''' This function is meant to re-initialize either pressure gauge with the values in the parameter tree'''
        unit = self.tree.getPressureParamValue('MKS 902B Setup Parameters','Pressure Unit')
        addr = self.tree.getPressureParamValue('MKS 902B Setup Parameters','Address')
        br = self.tree.getPressureParamValue('MKS 902B Setup Parameters','Baud Rate')
        self.MKS902B.set_gauge_params(unit,addr,br)


    def setupMFCs(self):
        ''' This function is meant to re-initialize the MFCs and their controller with the parameters in the tree, if needed'''
        ## initialize visa connection (not sure if this will error if the first time worked)
        self.visaInstr = self.tree.get0254ParamValue('MFC Setup Parameters','Visa Resource')
        self.deviceAddress = self.tree.get0254ParamValue('MFC Setup Parameters','Device Address')
        self.pyvisaConnection = self.rm.open_resource(self.visaInstr,read_termination='\r',write_termination='\r')
        self.brooks0254 = Brooks0254(self.pyvisaConnection, deviceAddress=self.deviceAddress)
        ## set MFC parameters (right now just changes the gas factor)
        gf1 = self.tree.getMFCParamValue('MFC 1 Setup Parameters','Gas Factor')
        gf2 = self.tree.getMFCParamValue('MFC 2 Setup Parameters','Gas Factor')
        gf3 = self.tree.getMFCParamValue('MFC 3 Setup Parameters','Gas Factor')
        self.brooks0254.setupMFCs([gf1,gf2,gf3])


    def run_purge_process(self):
        ''' For demo mode: looks like the tube furnace purge plot, displays updating placeholder data, responds to fill pressure and stop button or pressure condition'''
        self.currentProcessPlot.clear()
        if self.cp2 is not None:
            self.cp2.clear()
        
        self.currentProcessPlot.setLabel('left',"Pressure",units = 'Torr',color='#FE53BB',**{'font-size': '14pt'})
        self.currentProcessPlot.setLabel('bottom','Time',units='s',color='#e0e0e0',**{'font-size':'14pt'})
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
        ''' For demo mode: updates with self-generated data, stops on pressure condition'''
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
        tcurr += 1
        
        self.tube_pressure_trace.setData(self.time_data, self.tube_pressure_data)
        self.sccm_Ar_trace.setData(self.time_data,self.sccm_Ar_data)


    def plotDosing(self):
        ''' For demo mode: plots the H2S vapor pressure curve, and a point increasing with time for 10 s. 
        Plan is to replace self-generated point with measured (P,T), but maybe we will want P or sccm over time'''
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
            self.currentProcessPlot.setLabel('right', None)


        
        self.currentProcessPlot.setLabel('left',"Pressure",units = 'Torr',color='#3f51b5',**{'font-size': '14pt'})
        self.currentProcessPlot.setLabel('bottom',"Temperature",units='K',color='#3f51b5',**{'font-size': '14pt'})
        Trange = np.linspace(180,212)
        self.calcVaporPressure = Antoine(Ah2s,Bh2s,Ch2s,Trange)
        self.calcVaporPressureTrace = self.currentProcessPlot.plot(Trange,self.calcVaporPressure,pen=pg.mkPen(color='#3f51b5',width=2))
        self.actualPressureTrace = pg.ScatterPlotItem(pen='#52be80',symbol='o')
        self.currentProcessPlot.addItem(self.actualPressureTrace)
        
        self.t0 = time()
        self.actualTemp = 180
        self.actualVaporPressure = 0.1
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot_dosing)
        self.timer.start(1000)


    def update_plot_dosing(self):
        '''For demo mode'''
        tcurr = time() - self.t0
        if tcurr <=10:
            self.actualVaporPressure = self.actualVaporPressure*1.2
            self.actualTemp += 1
            self.actualPressureTrace.setData(x=[self.actualTemp],y=[self.actualVaporPressure])
            
        else:
            self.timer.stop()




    # def launch_tube_fill_window(self):
        # '''Not using for now'''
        # self.new_window = TubeFillWindow()
        # self.new_window.show()


class boxedPlot(qw.QWidget):
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




if __name__ == "__main__":
    app = qw.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())


    window = MainControlWindow(demoMode = True)


    sys.exit(app.exec())
