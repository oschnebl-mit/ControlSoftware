import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree

paramChange = pg.QtCore.pyqtSignal(object,object)

class BrooksParamTree(ParameterTree):
    def __init__(self):
        super().__init__()
        self.params = [
            {'name':'MFC Setup Parameters', 'type':'group','children':[
                {'name':'MFC 1 Setup Parameters', 'type':'group','children':[
                {'name':'Gas Factor','type':'float','value':1.0},
                {'name':'Rate Units','type':'int','value':18},
                {'name':'Time Base','type':'int','value':2},
                {'name':'Decimal Point','type':'int','value':1},
                {'name':'SP Function','type':'int','value':1}
                ]},
                {'name':'MFC 2 Setup Parameters', 'type':'group','children':[
                {'name':'Gas Factor','type':'float','value':1.3},
                {'name':'Rate Units','type':'int','value':18},
                {'name':'Time Base','type':'int','value':2},
                {'name':'Decimal Point','type':'int','value':1},
                {'name':'SP Function','type':'int','value':1}
                ]},
                {'name':'MFC 3 Setup Parameters', 'type':'group','children':[
                {'name':'Gas Factor','type':'float','value':1.1},
                {'name':'Rate Units','type':'int','value':18},
                {'name':'Time Base','type':'int','value':2},
                {'name':'Decimal Point','type':'int','value':1},
                {'name':'SP Function','type':'int','value':1}
                ]}


                    ]}
                ]
        self.p = Parameter.create(name='self.params',type='group',children=self.params)
        self.setParameters(self.p,showTop=False)

        self.p.sigTreeStateChanged.connect(self.emitChange)
    
    def emitChange(self,param,changes):
        self.paramChange.emit(param,changes)
