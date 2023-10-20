from typing import Dict, Any
import threading
import time
import datetime
import socket
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.core.virtual import viewport
from luma.oled.device import ssd1306
import config
import prt


class OLEDController:
    def __init__(self):
        if config.OLED_ENABLE:
            try:
                hostname = socket.gethostname()
            except Exception:
                hostname = "unknown"

            try:
                self.startup_phase = True
                self.list_entry_amount = 20

                self.serial = i2c(port=config.OLED_PORT, address=config.OLED_ADDRESS)
                self.device = ssd1306(self.serial, height=64, rotate=0)
                self.virtual = viewport(self.device, width=128, height=768)

                self.thread = threading.Thread(target=self._oled_worker)
                self.thread.daemon = True
                self.thread.start()
                with canvas(self.virtual) as draw:
                    draw.text((20, 5), text="IFK AIR SENSOR", fill="white")
                    draw.text((28, 20), text="version 0.1", fill="white")
                    draw.text((15, 35), text="hostname:" + hostname, fill="white")
                    draw.text((23, 50), text="startup phase", fill="white")
                print(f"OLED connected to i2c port: {config.OLED_PORT} on address: {hex(config.OLED_ADDRESS)}")
            except Exception:
                print(f"No OLED display found on i2c port: {config.OLED_PORT} on address: {hex(config.OLED_ADDRESS)}")

    def _oled_worker(self) -> None:
        while True:
            # How far we have to scroll to show all entries with a 9 pixel high text
            skroll_len = 9 * self.list_entry_amount
            # This list will scroll up and down and wait for some iterations at the top and bottom
            skroll_list = [0] * 60 + list(range(skroll_len)) + [skroll_len] * 30 + list(reversed(range(skroll_len)))
            for y_pos in skroll_list:
                time.sleep(0.01)
                if self.startup_phase:
                    break
                try:
                    self.virtual.set_position((0, y_pos))
                except Exception:
                    self.startup_phase = True

    def _get_unit(self, key: str) -> str:
        lookup = {
            "pm1": "ug/m^3",
            "pm25": "ug/m^3",
            "pm10": "ug/m^3",
            "opc_humid": "%",
            "opc_temp": "°C",
            "sht_humid": "%",
            "sht_temp": "°C",
            "hyt_humid": "%",
            "hyt_temp": "°C",
            "CO": "ppb",
            "NO": "ppb",
            "NO2": "ppb",
            "O3": "ppb",
            "heater_temp": "°C",
            "heater": "%",
            "lat": "°",
            "lon": "°",
            "alt": "m",
            "rssi": "dBm",
        }
        unit = lookup.get(key)
        return unit if unit is not None else ""

    def update_view(self, data: Dict[str, Any], mqtt_connected: bool, modem_num: int, logger_state: str) -> None:
        data_string = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n"
        for key, value in data.items():
            data_string += f"{key}: {value} {self._get_unit(key)}\n"
        data_string += f"server_connect: {mqtt_connected}\n"
        data_string += f"modem_num: {modem_num}\n"
        data_string += f"logger_state: {logger_state}\n"

        try:
            with canvas(self.virtual) as draw:
                for i, line in enumerate(data_string.split("\n")):
                    draw.text((0, (i * 12)), text=line, fill="white")
            self.list_entry_amount = i + 1  # We need this to know how far to scroll
            self.startup_phase = False
        except Exception:
            prt.GLOBAL_ENTITY.print_once("OLED disconnected", "OLED back online", 62)

    def stop(self) -> None:
        self.device.cleanup()
