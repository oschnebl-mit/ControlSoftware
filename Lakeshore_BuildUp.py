
# import pyvisa.constants
# import serial,time,re,pyvisa
# # pyvisa.log_to_screen() ## use log to screen when debugging serial comms
# rm = pyvisa.ResourceManager()
# print(rm.list_resources())

# lakeshore = rm.open_resource('ASRL6::INSTR',baud_rate=57600,parity=pyvisa.constants.Parity.odd,data_bits=7)
# lakeshore.write('*IDN?')
# print(lakeshore.read())
# lakeshore.close()


## Easy Mode:
from lakeshore import Model335

my_instrument = Model335(baud_rate=57600)
[A,B]=my_instrument.get_all_kelvin_reading()
print(f"Read A = {A} K and B = {B} K")
# print(my_instrument.get_celsius_reading("A"))

### testing 6/13/2025: niether version is working, COM6 isn't showing up in device manager
### testing 6/16/2025: lakeshore's Model335 package worked on my surface, just had to change baud rate in device manager
"""
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
"""