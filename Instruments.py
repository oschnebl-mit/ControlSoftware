import re,pyvisa
import nidaqmx
from lakeshore import Model335
import numpy as np

class DAQ():
    '''Class for communicating with ni daq that controls relays'''
    def __init__(self, logger):
        system = nidaqmx.system.System.local()
        DAQ_device = system.device['Dev1']
        self.logger = logger
        
        ## use nidaqmx Task() to create digital output channels (on/off relays)
        self.relay1 = nidaqmx.Task()
        self.relay1.do_channels.add_do_chan("Dev1/port0/line0")
        self.relay2 = nidaqmx.Task()
        self.relay2.do_channels.add_do_chan("Dev1/port0/line1")
        logger.info('Initialized relays at "Dev1/port0/line0" and "Dev1/port0/line1"')

    def open_relay1(self):
        logger.info('Write True at relay 1 to open')
        self.relay1.write(True)
    
    def close_relay1(self):
        logger.info('Write False at relay 1 to close')
        self.relay1.write(False)

    def open_relay2(self):
        logger.info('Write True at relay 2 to open')
        self.relay2.write(True)
    
    def close_relay2(self):
        logger.info('Write False at relay 2 to close')
        self.relay2.write(False)

''' Lakeshore docs on this specific model's python driver: https://lake-shore-python-driver.readthedocs.io/en/latest/model_335.html
The sensors we have: 1x Curve Matched Silicon Diode sensor @ cooler tip (LS-DT-670B-SD)
                    1x Calibrated Silicon Diode sensor for sample (DT-670-SD-1.4L)
'''

class TemperatureControl():
    '''
    Object that handles information passed to the cryo and gets measured values
    Might not need this
    '''

    def __init__(self,baud_rate,setpoint,ramp_rate,ramp_bool = True, loop = 1, delay = 10):
        self.temperatureController = Model335(baud_rate)
        self.setpoint = setpoint
        self.ramp_rate = ramp_rate
        self.ramp_bool = ramp_bool
        self.loop = loop 

  
    def changeSetpoint(self):
        # set_control_setpoint function takes int for which heater and float for value
        # need to have units setup
        self.temperatureController.set_control_setpoint(self.loop,self.setpoint)

    def changeRamp(self):
        '''built in ramp function takes output loop as int, ramp_enable as bool, rate_value as float
        This wrapper is just meant to pass values from the control panel
        '''
        self.temperatureController.set_setpoint_ramp_parameter(self.loop,self.ramp_bool,self.ramp_rate)


class PressureGauge:
    '''
    Object that holds the serial communication for a pressure gauge
    '''

    def __init__(self,instrument,deviceAddress=None,delay=10):
        '''instrument is string (e.g. 'ASRL3::INSTR') and device Address is string of 5 ints
        '''
        self.__connection: pyvisa = pyvisa.ResourceManager().open_resource(instrument) # read/write terminations?
        self.__address: str = deviceAddress

        if self.__address == None:
            newaddress = self.__ask_address()
            self.__address = newaddress[7:9]

    def __ask_address(self):
        command = f'@254AD?;FF'
        response = self.__connection.query(command)
        return response

    def get_pressure(self):
        '''NOTE: PR1 - PR4 exist, but seems like PR1-PR3 are the same, PR4 is scientific notation'''
        command = f'@{self.__address}PR1?;FF'
        response = self.__connection.query(command)
        if re.search('\\d*ACK',response) is not None:
            return float(response.split('ACK')[0:3])
        else:
            print(f'Failed to receive pressure reading... Received {response}')
            return -1
    
    def set_gauge_params(self,unit='TORR',address='254',baud_rate='9600'):
        ''' From manuals, seems to be the same for both models. I have assumed these are the only settings of interest
        Note the ! sets, while ? is for queries'''
        response = self.__connection.query( f'@{self.__address}U!{unit};FF')
        if re.search('\\d*ACK',response) is None:
            print(f'Failed to set pressure unit... Received {response}')
        response = self.__connection.query( f'@{self.__address}AD!{address};FF')
        if re.search(f'\\d*ACK',response) is None:
            print(f'Failed to set address... Received {response}')
        else:
            self.__address = address ## assumes it succeded
        response = self.__connection.query( f'@{self.__address}BR!{baud_rate};FF')
        if re.search("\\d*ACK",response) is None:
            print(f'Failed to set baud rate... Received {response}')


class Brooks0254:
    '''Object that holds the pyvisa connection to Brooks0254 MFC controller and handles communication with it'''

    def __init__(self, pyvisaConnection, deviceAddress=None):
        '''
        pyvisaConnection = pyvisa.ResourceManager().open_resource()
        MFCs: list of str naming the gases being controlled
        deviceAddress: str of len 5
        
        '''
        self.__connection = pyvisaConnection
        self.__address = deviceAddress

        self.MFC1 = MassFlowController(channel=1,pyvisaConnection=pyvisaConnection,deviceAddress=self.__address)
        self.MFC2 = MassFlowController(channel=2,pyvisaConnection=pyvisaConnection,deviceAddress=self.__address)
        self.MFC3 = MassFlowController(channel=3,pyvisaConnection=pyvisaConnection,deviceAddress=self.__address)

        self.MFC_list = [self.MFC1,self.MFC2, self.MFC3]

        for n, MFC in enumerate(self.MFC_list,start=1):
            MFC.setup_MFC()
    
    def setupMFCs(self,gf):
        '''Currently just sets the gas factor to a value from the parameter tree'''
        for n, MFC in enumerate(self.MFC_list,start=1):
            MFC.setup_MFC(gas_factor=gf[n-1],rate_units=18,time_base=2,decimal_point=1, SP_func = 1)

    def readValue(self):
        return 0
    
    def closeAll(self):
        ''' Emergency button to close all'''
        for MFC in self.MFC_list:
            response = MFC.valve_override(1)
            print(response)

    def resetVOR(self):
        '''Undo the closeAll function'''
        for MFC in self.MFC_list:
            response = MFC.valve_override(0)
            print(response)
    
    '''
    Things to set up for each MFC
    - gas factor
    - decimal point, units
    - mode (rate, batch, or blend)
    - time base (sec, min, hrs, days, or None)
    - audio beep off
    
    Things I think can be set manually:
    - valve override (keep normal)
    - PV signal type
    '''

    

class MassFlowController:
    TYPE_RESPONSE = '4'
    TYPE_BATCH_CONTROL_STATUS = '5'

    ''' Note the value codes might need to be in hex'''
    Output_Program_Values = {
    'SP_Signal_Type':'00',
    'SP_Full_scale':'09',
    'SP_Function':'02',
    'SP_Rate':'01',
    'SP_Batch':'44',
    'SP_Blend':'45',
    'SP_Source':'46'}

    
    Input_Program_Values = {
        'Measure_Units':'04',
        'Time_Base':'10',
        'Decimal_Point':'03',
        'Gas_Factor':'27',
        'Log_Type':'28',
        'PV_Signal_Type':'00',
        'PV_Full_Scale':'09'
    }

    def __init__(self,channel,pyvisaConnection,deviceAddress=''):
        '''
        Channel refers to each MFC (different gases)
        input for channel 1 = 1, output for channel 1 = 2
        input for channel 2 = 3, output for channel 2 = 4
        channels 3 and 4 follow the same pattern (odds in, evens out)
        channel 9 is global
        '''
        # Addressing parameters
        self.channel = channel
        self.__inputPort = 2 * channel - 1
        self.__outputPort = 2 * channel
        self.__address: str = deviceAddress  # this is a string because it needs to be zero-padded to be 5 chars long

        # PyVisa connection
        self.__connection: pyvisa = pyvisaConnection


    def setup_MFC(self,gas_factor=1,rate_units=18,time_base=2,decimal_point=1, SP_func = 1):
        ''' 
        GAS_FACTOR TODO
        rate_units: scc = 18, cm^3 = 6, cm^3s = 7, cm^3n = 8, sl = 19, ml = 0 (plus others)
        time_base: sec = 1, min = 2, hrs = 3, day = 4 
        decimal point: 0 = xxx. , 1 = xx.x , 2 = x.xx , 3 = .xxx 
        SP Func: rate = 1, batch = 2, blend = 3
        '''
        response = self.program_input_value('Measure_Units',rate_units)
        self.program_input_value('Time_Base',time_base)
        self.program_input_value('Decimal_Point',decimal_point)
        self.program_input_value('Gas_Factor',gas_factor)

        print(response)


    def get_measured_values(self):
        '''
        Use inputputPort for read operations
        Check for polled message type response ('4')
        Returns current process value, totalizer value, and datetime
        '''
        command = f'AZ{self.__address}.{self.__inputPort}K'
        response = self.__connection.query(command).split(sep=',')
        if response[2] == MassFlowController.TYPE_RESPONSE:
            return np.float16(response[5]), np.float32(response[4]), datetime.now()
        else:
            return None

    def clear_accumulated_value(self):
        ''' From manual: "allows any one channel input port accumulated value to be
         independently reset to zero" given the 1 after the Z. 
         I think this should reset the totalizer.
         Response should be None
         '''
        command = f'AZ{self.__address}.{self.__inputPort}Z1'
        response = self.__connection.query(command).split(sep=',')
        return response

    '''
    Below are functions that program output values. The command structure is as follows:
    AZ[yyyyy.xx]P[zz]=<new value><cr>  where [zz] depends on the paramter type
    The response will have the form: AZ,yyyyy.xx,4,Pzz,<new value>,<sum><cr><If>

    program_output_value does this generically
    '''

    def write_SP_rate(self,value):
        '''sends the command to make the setpoint rate equal to value (float)'''
        command = f'AZ{self.__address}.{self.__outputPort}P01={value}'
        response = self.__connection.query(command).split(sep=',')
        return response

    def write_SP_batch(self,value):
        '''sends command to make the batch setpoint equal to value (float)
        Note that it does not start the batch (I think)
         '''
        command = f'AZ{self.__address}.{self.__outputPort}P44={value}'
        response = self.__connection.query(command).split(sep=',')
        return response

    def program_output_value(self,param,value):
        '''
         Sends a program command to change the param (a str) to value (a float)
        '''
        if param not in Output_Program_Values:
            return 'Error: not an output parameter'
        else:
            pcode = Output_Program_Values[param] # this is a string
            command = f'AZ{self.__address}.{self.__outputPort}P{pcode}={value}'
            response = self.__connection.query(command).split(sep=',')
            return response

    def program_input_value(self,param,value):
        '''
         Sends a program command to change the param (a str) to value (a float)
        '''
        if param not in Input_Program_Values:
            return 'Error: not an output parameter'
        else:
            pcode = Input_Program_Values[param] # this is a 2 chr string
            command = f'AZ{self.__address}.{self.__inputPort}P{pcode}={value}'
            response = self.__connection.query(command).split(sep=',')
            return response

    def read_programmed_value(self,param,value):
        '''
         Reads the value of the given param (a str) 
         Value should be response[4]
        '''
        if param not in Output_Program_Values:
            return 'Error: not a parameter'
        else:
            pcode = Output_Program_Values[param] # this is a string
            command = f'AZ{self.__address}.{self.__outputPort}P{pcode}?'
            response = self.__connection.query(command).split(sep=',')
            return response
        
    def start_batch(self,batch_volume,batch_rate):
        ## program SP function to batch, SP Rate to desired rate, SP Batch to desired quantity, then start batch
        self.program_output_value('SP_Function','2')
        self.program_output_value('SP_Batch',batch_volume)
        self.program_output_value('SP_Rate',batch_rate)
        command = f'AZ{self.__address}.{self.__outputPort}F*' # start channel batch
        response = self.__connection.query(command).split(sep=",")
        return response
    
    def valve_override(self,value):
        # 0 = Normal, 1 = Closed, 2 = Open
        response = self.program_output_value('SP_VOR',value)