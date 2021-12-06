import threading
import time

import config
import prt
import pyopcn3
import spidev
from generic_sensor import SensorBase


class OPCHandler(SensorBase):
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.mode = 1
        self.spi.max_speed_hz = 500000
        self.connected = False

        self.request_data = threading.Event()  # this event is used to request data from outside the thread
        self.data = None  # used to pass data from runner thread to getData

        self.t = threading.Thread(target=self.OPCWorker)
        self.t.setDaemon(True)
        self.t.start()
        time.sleep(3)  # Give the thread some time to connect to the opc

    def OPCWorker(self):
        while True:
            if not self.connected:
                self.alphasense = pyopcn3.OPCN3(self.spi)
                self.alphasense.on()
                time.sleep(1)
                self.connected = True
            elif self.request_data.is_set():
                self.data = self.alphasense.histogram(number_concentration=False)
                self.request_data.clear()
            else:
                time.sleep(0.01)  # This keeps CPU usage from always hitting 100%

    def getData(self):
        ret = {'pm1': 0, 'pm25': 0, 'pm10': 0, 'opc_flow': 0, 'opc_humid': 0, 'opc_temp': 0, 'RAW_OPC_Bin 0': 0,
               'RAW_OPC_Bin 1': 0, 'RAW_OPC_Bin 2': 0, 'RAW_OPC_Bin 3': 0, 'RAW_OPC_Bin 4': 0, 'RAW_OPC_Bin 5': 0,
               'RAW_OPC_Bin 6': 0, 'RAW_OPC_Bin 7': 0, 'RAW_OPC_Bin 8': 0, 'RAW_OPC_Bin 9': 0, 'RAW_OPC_Bin 10': 0,
               'RAW_OPC_Bin 11': 0, 'RAW_OPC_Bin 12': 0, 'RAW_OPC_Bin 13': 0, 'RAW_OPC_Bin 14': 0, 'RAW_OPC_Bin 15': 0,
               'RAW_OPC_Bin 16': 0, 'RAW_OPC_Bin 17': 0, 'RAW_OPC_Bin 18': 0, 'RAW_OPC_Bin 19': 0, 'RAW_OPC_Bin 20': 0,
               'RAW_OPC_Bin 21': 0, 'RAW_OPC_Bin 22': 0, 'RAW_OPC_Bin 23': 0, 'RAW_OPC_Bin1 MToF': 0,
               'RAW_OPC_Bin3 MToF': 0, 'RAW_OPC_Bin5 MToF': 0, 'RAW_OPC_Bin7 MToF': 0, 'RAW_OPC_Sampling Period': 0,
               'RAW_OPC_SFR': 0, 'RAW_OPC_Temperature': 0, 'RAW_OPC_Relative humidity': 0, 'RAW_OPC_PM1': 0,
               'RAW_OPC_PM2.5': 0, 'RAW_OPC_PM10': 0, 'RAW_OPC_Reject count Glitch': 0,
               'RAW_OPC_Reject count LongTOF': 0, 'RAW_OPC_Reject count Ratio': 0, 'RAW_OPC_Reject Count OutOfRange': 0,
               'RAW_OPC_Fan rev count': 0, 'RAW_OPC_Laser status': 0, 'RAW_OPC_Checksum': 0}

        if self.connected:
            self.request_data.set()
            time.sleep(0.1)
            if self.data is not None and not self.request_data.is_set():
                ret['pm1'] = round(self.data['PM1'], config.DIGIT_ACCURACY)
                ret['pm25'] = round(self.data['PM2.5'], config.DIGIT_ACCURACY)
                ret['pm10'] = round(self.data['PM10'], config.DIGIT_ACCURACY)
                ret['opc_flow'] = round(self.data['SFR'], config.DIGIT_ACCURACY)
                # Apply two point calibration
                ret['opc_humid'] = self.calibrate(self.data['Relative humidity'], config.OPC_CALI_HUMID)
                ret['opc_temp'] = self.calibrate(self.data['Temperature'], config.OPC_CALI_TEMP)

                prefix = "RAW_OPC_"
                prefixed_data = {prefix + str(key): val for key, val in self.data.items()}
                ret.update(prefixed_data)

            else:
                self.connected = False
        else:
            prt.global_entity.printOnce("OPC disconnected", "OPC back online")
        self.data = None
        return ret

    def stop(self):
        self.alphasense.off()
