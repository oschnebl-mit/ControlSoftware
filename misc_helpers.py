import numpy as np
import pyqtgraph as pg

def add_line_glow(pItem):
    '''Takes a pyqtgraph plot item and adds glow effect to all lines.
    For ScatterPlotItem adds a line in the default gray'''
    alphas = np.linspace(25,5, 10, dtype=int)
    lws = np.linspace(1, 15, 10)
    pDataItems = pItem.listDataItems()
    for pDataItem in pDataItems:
        color = pDataItem.opts['pen'].color().name()
        (x_data, y_data) = pDataItem.getData()
        for alpha, lw in zip(alphas,lws):
            pen = pg.mkPen(color='{}{:02x}'.format(color, alpha),
                        width=lw,
                        connect="finite")

            pItem.addItem(pg.PlotDataItem(x_data, y_data,pen=pen))       
