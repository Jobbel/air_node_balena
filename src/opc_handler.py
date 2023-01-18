from typing import Dict, Any, Optional
import threading
import time
import spidev
import config
import prt
import pyopcn3
from generic_sensor import SensorBase


class OPCHandler(SensorBase):
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.mode = 1
        self.spi.max_speed_hz = 500000
        self.connected = False

        # holds the pyopcn instance
        self.alphasense = None
        # this event is used to request data from outside the thread
        self.request_data = threading.Event()
        # used to pass data from runner thread to getData
        self.data = None

        self.thread = threading.Thread(target=self._opc_worker)
        self.thread.daemon = True
        self.thread.start()
        # Give the thread some time to connect to the opc
        time.sleep(3)

    def _opc_worker(self) -> None:
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

    def get_data(self) -> Dict[str, Optional[float]]:
        ret = {
            "pm1": None,
            "pm25": None,
            "pm10": None,
            "opc_flow": None,
            "opc_humid": None,
            "opc_temp": None,
            "RAW_OPC_Bin 0": None,
            "RAW_OPC_Bin 1": None,
            "RAW_OPC_Bin 2": None,
            "RAW_OPC_Bin 3": None,
            "RAW_OPC_Bin 4": None,
            "RAW_OPC_Bin 5": None,
            "RAW_OPC_Bin 6": None,
            "RAW_OPC_Bin 7": None,
            "RAW_OPC_Bin 8": None,
            "RAW_OPC_Bin 9": None,
            "RAW_OPC_Bin 10": None,
            "RAW_OPC_Bin 11": None,
            "RAW_OPC_Bin 12": None,
            "RAW_OPC_Bin 13": None,
            "RAW_OPC_Bin 14": None,
            "RAW_OPC_Bin 15": None,
            "RAW_OPC_Bin 16": None,
            "RAW_OPC_Bin 17": None,
            "RAW_OPC_Bin 18": None,
            "RAW_OPC_Bin 19": None,
            "RAW_OPC_Bin 20": None,
            "RAW_OPC_Bin 21": None,
            "RAW_OPC_Bin 22": None,
            "RAW_OPC_Bin 23": None,
            "RAW_OPC_Bin1 MToF": None,
            "RAW_OPC_Bin3 MToF": None,
            "RAW_OPC_Bin5 MToF": None,
            "RAW_OPC_Bin7 MToF": None,
            "RAW_OPC_Sampling Period": None,
            "RAW_OPC_SFR": None,
            "RAW_OPC_Temperature": None,
            "RAW_OPC_Relative humidity": None,
            "RAW_OPC_PM1": None,
            "RAW_OPC_PM2.5": None,
            "RAW_OPC_PM10": None,
            "RAW_OPC_Reject count Glitch": None,
            "RAW_OPC_Reject count LongTOF": None,
            "RAW_OPC_Reject count Ratio": None,
            "RAW_OPC_Reject Count OutOfRange": None,
            "RAW_OPC_Fan rev count": None,
            "RAW_OPC_Laser status": None,
            "RAW_OPC_Checksum": None,
        }

        if self.connected:
            self.request_data.set()
            time.sleep(0.1)
            if self.data is not None and not self.request_data.is_set():
                ret["pm1"] = round(self.data["PM1"], config.DIGIT_ACCURACY)
                ret["pm25"] = round(self.data["PM2.5"], config.DIGIT_ACCURACY)
                ret["pm10"] = round(self.data["PM10"], config.DIGIT_ACCURACY)
                ret["opc_flow"] = round(self.data["SFR"], config.DIGIT_ACCURACY)
                # Apply two point calibration
                ret["opc_humid"] = self._calibrate(self.data["Relative humidity"], config.OPC_CALI_HUMID)
                ret["opc_temp"] = self._calibrate(self.data["Temperature"], config.OPC_CALI_TEMP)

                prefix = "RAW_OPC_"
                prefixed_data = {prefix + str(key): val for key, val in self.data.items()}
                ret.update(prefixed_data)

            else:
                self.connected = False
        else:
            prt.GLOBAL_ENTITY.print_once("OPC disconnected", "OPC back online")
        self.data = None
        return ret

    def stop(self) -> None:
        self.alphasense.off()
