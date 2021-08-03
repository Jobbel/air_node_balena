import time

import prt
import smbus


class HYTHandler(object):
    def __init__(self, _digit_accuracy, address=0x28):
        self.addr = address
        self.delay = 50.0 / 1000.0  # 50-60 ms delay. Without delay, it doesn't work.
        self.bus = smbus.SMBus(1)  # use /dev/i2c1
        self.digit_accuracy = _digit_accuracy

    def getData(self):
        try:
            self.bus.write_byte(self.addr, 0x00)  # send some stuff
            time.sleep(self.delay)  # wait a bit
            reading = self.bus.read_i2c_block_data(self.addr, 0x00, 4)  # read the bytes
            # Mask the first two bits
            humidity = round(((reading[0] & 0x3F) * 0x100 + reading[1]) * (100.0 / 16383.0), self.digit_accuracy)
            # Mask the last two bits, shift 2 bits to the right
            temperature = round(165.0 / 16383.0 * ((reading[2] * 0x100 + (reading[3] & 0xFC)) >> 2) - 40,
                                self.digit_accuracy)
            return {"hyt_humid": humidity, "hyt_temp": temperature}

        except:
            prt.global_entity.printOnce("HYT disconnected", "HYT back online")
            return {"hyt_humid": 0, "hyt_temp": 0}

    def stop(self):
        self.bus.close()
