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
        ret = {'pm1': 0, 'pm25': 0, 'pm10': 0, 'opc_flow': 0, 'opc_humid': 0, 'opc_temp': 0}
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
                # print(self.data)
            else:
                self.connected = False
        else:
            prt.global_entity.printOnce("OPC disconnected", "OPC back online")
        self.data = None
        return ret

    def stop(self):
        self.alphasense.off()
