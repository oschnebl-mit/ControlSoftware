import sys,qdarkstyle, os
import time as t
from PyQt5 import QtGui,QtCore
import PyQt5.QtWidgets as qw 
import pyqtgraph as pg
import numpy as np

class BoxedPlot(qw.QWidget):
    def __init__(self, plot_title, color):
        super().__init__()
        masterLayout = qw.QVBoxLayout()
        self.pen = pg.mkPen(color, width=2)

        layout = qw.QVBoxLayout()
        self.group = qw.QGroupBox(plot_title)
        self.plot = pg.PlotWidget()
        self.plot.getPlotItem().showGrid(x=True, y=True, alpha=1)
        self.plot.getPlotItem().showAxis('right')
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
        print(f'Add to plot {new_data}')
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
    def __init__(self, plot_title, color, max_points):
        super().__init__()
        masterLayout = qw.QVBoxLayout()
        self.num_points = max_points
        self.pen = pg.mkPen(color, width=1)
        self.brush = pg.mkBrush(color)
        layout = qw.QVBoxLayout()
        self.group = qw.QGroupBox(plot_title)
        self.plot = pg.PlotWidget()
        self.plot.getPlotItem().showAxis('right')
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
        if xdata is None:
            xdata = np.array([t.time()])
            ydata = np.array([new_data])
        else:
            xdata = np.append(xdata,t.time())
            ydata = np.append(ydata,new_data)
        # print(f'Add to plot: ({xdata},{ydata})')
        self.trace.setData(x=xdata, y=ydata)
        if len(xdata)>self.num_points:
            # print(len(xdata))
            self.plot.setXRange(xdata[-self.num_points],xdata[-1])
            # print(xdata[-1])
        # self.plot.getViewBox().autoRange()

