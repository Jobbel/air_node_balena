import time
import prt
import smbus
import config
from generic_sensor import SensorBase

class HYTHandler(SensorBase):
    def __init__(self):
        self.delay = 50.0 / 1000.0  # 50-60 ms delay. Without delay, it doesn't work.
        self.bus = smbus.SMBus(1)  # use /dev/i2c1

    def getData(self):
        try:
            self.bus.write_byte(config.HYT_ADDRESS, 0x00)  # send some stuff
            time.sleep(self.delay)  # wait a bit
            reading = self.bus.read_i2c_block_data(config.HYT_ADDRESS, 0x00, 4)  # read the bytes
            # Mask the first two bits
            humidity = round(((reading[0] & 0x3F) * 0x100 + reading[1]) * (100.0 / 16383.0), config.DIGIT_ACCURACY)
            # Mask the last two bits, shift 2 bits to the right
            temperature = round(165.0 / 16383.0 * ((reading[2] * 0x100 + (reading[3] & 0xFC)) >> 2) - 40,
                                config.DIGIT_ACCURACY)

            # Apply two point calibration
            humidity = self.calibrate(humidity, config.HYT_CALI_HUMID)
            temperature = self.calibrate(temperature, config.HYT_CALI_TEMP)
            return {"hyt_humid": humidity, "hyt_temp": temperature}

        except:
            prt.global_entity.printOnce("HYT disconnected", "HYT back online")
            return {"hyt_humid": 0, "hyt_temp": 0}

    def stop(self):
        self.bus.close()
