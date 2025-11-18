import re,pyvisa
import nidaqmx
# from lakeshore import Model335
import numpy as np
import time, serial
from threading import Lock

class DAQ():
    '''Class for communicating with ni daq that controls relays'''
    def __init__(self, testing, logger):
        self.logger = logger
        self.testing = testing
        ## use nidaqmx Task() to create digital output channels (on/off relays)
        if self.testing:
            try:
                self.relay0 = nidaqmx.Task()
                self.relay0.do_channels.add_do_chan("Dev1/port0/line0")
                self.relay1 = nidaqmx.Task()
                self.relay1.do_channels.add_do_chan("Dev1/port0/line1")
                self.relay2 = nidaqmx.Task()
                self.relay2.do_channels.add_do_chan("Dev1/port0/line2")
                logger.info('Initialized relays at "Dev1/port0/line1" and "Dev1/port0/line2"')
                self.virtual = False
            except:
                self.virtual = True
                logger.info('Failed to initialize DAQ relays')
        else:
            self.virtual = False
            self.relay0 = nidaqmx.Task()
            self.relay0.do_channels.add_do_chan("Dev1/port0/line0")
            self.relay1 = nidaqmx.Task()
            self.relay1.do_channels.add_do_chan("Dev1/port0/line1")
            self.relay2 = nidaqmx.Task()
            self.relay2.do_channels.add_do_chan("Dev1/port0/line2")
            self.scrollPurge = nidaqmx.Task()
            self.scrollPurge.do_channels.add_do_chan("Dev1/port0/line3")
            logger.info('Initialized relays at "Dev1/port0/line0", "Dev1/port0/line1", "Dev1/port0/line2, and Dev1/port0/line3"')

    def open_valve0(self):
        self.logger.info('Write True at relay 0 to open valve')
        if not self.virtual:
            self.relay0.write(True)
            
    def close_valve0(self):
        self.logger.info('Write False at relay 0 to close')
        if not self.virtual:
            self.relay0.write(False)

    def open_valve1(self):
        self.logger.info('Write True at relay 1 to open')
        if not self.virtual:
            self.relay1.write(True)
        
    
    def close_valve1(self):
        self.logger.info('Write False at relay 1 to close')
        if not self.virtual:
            self.relay1.write(False)


    def open_valve2(self):
        self.logger.info('Write True at relay 2 to open')
        if not self.virtual:
            self.relay2.write(True)        
    
    def close_valve2(self):
        self.logger.info('Write False at relay 2 to close')
        if not self.virtual:
            self.relay2.write(False)

    def test_valve1(self):
        print("Testing valve 1")
        self.open_valve1()
        time.sleep(5)
        self.close_valve1()

    def open_scrollPurge(self):
        self.logger.info('Write True at scrollPurge to open')
        if not self.virtual:
            self.scrollPurge.write(True)        
    
    def close_scrollPurge(self):
        self.logger.info('Write False at scrollPurge to close')
        if not self.virtual:
            self.scrollPurge.write(False)


    def close_connections(self):
        ## closes tasks so resources can be re-allocated
        if not self.virtual:
            self.relay0.close()
            self.relay1.close()
            self.relay2.close()
        if self.testing:
            print("closing nidaqmx tasks")


''' Lakeshore docs on this specific model's python driver: https://lake-shore-python-driver.readthedocs.io/en/latest/model_335.html
The sensors we have: 1x Curve Matched Silicon Diode sensor @ cooler tip (LS-DT-670B-SD)
                    1x Calibrated Silicon Diode sensor for sample (DT-670-SD-1.4L)
'''

class TemperatureControl():
    '''
    Object that handles information passed to the cryo and gets measured values
    Might not need this
    '''

    def __init__(self,logger,baud_rate,setpoint,ramp_rate,ramp_bool = True, loop = 1, delay = 10):
        self.temperatureController = Model335(baud_rate)
        self.setpoint = setpoint
        self.ramp_rate = ramp_rate
        self.ramp_bool = ramp_bool
        self.loop = loop 
        self.logger=logger
  
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

    def __init__(self,testing,logger,com_port,deviceAddress='254'):
        '''com_port (e.g. 'COM3') and device Address is string of 3 ints
        '''
        self.testing = testing
        self.logger = logger
        if not self.testing:
            self._connection = serial.Serial(port=com_port,baudrate=9600,parity=serial.PARITY_NONE,bytesize=8,stopbits=serial.STOPBITS_ONE,timeout=1)
            self._address: str = deviceAddress
            self.logger = logger
            self.com_lock = Lock()
            self.virtual = False
        elif self.testing:
            try:
                self._connection = serial.Serial(port=com_port,baudrate=9600,parity=serial.PARITY_NONE,bytesize=8,stopbits=serial.STOPBITS_ONE,timeout=1)
                self._address: str = deviceAddress
                self.logger = logger
                self.com_lock = Lock()
                self.virtual = False
            except:
                self.virtual = True


    def _ask_address(self):
        ''' function to get address of specific pressure gauge. 254 addresses all devices on port.
        Should return '@[ADR]AD[ADR];FF', most likely '@253AD253;FF'
        '''
        self._connection.write(b'@254AD?;FF')
        response = self._connection.readline()
        return response
    
    def query(self,message):
        ''' Helper function to write and read with com_lock. Takes message as string, may need to decode response'''
        with self.com_lock:
            self._connection.write(message.encode())
            return self._connection.readline()
    
    def test(self,address='254'):
        ''' Function to test for communication with pressure gauge. Can supply address if multiple devices could be accessed by 254.
        LED on pressure gauge should flash for 5 s during sleep, then turn off again.
        '''
        print(f"testing pressure gauge with address {address}")
        with self.com_lock:
            self._connection.write(f'@{address}TST!ON;FF'.encode())
            response = str(self._connection.readline())
            self.logger.debug(response)
            time.sleep(5) # wait 10 s to see flashing
            self._connection.write(f'@{address}TST!OFF;FF'.encode())
            response = str(self._connection.readline())
            self.logger.debug(response)

    def get_all_pressures(self):
        '''
        testing method to try to figure out the difference between PR1,2,3, and 4
        '''
        for i in range(1,5):
            command = f'@{self._address}PR{i}?;FF'
            with self.com_lock:
                self._connection.write(command.encode('utf-8'))
                # response = self._connection.read_bytes(15)
                response = self._connection.readline()
                # print(f'PR{i} = {response}')

    def get_pressure(self):
        '''NOTE: PR1 - PR4 exist, but seems like PR1-PR3 are the same, PR4 is scientific notation'''
        command = f'@{self._address}PR1?;FF'
        response = self.query(command).decode()
        if re.search('\\d*ACK',response) is not None:
            list = re.split('ACK|;',response)
            # print(list)
            value = list[1]
            # print(value)
            return float(value)
        else:
            self.logger.warning(f'Failed to receive pressure reading... Received {response}')
            return -1
    
    def set_gauge_params(self,unit='TORR',address='254',baud_rate='9600'):
        ''' From manuals, seems to be the same for both models. I have assumed these are the only settings of interest
        Note the ! sets, while ? is for queries'''
        response = self.query( f'@{self._address}U!{unit};FF')
        if re.search('\\d*ACK',response) is None:
            self.logger.warning(f'Failed to set pressure unit... Received {response}')
        response = self.query( f'@{self._address}AD!{address};FF')
        if re.search(f'\\d*ACK',response) is None:
            self.logger.warning(f'Failed to set address... Received {response}')
        else:
            self._address = address ## assumes it succeded
        response = self.query( f'@{self._address}BR!{baud_rate};FF')
        if re.search("\\d*ACK",response) is None:
            self.logger.warning(f'Failed to set baud rate... Received {response}')


class Brooks0254:
    '''Object that holds the pyvisa connection to Brooks0254 MFC controller and handles communication with it'''

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
    
    def __init__(self,testing, logger, instrument, deviceAddress='29751'):
        '''
        pyvisaConnection = pyvisa.ResourceManager().open_resource()
        MFCs: list of str naming the gases being controlled
        deviceAddress: str of len 5

        As if July 2025, MFCs are installed, H2S is top, Ar is middle, H2 is bottom,
        Let's call H2S = MFC1, Ar = MFC2, H2 = MFC3
        
        '''
        self.logger = logger
        self.testing = testing
        if self.testing:
            try:
                self._connection = pyvisa.ResourceManager().open_resource(instrument)
                self._address = deviceAddress
                self.virtual = False
            except:
                self.virtual = True
                self.logger.info('Failed to initialize Brooks 0254')
        else:
            self._connection = pyvisa.ResourceManager().open_resource(instrument)
            self._address = deviceAddress
            self.virtual = False

        self.MFC1 = MassFlowController(self.logger,channel=1,pyvisaConnection=self._connection,deviceAddress=self._address,virtual=self.virtual)
        self.MFC2 = MassFlowController(self.logger,channel=2,pyvisaConnection=self._connection,deviceAddress=self._address,virtual=self.virtual)
        self.MFC3 = MassFlowController(self.logger,channel=3,pyvisaConnection=self._connection,deviceAddress=self._address,virtual=self.virtual)

        self.MFC_list = [self.MFC1,self.MFC2, self.MFC3]



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

    def __init__(self,logger,channel,pyvisaConnection,deviceAddress='',virtual=False):
        '''
        Channel refers to each MFC (different gases)
        input for channel 1 = 1, output for channel 1 = 2
        input for channel 2 = 3, output for channel 2 = 4
        channels 3 and 4 follow the same pattern (odds in, evens out)
        channel 9 is global
        '''
        # Addressing parameters
        self.channel = channel
        self._inputPort = 2 * channel - 1
        self._outputPort = 2 * channel
        self._address: str = deviceAddress  # this is a string because it needs to be zero-padded to be 5 chars long
        self.com_lock = Lock()
        self.virtual = virtual
        self.logger = logger
        # PyVisa connection
        if not self.virtual:
            self._connection: pyvisa = pyvisaConnection


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
        command = f'AZ{self._address}.{self._inputPort}K'
        if self.virtual:
            print(command)
        else:
            with self.com_lock:
                try:
                    response = self._connection.query(command).split(sep=',')
                    if response[2] == MassFlowController.TYPE_RESPONSE:
                        return np.float16(response[5]), np.float32(response[4]), time.time()
                    else:
                        self.logger.warning('Request for measured values returned something unexpected')
                        return None
                except pyvisa.errors.VisaIOError as e:
                    print("Failed to retrieve measured values from MFC controller")
                    self.logger.debug(f'Pyvisa error: {e}')
                    return -1.0,-1.0,time.time()


    def clear_accumulated_value(self):
        ''' From manual: "allows any one channel input port accumulated value to be
         independently reset to zero" given the 1 after the Z. 
         I think this should reset the totalizer.
         Response should be None
         '''
        command = f'AZ{self._address}.{self._inputPort}Z1'
        if self.virtual:
            print(command)
        else:
            with self.com_lock:
                response = self._connection.query(command).split(sep=',')
            return response

    '''
    Below are functions that program output values. The command structure is as follows:
    AZ[yyyyy.xx]P[zz]=<new value><cr>  where [zz] depends on the paramter type
    The response will have the form: AZ,yyyyy.xx,4,Pzz,<new value>,<sum><cr><If>

    program_output_value does this generically
    '''

    def write_SP_rate(self,value):
        '''sends the command to make the setpoint rate equal to value (float)'''
        command = f'AZ{self._address}.{self._outputPort}P01={value}'
        with self.com_lock:
            try:
                response = self._connection.query(command).split(sep=',')
                return response
            except pyvisa.errors.VisaIOError as e:
                print("Failed to write SP rate to MFC controller")
                self.logger.debug(f'Pyvisa error: {e}')
                return None

    def write_SP_batch(self,value):
        '''sends command to make the batch setpoint equal to value (float)
        Note that it does not start the batch (I think)
         '''
        command = f'AZ{self._address}.{self._outputPort}P44={value}'
        with self.com_lock:
            response = self._connection.query(command).split(sep=',')
        return response

    def program_output_value(self,param,value):
        '''
         Sends a program command to change the param (a str) to value (a float)
        '''
        if param not in self.Output_Program_Values:
            self.logger.info('Error: not an output parameter')
        else:
            pcode = self.Output_Program_Values[param] # this is a string
            command = f'AZ{self._address}.{self._outputPort}P{pcode}={value}'
            if self.virtual:
                print(command)
            else:
                try:
                    with self.com_lock:
                        response = self._connection.query(command).split(sep=',')
                    self.logger.info(f'Received response {response}')
                    return response
                except pyvisa.errors.VisaIOError as e:
                    # print('Failed to program output value')
                    self.logger.warning(f'Received VisaIOError {e}')
                    return None

    def program_input_value(self,param,value):
        '''
         Sends a program command to change the param (a str) to value (a float)
        '''
        if param not in self.Input_Program_Values:
            self.logger.info('Error: not an input parameter')
            return None
        else:
            pcode = self.Input_Program_Values[param] # this is a 2 chr string
            command = f'AZ{self._address}.{self._inputPort}P{pcode}={value}'
            self.logger.info(f'Sending command {command} to controller.')
            try:
                with self.com_lock:
                    response = self._connection.query(command).split(sep=',')
                self.logger.info(f'Received response {response}')
                return response
            except pyvisa.errors.VisaIOError as e:
                print('Failed to program input value')
                self.logger.warning(f'Received VisaIOError {e}')
                return None

    def read_programmed_value(self,param,value):
        '''
         Reads the value of the given param (a str) 
         Value should be response[4]
        '''
        if param not in self.Output_Program_Values:
            return 'Error: not a parameter'
        else:
            pcode = self.Output_Program_Values[param] # this is a string
            command = f'AZ{self._address}.{self._outputPort}P{pcode}?'
            with self.com_lock:
                response = self._connection.query(command).split(sep=',')
            return response

    def set_sccm(self,rate):
        self.logger.info(f'Setting MFC to {rate}')
        response = self.program_output_value('SP_Function','1')
        if response == None:
            print(f'Failed to program output value SP Function')
        response = self.program_output_value('SP_Rate',rate)
        if response == None:
            print(f'Failed to program output value SP_Rate to rate {rate}')

        
    def start_batch(self,batch_volume,batch_rate):
        ### should com_lock wrap around all three program requests?
        ### competing thread would just ask for a measurement, so it would be fine to interleave
        ## program SP function to batch, SP Rate to desired rate, SP Batch to desired quantity, then start batch
        self.program_output_value('SP_Function','2')
        self.program_output_value('SP_Batch',batch_volume)
        self.program_output_value('SP_Rate',batch_rate)
        command = f'AZ{self._address}.{self._outputPort}F*' # start channel batch
        with self.com_lock:
            response = self._connection.query(command).split(sep=",")
        return response
    
    def valve_override(self,value):
        # 0 = Normal, 1 = Closed, 2 = Open
        response = self.program_output_value('SP_VOR',value)