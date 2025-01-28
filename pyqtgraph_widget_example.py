
import numpy as np

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

app = pg.mkQApp()

win = pg.GraphicsLayoutWidget(show=True, title="Bring Tube to Atmospheric Pressure")
win.resize(1000,600)
win.setWindowTitle('Bring Tube to Atmospheric Pressure')

p1 = win.addPlot(title="Pressure/Flow")
p1.setYRange(0,800)
p1.setLabel('left',"Pressure",units = 'Torr')
# p1.setLabel('right', "Ar Flow", units = 'sccm')
## create a new ViewBox, link the right axis to its coordinate system
p2 = pg.ViewBox()
p1.showAxis('right')
p1.scene().addItem(p2)
p1.getAxis('right').linkToView(p2)
p2.setXLink(p1)
p1.getAxis('right').setLabel('Ar Flow', color='r',units='sccm')

def updateViews():
    global p2
    p2.setGeometry(p1.getViewBox().sceneBoundingRect())
    p2.linkedViewChanged(p1.getViewBox(), p2.XAxis)

updateViews()
# p1.getViewBox().sigResized.connect(updateViews)

tube_pressure_trace = p1.plot(pen='y')
sccm_Ar_trace = pg.PlotCurveItem(pen='r')
p2.addItem(sccm_Ar_trace)

tube_pressure_data = [0]
sccm_Ar_data = [0]
time_data = [0]


def update_plot(stop_pressure=700):
    global tube_pressure_trace, sccm_Ar_trace, tcurr, tube_pressure_data, sccm_Ar_data,timer

    tcurr +=1
    actual_tube_pressure = tube_pressure_data[-1] ## in practice this would be a measurement
    if actual_tube_pressure >= stop_pressure:
        Ar_flow = 0 ## in practice this would set the MFC
        timer.stop()
    elif tcurr <= 5:
        Ar_flow = 10
    elif tcurr > 5:
        Ar_flow = 100

    tube_pressure_data.append(actual_tube_pressure+Ar_flow)
    sccm_Ar_data.append(Ar_flow)
    time_data.append(tcurr)
    
    tube_pressure_trace.setData(time_data,tube_pressure_data)
    sccm_Ar_trace.setData(time_data,sccm_Ar_data)


tcurr = 0

timer = QtCore.QTimer()
timer.timeout.connect(update_plot)
timer.start(1000)

pg.exec()