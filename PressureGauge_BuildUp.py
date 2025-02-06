import re, pyvisa

''' from MKS 902B manual:
Command syntax for an information query:
@<device address><query>?;FF
Command syntax for a command:
@<device address><command>!<parameter>;FF

e.g. request pressure: @254PR1?;FF

Addressing: 001 to 253 allowed (253 default)
Use 254 to communicate with all transudcers on network 

e.g. I think this would work to find out the address
Query: @254AD?;FF
Query reply: @254ACK253;FF

then to change:
@253AD!001;FF

Other useful tidbits:
@xxxU!MBAR;FF -> @xxxACKMBAR;FF  Set pressure unit setup (torr, mbar, pascal)
@xxxBR!19200;FF ->  @xxxACK19200;FF Set communication Baud rate (4800, 9600, 19200, 38400, 57600, 115200, 230400)
'''

'''
to get pyvisa connection:
print(rm.list_resources()) to see what's found
pyvisa_connetion = pyvisa.ResourceManager.open_resource('ASL...INSTR',read_termination,write_termination)
'''

class PressureGauge:
    '''
    Intended to read MKS 902B and 914 by RS485 communication
    TODO: May want to set the address to something unique
    Will definitely have to if both gauges come set to 253
    '''
    def __init__(self,pyvisaConnection,deviceAddress=None):
        self.__connection: pyvisa = pyvisaConnection
        self.__address: str = deviceAddress

        if self.__address == None:
            newaddress = self.__ask_address()
            self.__address = newaddress[7:9]

    def __ask_address(self):
        command = f'@254AD?;FF'
        response = self.__connection.query(command)
        return response

    def readPressure(self):
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


if __name__ == "__main__":
    import serial,time
    # pyvisa.log_to_screen() ## use log to screen when debugging serial comms
    rm = pyvisa.ResourceManager()
    print(rm.list_resources())
    rsrc = rm.open_resource('ASRL3::INSTR',read_termination = '\n')

    rsrc.write('@254TST!ON;FF')
    print(rsrc.read_bytes(12))
    time.sleep(1)
    # print(rsrc.get_visa_attribute(encoding))
    rsrc.write('@254TST!OFF;FF')
    print(rsrc.read_bytes(12))
    rsrc.close()
   

    # mksgauge = PressureGauge(rsrc)
    # print(mksgauge.__ask_address())
        # from TubeFurnaceController import GenericSerialDevice
    # pgauge = GenericSerialDevice(com_port=3,parity=serial.PARITY_EVEN,testing=False,name='Temperature Controller')
    # response = pgauge.ask('@254TST!ON;FF')
    # print(response)
    # pgauge.close_connection()

    # ser = serial.Serial(
    #     port="COM3", baudrate = 9600,
    #     parity=serial.PARITY_NONE,
    #     bytesize=8,stopbits=serial.STOPBITS_ONE, timeout=1)
    # if ser.isOpen():
    #     print(ser.name + ' is open...')
    #     # for j in range(2):
    #     #     print(ser.readline())
    # ## Write ASCII Commands To TSI 4043 Flow Sensor
    # ser.write(b'@253PR1?;FF') # test mode (flashes LED)  
    
    # for n in range(3):
    #     rsp = ser.readline()
    #     print(rsp)
    #     print(rsp.decode())

    # ser.close()
