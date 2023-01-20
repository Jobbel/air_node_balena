from typing import Dict, Any, Optional
import time
from subprocess import STDOUT, check_output
import threading
import prt
import config


class ModemHandler:

    def __init__(self):
        self.gps_timestamp = "unknown"
        self.current_gps_data = {"lat": None, "lon": None, "alt": None, "rssi": None}
        self.modem_num = -1

        if config.GPS_POLL_ENABLE:
            self.thread = threading.Thread(target=self._modem_worker)
            self.thread.daemon = True
            self.thread.start()

    def get_data(self) -> Dict[str, Any]:
        return self.current_gps_data

    def get_gps_timestamp(self) -> str:
        return self.gps_timestamp

    def get_mm_number(self) -> int:
        return self.modem_num

    def _modem_worker(self) -> None:
        time.sleep(20)
        print("Started GPS polling thread")
        while True:
            ret = {"lat": None, "lon": None, "alt": None, "rssi": None}
            self._update_modem_number()
            time.sleep(1)  # Without these qmicli times out
            if self.modem_num != -1:
                ret.update(self._get_gps_location())
                time.sleep(1)  # Without these qmicli times out
                ret["rssi"] = self._get_rssi()
            else:
                prt.GLOBAL_ENTITY.print_once("GPS disconnected", "GPS back online", 10)
            self.current_gps_data = ret
            time.sleep(1)

    def _update_modem_number(self) -> None:
        cmd = "mmcli -L | grep Modem | sed -e 's/\//\ /g' | awk '{print $5}'"
        try:
            ret = check_output(cmd, shell=True, stderr=STDOUT, timeout=1).decode("utf-8").strip()
            if ret != "" and ret.isdigit():
                self.modem_num = int(ret)
            else:
                self.modem_num = -1
        except Exception:
            self.modem_num = -1

    def _enable_gps(self) -> bool:
        cmd = "mmcli -m " + str(self.modem_num) + " --command=AT+CGPS=1,1"
        try:
            ret = check_output(cmd, shell=True, stderr=STDOUT, timeout=1).decode("utf-8")
            return """response: ''""" in ret
        except Exception:
            return False

    def _get_gps_location(self) -> Dict[str, Any]:
        ret = {"lat": None, "lon": None, "alt": None}
        cmd = "mmcli -m " + str(self.modem_num) + " --command=AT+CGPSINFO"
        try:
            nmea_data = check_output(cmd, shell=True, stderr=STDOUT, timeout=1).decode("utf-8").strip().split("'")[1]
            if ",,,,,,,," in nmea_data:
                # At this point we either have no fix or gps has not been enabled yet
                self.gps_timestamp = "unknown"
                if not self._enable_gps():
                    prt.GLOBAL_ENTITY.print_once("no GPS fix", "Error stopped occuring: no GPS fix", 10)
                    time.sleep(5)  # Sleep to avoid spamming qmicli gps enable messages if already enabled
            elif "CGPSINFO" in nmea_data:
                # Format: [lat],[N/S],[log],[E/W],[date],[UTC time],[alt],[speed],[course]
                nmea_data = nmea_data[11:].split(',')  # remove CGPSINFO from the beginning
                raw_lat = str(nmea_data[0])
                raw_lon = str(nmea_data[2])
                ret['lat'] = round((float(raw_lat[0:2]) + (float(raw_lat[2:9]) / 60)), 6)
                ret['lon'] = round((float(raw_lon[0:3]) + (float(raw_lon[3:10]) / 60)), 6)
                ret['alt'] = float(nmea_data[6])
                ts = time.strptime(nmea_data[4] + ":" + nmea_data[5], "%d%m%y:%H%M%S.0")
                self.gps_timestamp = time.mktime(ts)
                # print(f"lat:{ret['lat']}, lon:{ret['lon']}, alt:{ret['alt']}, time:{self.gps_timestamp}")
            else:
                raise ValueError
        except Exception:
            self.gps_timestamp = "unknown"
            prt.GLOBAL_ENTITY.print_once("Failed to get GPS data", "Error stopped occuring: Failed to get GPS data", 10)
        return ret

    def _get_rssi(self) -> Optional[int]:
        cmd = "mmcli -m " + str(self.modem_num) + " --command=AT+CSQ"
        try:
            ret = check_output(cmd, shell=True, stderr=STDOUT, timeout=1).decode("utf-8")
            return self._convert_ss_to_rssi(int(ret.strip().split("response: '+CSQ: ")[1].split(",")[0]))
        except Exception:
            prt.GLOBAL_ENTITY.print_once("Failed to get signal strength data",
                                        "Error stopped occuring: Failed to get signal strength data", 10)
            return None

    def _convert_ss_to_rssi(self, ss: int) -> Optional[int]:
        lookup = {
            2: -109,
            3: -107,
            4: -105,
            5: -103,
            6: -101,
            7: -99,
            8: -97,
            9: -95,
            10: -93,
            11: -91,
            12: -89,
            13: -87,
            14: -85,
            15: -83,
            16: -81,
            17: -79,
            18: -77,
            19: -75,
            20: -73,
            21: -71,
            22: -69,
            23: -67,
            24: -65,
            25: -63,
            26: -61,
            27: -59,
            28: -57,
            29: -55,
            30: -53,
        }
        return lookup.get(ss)

    def stop(self) -> None:
        pass
