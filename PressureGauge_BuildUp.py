import re, pyvisa
import serial
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

class GenericSerialDevice:
    def __init__(self, logger, com_port=0, baudrate=9600, timeout=0.1, parity=serial.PARITY_NONE, bytesize=serial.EIGHTBITS,
                 testing=False, name='serial device'):
        self.testing = testing
        self.max_number_of_attempts_per_read = 5
        self.min_ms_between_successive_reads = 50
        # self.com_lock = Lock()
        self.com_port = com_port
        self.serial_baudrate = baudrate
        self.serial_timeout = timeout
        self.serial_parity = parity
        self.serial_bytesize = bytesize
        self.name = name
        self.logger = logger

        self._serial_connection = self._generate_serial_connection()
        if not self.connection_is_open():
            self.open_connection()

    def __del__(self):
        self.close_connection()

    def _generate_serial_connection(self):
        if self.testing:
            return None

        return serial.Serial(
            port=f'COM{self.com_port}',
            baudrate=self.serial_baudrate,
            timeout=self.serial_timeout,
            parity=self.serial_parity,
            bytesize=self.serial_bytesize
        )

    def connection_is_open(self):
        if self.testing:
            return False

        return self._serial_connection.is_open

    def open_connection(self):
        if self.testing:
            return

        self._serial_connection.open()

    def close_connection(self):
        if self.testing:
            return

        self._serial_connection.close()

    def _write(self, message_str: str):
        if not message_str.endswith('\r'):
            message_str = message_str + '\r'

        if self.testing:
            print(f'would write {message_str}')
        else:
            self._serial_connection.write(bytes(message_str, 'ascii'))
            self.logger.debug(f'wrote {message_str} to {self.name}')

    def write(self, message_str: str):
        # with self.com_lock:
        self._write(message_str)

    def _read(self, accept_empty_response=False) -> str:
        if self.testing:
            return ''

        for i in range(self.max_number_of_attempts_per_read):
            time.sleep(self.min_ms_between_successive_reads / 1000)
            response = self._serial_connection.readline()

            try:
                str_response = response.decode()
                self.logger.debug(f'received response: {str_response} from {self.name}')
                if accept_empty_response or (str_response != ""):
                    return str_response  # successful read, so exit for-loop

            except Exception as ex:
                self.logger.warning(f'Read attempt {i + 1}: failed to decode response of "{response}" from {self.name}')
                self.logger.exception(ex)

        self.logger.warning(f'{self.name} failed to perform read after {self.max_number_of_attempts_per_read} tries')
        return ""

    def read(self, accept_empty_response=False) -> str:
        # with self.com_lock:
        return self._read(accept_empty_response)

    def ask(self, message, accept_empty_response=False):
        # with self.com_lock:
        self._write(message)
        return self._read(accept_empty_response)

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


if __name__ == "__main__":
    # from TubeFurnaceController import GenericSerialDevice
    import serial,time, logging
    # pyvisa.log_to_screen()
    # rm = pyvisa.ResourceManager()
    # # print(rm.list_resources())
    # rsrc = rm.open_resource('ASRL3::INSTR',read_termination = '\n')

    # rsrc.write('@254TST!ON;FF')
    # print(rsrc.read_bytes(12))
    # time.sleep(1)
    # # print(rsrc.get_visa_attribute(encoding))
    # rsrc.write('@254TST!OFF;FF')
    # print(rsrc.read_bytes(12))
    # rsrc.write('@254AD?;FF')
    # print(rsrc.read_bytes(12))
    # rsrc.write('@254PR1?;FF')
    # print(rsrc.read_bytes(12))
    # rsrc.close()
   ## on 3/6/2 the above pyvisa strategy is working

    # mksgauge = PressureGauge(rsrc)
    # print(mksgauge.__ask_address())
    # timestr = time.strftime('%Y%m%d-%H%M%S')
    # logger = logging.getLogger(__name__)
    # logging.basicConfig(filename=f'logs/CryoControlTest_{timestr}.log',level=logging.INFO)
    # logger.addHandler(logging.NullHandler())
    # pgauge = GenericSerialDevice(logger,com_port=3,parity=serial.PARITY_EVEN,testing=False,name='Temperature Controller')
    # response = pgauge.ask('@254TST!ON;FF')
    # print(response)
    # time.sleep(2)
    # response = pgauge.ask('@254TST!OFF;FF')
    # print(response)
    # response = pgauge.ask('@254PR1?;FF')
    # print(response)
    # pgauge.close_connection()
## on 3/6/2 the above gneeric serial device strategy is not working

    ser = serial.Serial(
        port="COM5", baudrate = 9600,
        parity=serial.PARITY_NONE,
        bytesize=8,stopbits=serial.STOPBITS_ONE, timeout=1)
    if ser.isOpen():
        print(ser.name + ' is open...')
        # for j in range(2):
        #     print(ser.readline())
    ## Write ASCII Commands To TSI 4043 Flow Sensor
    # ser.write(b'@254AD?;FF') # test mode (flashes LED)  
    # ser.write(b'@254TST!ON;FF')
    # print(ser.readline().decode())
    # time.sleep(10)
    # ser.write(b'@254TST!OFF;FF')
    ser.write(b'@254PR4?;FF')
    
    for n in range(3):
        rsp = ser.readline()
        print(rsp)
        print(rsp.decode())

    ser.close()
 ## on 3/6/25 the above returned 
    #     COM3 is open...
    # b'@253ACK736.0;FF'
    # @253ACK736.0;FF
    # b''

    # b''
