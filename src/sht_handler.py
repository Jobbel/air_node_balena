from typing import Dict, Optional
import time
from Adafruit_SHT31 import SHT31
import prt
import config
from generic_sensor import SensorBase


class SHTHandler(SensorBase):
    def __init__(self):
        super().__init__()
        self.sensor = SHT31(address=config.SHT_ADDRESS)
        self.counter = 0

    def _handle_heater(self) -> None:
        if self.counter == 0:
            # Turn off heater if it was enabled on the last call of getData()
            self.sensor.set_heater(False)

        self.counter += 1

        # Heat every 20 seconds for 1 second to remove condensation from the sensor
        if self.counter >= 20:
            # print("Heating SHT for 1 second")
            self.sensor.set_heater(True)
            self.counter = 0

    def get_data(self) -> Dict[str, Optional[float]]:
        try:
            if config.SHT_HEATER_ENABLE:
                self._handle_heater()
            else:
                self.sensor.set_heater(False)
            time.sleep(0.01)  # If we don't wait here, i2c fails for some reason

            (temp, humid) = self.sensor.read_temperature_humidity()

            # Apply two point calibration
            humid = self._calibrate(humid, config.SHT_CALI_HUMID)
            temp = self._calibrate(temp, config.SHT_CALI_TEMP)

            return {"sht_humid": humid, "sht_temp": temp}

        except Exception:
            prt.GLOBAL_ENTITY.print_once("SHT disconnected", "SHT back online")
            return {"sht_humid": None, "sht_temp": None}

    def stop(self) -> None:
        self.sensor.set_heater(False)
