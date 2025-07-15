
import nidaqmx, logging
import time as t

class DAQ():
    '''Class for communicating with ni daq that controls relays'''
    def __init__(self, logger):
        # system = nidaqmx.system.System.local()
        # DAQ_device = system.device['Dev1']
        self.logger = logger
        
        ## use nidaqmx Task() to create digital output channels (on/off relays)
        self.relay1 = nidaqmx.Task()
        self.relay1.do_channels.add_do_chan("Dev1/port0/line0")
        self.relay2 = nidaqmx.Task()
        self.relay2.do_channels.add_do_chan("Dev1/port0/line1")
        logger.info('Initialized relays at "Dev1/port0/line0" and "Dev1/port0/line1"')

    def open_relay1(self):
        self.logger.info('Write True at relay 1 to open')
        self.relay1.write(True)
    
    def close_relay1(self):
        self.logger.info('Write False at relay 1 to close')
        self.relay1.write(False)

    def open_relay2(self):
        self.logger.info('Write True at relay 2 to open')
        self.relay2.write(True)
    
    def close_relay2(self):
        self.logger.info('Write False at relay 2 to close')
        self.relay2.write(False)

    def close_connections(self):
        ## closes tasks so resources can be re-allocated
        self.relay1.close()
        self.relay2.close()
        


if __name__ == "__main__":
    # import pyvisa # if not demoMode
    timestr = t.strftime('%Y%m%d-%H%M%S')
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename=f'logs/CryoControlTest_{timestr}.log',level=logging.DEBUG)
    logger.addHandler(logging.NullHandler())
    
    testdaq = DAQ(logger)
    testdaq.open_relay1()
    t.sleep(5)
    testdaq.close_relay1()
    testdaq.close_connections()
