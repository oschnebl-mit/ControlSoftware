import pyvisa
import numpy as np
import time
from datetime import datetime
from threading import Lock
''' Defining Global Dictionary out here:'''
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

class Brooks0254:

    def __init__(self, testing, pyvisaConnection, deviceAddress=None):
        '''
        pyvisaConnection = pyvisa.ResourceManager().open_resource()
        MFCs: list of str naming the gases being controlled
        deviceAddress: str of len 5
        
        '''
        self.testing = testing
        if self.testing:
            self.__connection = None
        else:
            self.__connection = pyvisaConnection
        self.__address = deviceAddress
        

        self.MFC1 = MassFlowController(testing=self.testing,channel=1,pyvisaConnection=pyvisaConnection,deviceAddress=self.__address)
        self.MFC2 = MassFlowController(testing=self.testing,channel=2,pyvisaConnection=pyvisaConnection,deviceAddress=self.__address)
        self.MFC3 = MassFlowController(testing=self.testing,channel=3,pyvisaConnection=pyvisaConnection,deviceAddress=self.__address)

        self.MFC_list = []

        # self.MFC1 = MassFlowController(channel=1,pyvisaConnection=pyvisaConnection,deviceAddress=self.__address)
        # self.MFC1.setup_MFC()

        # for n in range(1,4):
        #     try:
        #         newMFC = MassFlowController(channel = n,pyvisaConnection=pyvisaConnection,deviceAddress=self.__address)
        #         self.MFC_list.append(newMFC)
        #     except pyvisa.errors.VisaIOError as vioe:
        #         print(f"Error while creating controller {n}: {vioe}")

        # for n, MFC in enumerate(self.MFC_list,start=1):
        #     MFC.setup_MFC()
    

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

    MEASUREMENT_UNITS = dict({
        "ml": 0,
        "mls": 1,
        "mln": 2,
        "l": 3,
        "ls": 4,
        "ln": 5,
        "cm^3": 6,
        "cm^3s": 7,
        "cm^3n": 8,
        "m^3": 9,
        "m^3s": 10,
        "m^3n": 11,
        "g": 12,
        "lb": 13,
        "kg": 14,
        "ft^3": 15,
        "ft^3s": 16,
        "ft^3n": 17,
        "scc": 18,
        "sl": 19,
        "bar": 20,
        "mbar": 21,
        "psi": 22,
        "kPa": 23,
        "Torr": 24,
        "atm": 25,
        "Volt": 26,
        "mA": 27,
        "oC": 28,
        "oK": 29,
        "oR": 30,
        "oF": 31,
        "g/cc": 32,
        "sg": 33,
        "%": 34,
        "lb/in^3": 35,
        "lb/ft^3": 36,
        "lb/gal": 37,
        "kg/m^3": 38,
        "g/ml": 39,
        "kg/l": 40,
        "g/l": 41
    })

    # Base time units
    RATE_TIME_BASE = dict({
        "sec": 1,
        "min": 2,
        "hrs": 3,
        "day": 4
    })

    SP_FUNCTION = {
        'rate': 1,
        'batch': 2,
        'blend': 3
    }

    def __init__(self,testing, channel,pyvisaConnection,deviceAddress=''):
        '''
        Channel refers to each MFC (different gases)
        input for channel 1 = 1, output for channel 1 = 2
        input for channel 2 = 3, output for channel 2 = 4
        channels 3 and 4 follow the same pattern (odds in, evens out)
        channel 9 is global
        '''
        self.testing = testing
        # Addressing parameters
        self.channel = channel
        self.__inputPort = 2 * channel - 1
        self.__outputPort = 2 * channel
        self.__address: str = deviceAddress  # this is a string because it needs to be zero-padded to be 5 chars long

        # PyVisa connection
        if self.testing:
            self.__connection = None
        else:
            self.__connection: pyvisa = pyvisaConnection
        self.com_lock = Lock()


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
        self.program_input_value('Gas_Factor',f'{gas_factor:0<5}') ## format gas factor so it always has 4 sig figs

        self.logger.info('Successfully programmed MFC input values, received following response', response)


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
            command = f'AZ{self.__address}.0{self.__outputPort}P{pcode}={value}'
            if self.testing:
                print(command)
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
            command = f'AZ{self.__address}.0{self.__inputPort}P{pcode}={value}'
            if self.testing:
                print(command)
            try:
                response = self.__connection.query(command).split(sep=',')
                return response
            except:
                print('Failed to connect, no response')

    def read_programmed_value(self,param):
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
        
    def read_measured_values(self):
        ''' Should get all input port values'''
        command = f'AZ{self.__address}.{self.__inputPort}K'
        response = self.__connection.query(command).split(sep=',')
        return response
    
    def read_port_values(self,input=True):
        ''' FROM MANUAL: This command enables terminal operator or host to acquire the present 
        state of a channel output [or input] port programmed values.'''
        if input:
            command = f'AZ{self.__address}.{self.__inputPort}V'
        else:
            command = f'AZ{self.__address}.{self.__outputPort}V'
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

    def practice_batch(self,batch_volume,batch_rate):
        ## want to test code
        ### differs from start batch in that this function waits for "DONE" signal
        ### competing thread would just ask for a measurement, so it would be fine to interleave
        ## program SP function to batch, SP Rate to desired rate, SP Batch to desired quantity, then start batch
        resp = self.program_output_value('SP_Function','2')
        # print(resp)
        self.program_output_value('SP_Batch',batch_volume)
        self.program_output_value('SP_Rate',batch_rate)
        command = f'AZ{self.__address}.{self.__inputPort}P00=007'
        print(self.__connection.query(command))
        # command = f'AZ{self.__address}.{self.__outputPort} F*' #start batch
        # with self.com_lock:
        #     self.__connection.write(command)
        #     response = self.__connection.read()
        #     print(response)
            # while 'OK' in response:
            #     command = f'AZ{self.__address}.{self.__inputPort} V' #check batch status
            #     # self.__connection.write(command)
            #     response = self.__connection.query(command)
            #     print(response)
                
        # return response

# t1 = TestController(1,deviceAddress=33533)
# t2 = TestController(2)

# print(t1.read_value(0x04))
# print(t2.read_value(0x04))

if __name__ == "__main__":
    rm = pyvisa.ResourceManager()
    brooks = rm.open_resource('ASRL8::INSTR',read_termination='\r',write_termination='\r')
    brooks4channel = Brooks0254(False, brooks, deviceAddress='29751')

    # brooks4channel.MFC_list[1].practice_batch(1.0,0.1)
    print(brooks4channel.MFC2.program_output_value('SP_Rate',4.0))
    print(brooks4channel.MFC2.read_programmed_value('SP_Rate'))
    time.sleep(10)
    response = brooks4channel.MFC2.get_measured_values()
    print(response)
    time.sleep(10)
    print(brooks4channel.MFC2.program_output_value('SP_Rate',0.0))
    print(brooks4channel.MFC2.read_programmed_value('SP_Rate'))
    time.sleep(10)
    response = brooks4channel.MFC2.get_measured_values()
    print(response)
    
