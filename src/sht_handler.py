import time

import prt
from Adafruit_SHT31 import *


class SHTHandler(object):
    def __init__(self, digit_accuracy, address=0x44, heating_enabled=True):
        self.sensor = SHT31(address=address)
        self._digit_accuracy = digit_accuracy
        self._heating_enabled = heating_enabled
        self.counter = 0

    def handleHeater(self):
        if self.counter == 0:
            self.sensor.set_heater(False)  # Turn off heater if it was enabled on the last call of getData()

        self.counter += 1

        if self.counter >= 20:  # Heat every 20 seconds for 1 second to remove condensation from the sensor
            # print("Heating SHT for 1 second")
            self.sensor.set_heater(True)
            self.counter = 0

    def getData(self):
        try:
            if self._heating_enabled is True:
                self.handleHeater()
                time.sleep(0.01)  # If we dont wait here, i2c fails for some reason

            (temp, humid) = self.sensor.read_temperature_humidity()
            return {"sht_humid": round(humid, self._digit_accuracy), "sht_temp": round(temp, self._digit_accuracy)}

        except:
            prt.global_entity.printOnce("SHT disconnected", "SHT back online")
            return {"sht_humid": 0, "sht_temp": 0}

    def stop(self):
        self.sensor.set_heater(False)
