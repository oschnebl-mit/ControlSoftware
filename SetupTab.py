import sys,qdarkstyle
import time as t
from PyQt5 import QtGui,QtCore
import PyQt5.QtWidgets as qw 
import pyqtgraph as pg
import numpy as np
import logging

from Control_Parameters import CtrlParamTree, ProcessTree

class SetupTab(qw.QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

        ## connect buttons
        self.mks902Button.clicked.connect(self.setupMKS902)
        self.mks925Button.clicked.connect(self.setupMKS925)
        self.mfcButton.clicked.connect(self.setupMFCs)

    def initUI(self):
        ## Create an empty box to hold all the following widgets
        self.mainbox = qw.QWidget()
        self.setCentralWidget(self.mainbox)  # Put it in the center of the main window
        layout = qw.QGridLayout()  # All the widgets will be in a grid in the main box
        self.mainbox.setLayout(layout)  # set the layout

        self.ctrlTree = CtrlParamTree()
        self.mfcButton = qw.QPushButton("Re-initialize MFCs")
        self.mks925Button = qw.QPushButton("Re-initialize MKS925 (Pirani)")
        self.mks902Button = qw.QPushButton("Re-initialize MKS902B (Piezo)")

        self.processTree = ProcessTree()


        layout.addWidget(self.mfcButton,       0,0,1,1)
        layout.addWidget(self.mks925Button,    1,0,1,1)
        layout.addWidget(self.mks902Button,    2,1,1,1)
        layout.addWidget(self.ctrlTree,        5,0,12,1)
        layout.addWidget(self.processTree,     0,2,6,1)

    def setupMKS925(self):
        ## function intended to troubleshoot connection to pressure gauge from within gui
        unit = self.ctrlTree.getPressureParamValue('MKS 925 Setup Parameters','Pressure unit')
        addr = self.ctrlTree.getPressureParamValue('MKS 925 Setup Parameters','Address')
        baud = self.ctrlTree.getPressureParamValue('MKS 925 Setup Parameters','Baud Rate')
        self.logger.debug(f'Setting MKS925 gauge to new parameters: {unit},{addr},{baud}')
        self.mks925.set_gauge_params(unit,addr,baud)

    def setupMKS902(self):
        ## function intended to troubleshoot connection to pressure gauge from within gui
        unit = self.ctrlTree.getPressureParamValue('MKS 902B Setup Parameters','Pressure unit')
        addr = self.ctrlTree.getPressureParamValue('MKS 902B Setup Parameters','Address')
        baud = self.ctrlTree.getPressureParamValue('MKS 902B Setup Parameters','Baud Rate')
        self.logger.debug(f'Setting MKS902B gauge to new parameters: {unit},{addr},{baud}')
        self.mks902.set_gauge_params(unit,addr,baud)

    def setupMFCs(self):
        for i in range(3):
            gas_factor = self.ctrlTree.getMFCParamValue(i+1,'Gas Factor')
            rate_units_str = self.ctrlTree.getMFCParamValue(i+1,'Rate Units')
            time_base_str = self.ctrlTree.getMFCParamValue(i+1,'Time Base')
            decimal_point = self.ctrlTree.getMFCParamValue(i+1,'Decimal Point')
            func = self.ctrlTree.getMFCParamValue(i+1,'SP Function')
            if self.testing:
                print(f'Try to program MFC{i+1} with gas factor {gas_factor}, rate units {rate_units_str},time base {time_base_str}, decimal point {decimal_point}, and SP function {func}')
                try:
                    rate_units = self.b0254.MEASUREMENT_UNITS[rate_units_str]
                    time_base = self.b0254.RATE_TIME_BASE[time_base_str]
                    self.b0254.MFC_list[i].setup_MFC(gas_factor,rate_units,time_base,decimal_point,func)
                except:
                    print('Failed to program MFC')
            else:
                rate_units = self.b0254.MEASUREMENT_UNITS[rate_units_str]
                time_base = self.b0254.RATE_TIME_BASE[time_base_str]
                self.b0254.MFC_list[i].setup_MFC(gas_factor,rate_units,time_base,decimal_point,func)