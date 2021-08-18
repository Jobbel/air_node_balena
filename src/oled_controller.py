import threading
import time
import datetime
import prt
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.core.virtual import viewport
from luma.oled.device import ssd1306
from PIL import Image
import config


class OLEDController(object):

    def __init__(self):
        try:
            self.startup_phase = True
            self.list_entry_amount = 21

            self.serial = i2c(port=6, address=config.OLED_ADDRESS)
            self.device = ssd1306(self.serial, height=64, rotate=0)
            self.virtual = viewport(self.device, width=128, height=768)

            self.t = threading.Thread(target=self.animateSkrolling)
            self.t.setDaemon(True)
            self.t.start()
            with canvas(self.virtual) as draw:
                draw.text((20, 10), text="IFK AIR SENSOR", fill="white")
                draw.text((23, 25), text="startup phase", fill="white")
                draw.text((28, 40), text="version 0.1", fill="white")
            print("OLED connected to i2c6")
        except:
            print("No OLED display found on i2c6")

    def animateSkrolling(self):
        while True:
            skroll_len = 9 * self.list_entry_amount  # How far we have to skroll to show all entrys with a 9 pixel high text
            # This list will skroll up and down and wait for 30 iterations at the top and bottom
            skroll_list = [0] * 30 + list(range(skroll_len)) + [skroll_len] * 30 + list(reversed(range(skroll_len)))
            for y in skroll_list:
                if self.startup_phase is False:
                    try:
                        self.virtual.set_position((0, y))
                    except:
                        self.startup_phase = True
                time.sleep(0.01)

    def getUnit(self, key):
        lookup = {'pm1': "ug/m^3", 'pm25': "ug/m^3", 'pm10': "ug/m^3", 'opc_humid': "%",
                  'opc_temp': "°C", 'sht_humid': "%", 'sht_temp': "°C", 'hyt_humid': "%",
                  'hyt_temp': "°C", 'CO': "ppb", 'NO': "ppb", 'NO2': "ppb", 'O3': "ppb",
                  'heater': '%', 'lat': "°", 'lon': "°", 'alt': "m", 'rssi': "dBm"}
        if key in lookup:
            return lookup[key]
        else:
            return ""

    def updateView(self, data, mqtt_connected, modem_num):
        data_string = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n"
        for key, value in data.items():
            data_string += f"{key}: {value} {self.getUnit(key)}\n"
        data_string += f"server_connect: {mqtt_connected}\n"
        data_string += f"modem_num: {modem_num}\n"

        try:
            with canvas(self.virtual) as draw:
                for i, line in enumerate(data_string.split("\n")):
                    draw.text((0, (i * 12)), text=line, fill="white")
            self.list_entry_amount = i  # We need this to know how far to scroll
            self.startup_phase = False
        except:
            prt.global_entity.printOnce("OLED disconnected", "OLED back online", 62)

    def stop(self):
        self.device.cleanup()
