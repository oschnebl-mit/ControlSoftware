import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree


paramChange = pg.QtCore.pyqtSignal(object,object)

class CtrlParamTree(ParameterTree):
    def __init__(self):
        super().__init__()
        self.params = [
            {'name':'MFC Setup Parameters', 'type':'group','children':[
                {'name':'MFC 1 Setup Parameters', 'type':'group','children':[
                {'name':'Gas Factor','type':'float','value':1.39},
                {'name':'Rate Units','type':'int','value':18},
                {'name':'Time Base','type':'list','limits':['sec','min','hrs','day']},
                {'name':'Decimal Point','type':'int','value':1},
                {'name':'SP Function','type':'list','limits':['RATE','BATCH']}
                ]},
                {'name':'MFC 2 Setup Parameters', 'type':'group','children':[
                {'name':'Gas Factor','type':'float','value':1.0},
                {'name':'Rate Units','type':'int','value':18},
                {'name':'Time Base','type':'list','limits':['sec','min','hrs','day']},
                {'name':'Decimal Point','type':'int','value':1},
                {'name':'SP Function','type':'list','limits':['RATE','BATCH']}
                ]},
                {'name':'MFC 3 Setup Parameters', 'type':'group','children':[
                {'name':'Gas Factor','type':'float','value':0.84},
                {'name':'Rate Units','type':'int','value':18},
                {'name':'Time Base','type':'list','limits':['sec','min','hrs','day']},
                {'name':'Decimal Point','type':'int','value':1},
                {'name':'SP Function','type':'list','limits':['RATE','BATCH']}
                ]},
                {'name':'Visa Resource','type':'str','value':'ASRL4::INSTR'},
                {'name':'Device Address','type':'str','value':'29751'}

                    ]},
                {'name':'MKS 902B Setup Parameters','type':'group','children':[
                    {'name':'Pressure unit','type':'list','limits':['TORR','MBAR'],'value':'TORR'},
                    {'name':'Address','type':'str','value':'254'},
                    {'name':'Baud Rate','type':'list','limits':['4800','9600','19200','38400','57600','115200','230400'],'value':'9600'}
                ]},
                {'name':'MKS 925 Setup Parameters','type':'group','children':[
                    {'name':'Pressure unit','type':'str','limits':['TORR','MBAR'],'value':'TORR'},
                    {'name':'Address','type':'str','value':'254'},
                    {'name':'Baud Rate','type':'list','limits':['4800','9600','19200','38400','57600','115200','230400'],'value':'9600'}
                ]}
                #  {'name':'Lakeshore 335 Setup Parameters','type':'group','children':[
                #    ## don't want to give unneeded options, maybe control mode?
                # ]}
                ]
        self.p = Parameter.create(name='self.params',type='group',children=self.params)
        self.setParameters(self.p,showTop=False)
        
        self.p.sigTreeStateChanged.connect(self.emitChange)

    def emitChange(self,param,changes):
        self.paramChange.emit(param,changes)

    def getMFCParamValue(self,mfc_no,child):
        # print(self.p.param('MFC Setup Parameters','MFC 3 Setup Parameters','Gas Factor').value())
        ## mfc_no is an integer 1-3
        branch = f'MFC {mfc_no} Setup Parameters'
        return self.p.param('MFC Setup Parameters',branch,child).value()
    
    def get0254ParamValue(self,branch,child):
        return self.p.param(branch,child).value()

    def getPressureParamValue(self,branch,child):
        return self.p.param(branch,child).value()

class ProcessTree(ParameterTree):

    def __init__(self):
        super().__init__()
        self.params = [
            {'name':'Purge Parameters','type':'group','children':[
                {'name':'Batch Volume','type':'float','value':1},
                {'name':'Batch Rate','type':'float','value':1},
                {'name':'Low Pressure','type':'float','value':1},
                {'name':'High Pressure','type':'float','value':1},
                {'name':'No. Cycles','type':'int','value':3},
                {'name':'Timeout (min)','type':'int','value':1},
                {'name':'Logging Interval (s)','type':'int','value':1}
         ]},
            {'name':'Dose H2S','type':'group','children':[
                {'name':'Batch Volume','type':'float','value':1},
                {'name':'Batch Rate','type':'float','value':1},
                {'name':'Cut-off Pressure','type':'float','value':1}
        ]},
            {'name':'Dose H2','type':'group','children':[
                {'name':'Batch Volume','type':'float','value':1},
                {'name':'Batch Rate','type':'float','value':1},
                {'name':'Cut-off Pressure','type':'float','value':1}
        ]},
            {'name':'Cryo Setpoint','type':'group','children':[
                {'name':'Control Loop','type':'int','value':1},
                {'name':'Ramp Enable','type':'bool','value':True},
                {'name':'Ramp Rate (K/min)','type':'float','value':2},
                {'name':'Setpoint (K)','type':'float','value':300}
            ]}
        ]
        self.p = Parameter.create(name='self.params',type='group',children=self.params)
        self.setParameters(self.p,showTop=False)
    '''
      
        def set_setpoint_ramp_parameter(self, output, ramp_enable, rate_value):
        """Sets the control loop of a particular output.

            Args:
                output (int):
                    Specifies which output's control loop to configure.
                ramp_enable (bool):
                    Specifies whether ramping is off or on (False = Off or True = On).
                rate_value (float):
                    Specifies set-point ramp rate in kelvin per minute.
                    The rate is always positive but will respond to ramps up or down.
                    A rate of 0 is interpreted as infinite, and will respond as if set-point ramping were off.
                    (0.1 to 100)

        """
        self.command(f"RAMP {output},{int(ramp_enable)},{rate_value}")
     '''
    def getPurgeValue(self,child):
        return self.p.param('Purge Parameters',child).value()

    def getH2SDoseValue(self,child):
        return self.p.param('Dose H2S',child).value()

    def getH2DoseValue(self,child):
        return self.p.param('Dose H2',child).value()
    
    def getCryoValue(self,child):
        return self.p.param('Cryo Setpoint',child).value()
