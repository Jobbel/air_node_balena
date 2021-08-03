import time
from subprocess import STDOUT, check_output, TimeoutExpired
import threading
import prt


class ModemHandler(object):

    def __init__(self):
        self.gps_timestamp = "unknown"
        self.current_gps_data = {"lat": 0, "lon": 0, "alt": 0, "rssi": 0}
        self.modem_num = -1

        self.t = threading.Thread(target=self.modemPoller)
        self.t.setDaemon(True)
        self.t.start()

    def getData(self):
        return self.current_gps_data

    def getGPSTimestamp(self):
        return self.gps_timestamp

    def getMMNumber(self):
        return self.modem_num

    def modemPoller(self):
        while True:
            ret = {"lat": 0, "lon": 0, "alt": 0, "rssi": 0}
            self.updateModemNumber()
            if self.modem_num is not -1:
                if self.enableGPS() is True:
                    ret.update(self.getGPSLocation())
                    ret["rssi"] = self.getRSSI()
                else:
                    prt.global_entity.printOnce("Failed to enable location gathering", "Error stopped occuring: Failed to enable location gathering")
            else:
                prt.global_entity.printOnce("GPS disconnected", "GPS back online")

            self.current_gps_data = ret
            time.sleep(1)

    def updateModemNumber(self):
        cmd = "mmcli -L | grep Modem | sed -e 's/\//\ /g' | awk '{print $5}'"
        try:
            ret = check_output(cmd, shell=True, stderr=STDOUT, timeout=0.1).decode("utf-8").strip()
            if ret is not "" and ret.isdigit():
                self.modem_num = int(ret)
            else:
                self.modem_num = -1
        except:
            prt.global_entity.printOnce("Getting modem number failed", "Error stopped occuring: Getting modem number failed")
            self.modem_num = -1

    def enableGPS(self):
        cmd = "mmcli -m " + str(self.modem_num) + " --location-enable-gps-raw"
        try:
            ret = check_output(cmd, shell=True, stderr=STDOUT, timeout=0.1).decode("utf-8")
            return "successfully setup location gathering" in ret
        except:
            prt.global_entity.printOnce("Enabling GPS failed", "Error stopped occuring: Enabling GPS failed")
            return False

    def getGPSLocation(self):
        ret = {"lat": 0, "lon": 0, "alt": 0}
        cmd = "mmcli -m " + str(self.modem_num) + " --command=AT+CGPSINFO"
        try:
            nmea_data = check_output(cmd, shell=True, stderr=STDOUT, timeout=0.1).decode("utf-8").strip().split("'")[1]
            if ",,,,,,,," in nmea_data:
                prt.global_entity.printOnce("no GPS fix", "Error stopped occuring: no GPS fix")
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
            else:
                raise ValueError
        except:
            prt.global_entity.printOnce("Failed to get GPS data", "Error stopped occuring: Failed to get GPS data")
        return ret

    def getRSSI(self):
        cmd = "mmcli -m " + str(self.modem_num) + " --command=AT+CSQ"
        try:
            ret = check_output(cmd, shell=True, stderr=STDOUT, timeout=0.1).decode("utf-8")
            return self.convertSSToRSSI(ret.strip().split("response: '+CSQ: ")[1].split(",")[0])
        except:
            prt.global_entity.printOnce("Failed to get signal strength data", "Error stopped occuring: Failed to get signal strength data")
            return 0

    def convertSSToRSSI(self, ss):
        lookup = {2: -109, 3: -107, 4: -105, 5: -103, 6: -101, 7: -99, 8: -97, 9: -95, 10: -93,
                  11: -91, 12: -89, 13: -87, 14: -85, 15: -83, 16: -81, 17: -79, 18: -77, 19: -75,
                  20: -73, 21: -71, 22: -69, 23: -67, 24: -65, 25: -63, 26: -61, 27: -59, 28: -57,
                  29: -55, 30: -53}
        ss = int(ss)
        if ss in lookup:
            return lookup[ss]
        else:
            return 0

    def stop(self):
        pass
