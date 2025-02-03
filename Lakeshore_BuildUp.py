
import pyvisa.constants
import serial,time,re,pyvisa
# pyvisa.log_to_screen() ## use log to screen when debugging serial comms
rm = pyvisa.ResourceManager()
print(rm.list_resources())

lakeshore = rm.open_resource('ASRL6::INSTR',baud_rate=57600,parity=pyvisa.constants.Parity.odd,data_bits=7)
lakeshore.write('*IDN?')
print(lakeshore.read())
lakeshore.close()

''' 
## Easy Mode:
from lakeshore import Model335

my_instrument = Model335(baud_rate=57600)
print(my_instrument.get_celsius_reading('A'))
'''