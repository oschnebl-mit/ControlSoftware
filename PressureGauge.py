import re, pyvisa
from pyqtgraph.Qt import QtCore

class PressureGaugeThread(QtCore.QThread):
    '''
    Thread that periodically reads from pressure gauge via serial communication
    '''
    newData = QtCore.pyqtSignal(object)

    def __init__(self,instrument,deviceAddress=None,delay=10):
        '''instrument is string (e.g. 'ASRL3::INSTR') and device Address is string of 5 ints
        '''
        super().__init__()
        self.running = False
        self.delay = delay
        self.__connection: pyvisa = pyvisa.ResourceManager().open_resource(instrument) # read/write terminations?
        self.__address: str = deviceAddress

        if self.__address == None:
            newaddress = self.__ask_address()
            self.__address = newaddress[7:9]

    def run(self):
        self.running = True
        while self.running:
            self.output = self.get_pressure()
            self.newData.emit(self.output)
            QtCore.QThread.msleep(self.delay)


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