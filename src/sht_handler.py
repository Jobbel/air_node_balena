import time

import prt
from Adafruit_SHT31 import *
import config


class SHTHandler(object):
    def __init__(self):
        self.sensor = SHT31(address=config.SHT_ADDRESS)
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
            if config.SHT_HEATER_ENABLE:
                self.handleHeater()
                time.sleep(0.01)  # If we dont wait here, i2c fails for some reason

            (temp, humid) = self.sensor.read_temperature_humidity()
            return {"sht_humid": round(humid, config.DIGIT_ACCURACY), "sht_temp": round(temp, config.DIGIT_ACCURACY)}

        except:
            prt.global_entity.printOnce("SHT disconnected", "SHT back online")
            return {"sht_humid": 0, "sht_temp": 0}

    def stop(self):
        self.sensor.set_heater(False)
