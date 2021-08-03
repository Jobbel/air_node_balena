import threading
import time

import prt
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.core.virtual import viewport
from luma.oled.device import ssd1306


class OLEDController(object):

    def __init__(self):
        try:
            self.startup_phase = True
            self.serial = i2c(port=6, address=0x3C)
            self.device = ssd1306(self.serial, height=32, rotate=0)
            self.virtual = viewport(self.device, width=128, height=768)
            self.t = threading.Thread(target=self.animateSkrolling)
            self.t.setDaemon(True)
            self.t.start()
            with canvas(self.virtual) as draw:
                draw.text((20, 10), text="IFK AIR SENSOR", fill="white")
                draw.text((22, 20), text="startup phase", fill="white")
            print("OLED connected to i2c port 6")
        except:
            print("No OLED display found on i2c port 6")

    def animateSkrolling(self):
        while True:
            for y in range(250):
                if self.startup_phase is False:
                    try:
                        self.virtual.set_position((0, y))
                    except:
                        self.startup_phase = True
                time.sleep(0.02)

    def getUnit(self, key):
        lookup = {'pm1': "ug/m^3", 'pm25': "ug/m^3", 'pm10': "ug/m^3", 'opc_humid': "%",
                  'opc_temp': "°C", 'sht_humid': "%", 'sht_temp': "°C", 'hyt_humid': "%",
                  'hyt_temp': "°C", 'CO': "ppb", 'NO': "ppb", 'NO2': "ppb", 'O3': "ppb",
                  'heater': '%', 'lat': "°", 'lon': "°", 'alt': "m", 'rssi': "dBm"}
        if key in lookup:
            return lookup[key]
        else:
            return ""

    def updateView(self, data):
        data_string = ""
        for key, value in data.items():
            data_string += f"{key}: {value} {self.getUnit(key)}\n"

        try:
            with canvas(self.virtual) as draw:
                for i, line in enumerate(data_string.split("\n")):
                    draw.text((0, 40 + (i * 12)), text=line, fill="white")

            self.startup_phase = False
        except:
            prt.global_entity.printOnce("OLED disconnected", "OLED back online", 62)


    def stop(self):
        self.device.cleanup()
