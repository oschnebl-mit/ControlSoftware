import sys,qdarkstyle
from time import time
from PyQt5 import QtGui,QtCore
import PyQt5.QtWidgets as qw 
import pyqtgraph as pg

from TubeFurnaceFillGui import TubeFillWindow

class MainControlWindow(qw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Control Panel')

        self.resize(1280, 720)  # Non- maximized size
        self.showMaximized()
        
        ## Create an empty box to hold all the following widgets
        self.mainbox = qw.QWidget()
        self.setCentralWidget(self.mainbox)  # Put it in the center of the main window
        layout = qw.QGridLayout()  # All the widgets will be in a grid in the main box
        self.mainbox.setLayout(layout)  # set the layout

        self.temp_plot = pg.PlotWidget()
        self.highVac_plot = pg.PlotWidget()
        self.rxnVac_plot = pg.PlotWidget()

        self.temp_plot.setLabel('right',"Temperature",units="K")
        self.highVac_plot.setLabel('right',"High Vac Pressure",units = "Torr")
        self.rxnVac_plot.setLabel('right',"Process Pressure",units = "Torr")

        self.highVac_plot.setXLink(self.temp_plot)
        self.rxnVac_plot.setXLink(self.temp_plot)

        self.currentProcessPlot = pg.PlotWidget()
        self.cp2 = None

        self.purgeButton = qw.QPushButton("Fill with Ar")
        self.stopButton = qw.QPushButton("Stop")
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

        ## Add widgets to layout grid w/ row, col, rowspan, colspan
        layout.addLayout(self.purgeGroup,0,0,1,1)
        layout.addWidget(self.currentProcessPlot,1,0,2,1)

        layout.addWidget(self.temp_plot,0,2,1,1)
        layout.addWidget(self.highVac_plot,1,2,1,1)
        layout.addWidget(self.rxnVac_plot,2,2,1,1)

        self.show()

    def abort_process(self):
        ## in practice would set flows to zero
        self.timer.stop()

    def run_purge_process(self):
        self.currentProcessPlot.clear()
        if self.cp2 is not None:
            self.cp2.clear()
        
        self.currentProcessPlot.setLabel('left',"Pressure",units = 'Torr')
        
        ### for second trace #######
        self.cp2 = pg.ViewBox()
        self.currentProcessPlot.showAxis('right')
        self.currentProcessPlot.scene().addItem(self.cp2)
        self.currentProcessPlot.getAxis('right').linkToView(self.cp2)
        self.cp2.setXLink(self.currentProcessPlot)
        self.currentProcessPlot.setLabel('right',"Ar Flow",units='sccm')

        self.updateViews()
        self.currentProcessPlot.getViewBox().sigResized.connect(self.updateViews)
        #################

        self.tube_pressure_trace = self.currentProcessPlot.plot(pen='y')
        self.sccm_Ar_trace = pg.PlotCurveItem(pen='r')
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


    def launch_tube_fill_window(self):
        self.new_window = TubeFillWindow()
        self.new_window.show()

if __name__ == "__main__":
    app = qw.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    window = MainControlWindow()
    sys.exit(app.exec())
