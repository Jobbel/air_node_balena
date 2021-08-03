import threading
import time

import prt
import pyopcn3
import spidev


class OPCHandler(object):
    def __init__(self, digit_accuracy):
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.mode = 1
        self.spi.max_speed_hz = 500000
        self._digit_accuracy = digit_accuracy
        self.connected = False

        self.request_data = threading.Event()  # this event is used to request data from outside the thread
        self.data = None  # used to pass data from runner thread to getData

        self.t = threading.Thread(target=self.runner)
        self.t.setDaemon(True)
        self.t.start()
        time.sleep(3)  # Give the thread some time to connect to the opc

    def runner(self):
        while True:
            if self.connected is False:
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
        ret = {'pm1': 0, 'pm25': 0, 'pm10': 0, 'opc_humid': 0, 'opc_temp': 0}
        if self.connected:
            self.request_data.set()
            time.sleep(0.1)
            if self.data is not None and self.request_data.is_set() is False:
                ret['pm1'] = round(self.data['PM1'], self._digit_accuracy)
                ret['pm25'] = round(self.data['PM2.5'], self._digit_accuracy)
                ret['pm10'] = round(self.data['PM10'], self._digit_accuracy)
                ret['opc_humid'] = round(self.data['Relative humidity'], self._digit_accuracy)
                ret['opc_temp'] = round(self.data['Temperature'], self._digit_accuracy)
            else:
                self.connected = False
        else:
            prt.global_entity.printOnce("OPC disconnected", "OPC back online")
        self.data = None
        return ret

    def stop(self):
        self.alphasense.off()
