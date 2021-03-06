import time
from subprocess import STDOUT, check_output
import threading
import prt
import os
import config


class ModemHandler(object):

    def __init__(self):
        self.gps_timestamp = "unknown"
        self.current_gps_data = {"lat": 0, "lon": 0, "alt": 0, "rssi": 0}
        self.modem_num = -1

        if config.GPS_POLL_ENABLE:
            self.t = threading.Thread(target=self.modemWorker)
            self.t.setDaemon(True)
            self.t.start()

    def getData(self):
        return self.current_gps_data

    def getGPSTimestamp(self):
        return self.gps_timestamp

    def getMMNumber(self):
        return self.modem_num

    def modemWorker(self):
        time.sleep(20)
        print("Started GPS polling thread")
        while True:
            ret = {"lat": 0, "lon": 0, "alt": 0, "rssi": 0}
            self.updateModemNumber()
            time.sleep(1)  # Without these qmicli times out
            if self.modem_num != -1:
                ret.update(self.getGPSLocation())
                time.sleep(1)  # Without these qmicli times out
                ret["rssi"] = self.getRSSI()
            else:
                prt.global_entity.printOnce("GPS disconnected", "GPS back online", 10)

            self.current_gps_data = ret
            time.sleep(3)


    def updateModemNumber(self):
        cmd = "mmcli -L | grep Modem | sed -e 's/\//\ /g' | awk '{print $5}'"
        try:
            ret = check_output(cmd, shell=True, stderr=STDOUT, timeout=1).decode("utf-8").strip()
            if ret != "" and ret.isdigit():
                self.modem_num = int(ret)
            else:
                self.modem_num = -1
        except:
            self.modem_num = -1

    def enableGPS(self):
        cmd = "mmcli -m " + str(self.modem_num) + " --command=AT+CGPS=1,1"
        try:
            ret = check_output(cmd, shell=True, stderr=STDOUT, timeout=1).decode("utf-8")
            return """response: ''""" in ret
        except:
            return False

    def getGPSLocation(self):
        ret = {"lat": 0, "lon": 0, "alt": 0}
        cmd = "mmcli -m " + str(self.modem_num) + " --command=AT+CGPSINFO"
        try:
            nmea_data = check_output(cmd, shell=True, stderr=STDOUT, timeout=1).decode("utf-8").strip().split("'")[1]
            if ",,,,,,,," in nmea_data:
                # At this point we either have no fix or gps has not been enabled yet
                if not self.enableGPS():
                    prt.global_entity.printOnce("no GPS fix", "Error stopped occuring: no GPS fix", 10)
                self.gps_timestamp = "unknown"
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
            self.gps_timestamp = "unknown"
            prt.global_entity.printOnce("Failed to get GPS data", "Error stopped occuring: Failed to get GPS data", 10)
        return ret

    def getRSSI(self):
        cmd = "mmcli -m " + str(self.modem_num) + " --command=AT+CSQ"
        try:
            ret = check_output(cmd, shell=True, stderr=STDOUT, timeout=1).decode("utf-8")
            return self.convertSSToRSSI(ret.strip().split("response: '+CSQ: ")[1].split(",")[0])
        except:
            prt.global_entity.printOnce("Failed to get signal strength data",
                                        "Error stopped occuring: Failed to get signal strength data", 10)
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
