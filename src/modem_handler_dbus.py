from typing import Dict, Any, Optional
import time
from subprocess import STDOUT, check_output
import threading
import prt
import config
import dbus
from pynmeagps import NMEAReader


class ModemHandlerDBus:

    def __init__(self):
        self.gps_timestamp = "unknown"
        self.current_gps_data = {"lat": None, "lon": None, "alt": None, "rssi": None}
        self.modem_num = -1

        if config.GPS_POLL_ENABLE:
            self.bus = dbus.SystemBus()
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
            if self.modem_num != -1:
                ret.update(self._get_gps_location())
                ret["rssi"] = self._get_signal_quality()  # Only signal quality from 0 to 100% is available
            else:
                self.gps_timestamp = "unknown"
                prt.GLOBAL_ENTITY.print_once("GPS disconnected", "GPS back online", 10)
            self.current_gps_data = ret
            time.sleep(1)

    def _update_modem_number(self) -> None:
        try:
            modem_manager_proxy = self.bus.get_object("org.freedesktop.ModemManager1", "/org/freedesktop/ModemManager1")
            object_manager_interface = dbus.Interface(modem_manager_proxy, "org.freedesktop.DBus.ObjectManager")
            managed_objects = object_manager_interface.GetManagedObjects()

            for path, interfaces in managed_objects.items():
                if "org.freedesktop.ModemManager1.Modem" in interfaces:
                    modem_num = path.split("/")[-1]
                    if modem_num.isdecimal():
                        self.modem_num = int(modem_num)
                        return
            self.modem_num = -1

        except Exception:
            self.modem_num = -1

    def _enable_gps(self) -> None:
        try:
            modem = self.bus.get_object('org.freedesktop.ModemManager1', f"/org/freedesktop/ModemManager1/Modem/{self.modem_num}")
            location_interface = dbus.Interface(modem, 'org.freedesktop.ModemManager1.Modem.Location')
            # Enable GPS NMEA tracking
            # 0 none
            # 1 3gpp
            # 2 gps raw
            # 4 gps nmea <- we only want nmea as it contains both location and datetime
            # 6 raw and nmea
            location_interface.Setup(4, False)  # (gps tracking mode, emit signals)
            #location_interface.SetGpsRefreshRate(1)
            #properties_interface = dbus.Interface(modem, "org.freedesktop.DBus.Properties")
            #signals_location = properties_interface.Get("org.freedesktop.ModemManager1.Modem.Location", "Enabled")
            #print("set gps tracking to:", signals_location)
            print(f"Enabled GPS tracking on modem number: {self.modem_num}")

        except Exception as e:
            prt.GLOBAL_ENTITY.print_once(f"Failed to enable GPS tracking, dump: {e}",
                                        f"Error stopped occuring: Failed to enable GPS tracking, dump: {e}", 10)

    def _get_gps_location(self) -> Dict[str, Any]:
        ret = {"lat": None, "lon": None, "alt": None}
        try:
            modem = self.bus.get_object('org.freedesktop.ModemManager1', f"/org/freedesktop/ModemManager1/Modem/{self.modem_num}")
            location_interface = dbus.Interface(modem, 'org.freedesktop.ModemManager1.Modem.Location')
            location_data = location_interface.GetLocation()

            if not location_data:  # if no data is returned the GPS tracking has not been enabled
                self._enable_gps()
                return ret
            for key, value in location_data.items():
                if key != 4:  # 4 corresponds to the NMEA data, if it is missing the GPS tracking has not been enabled
                    self._enable_gps()
                    continue
                for line in value.splitlines():
                    nmea = NMEAReader.parse(line)
                    if nmea == None:
                        continue
                    if nmea.msgID == "GGA" and nmea.quality == 0:
                        continue # no gps fix
                    if nmea.msgID == "GGA" and nmea.lat != "" and nmea.lon != "" and nmea.alt != "":
                        ret["lat"] = nmea.lat
                        ret["lon"] = nmea.lon
                        ret["alt"] = nmea.alt
                        continue
                    if nmea.msgID == "RMC" and nmea.date != "" and nmea.time != "":
                        # nmea.time sometimes contains milliseconds, sometimes it does not
                        time_str = nmea.time if "." in str(nmea.time) else f"{nmea.time}.000000"
                        ts = time.strptime(f"{nmea.date}:{time_str}", "%Y-%m-%d:%H:%M:%S.%f")
                        self.gps_timestamp = time.mktime(ts)
                        continue
            #print(f"lat:{ret['lat']}, lon:{ret['lon']}, alt:{ret['alt']}, time:{self.gps_timestamp}")
        except Exception as e:
            self.gps_timestamp = "unknown"
            prt.GLOBAL_ENTITY.print_once(f"Failed to get GPS data, dump: {e}", f"Error stopped occuring: Failed to get GPS data, dump: {e}", 10)
        return ret

    def _get_signal_quality(self) -> Optional[int]:
        try:
            modem = self.bus.get_object("org.freedesktop.ModemManager1", f"/org/freedesktop/ModemManager1/Modem/{self.modem_num}")
            properties_interface = dbus.Interface(modem, "org.freedesktop.DBus.Properties")
            signal_quality = properties_interface.Get("org.freedesktop.ModemManager1.Modem", "SignalQuality")[0] 
            return signal_quality
        except Exception as e:
            prt.GLOBAL_ENTITY.print_once(f"Failed to get signal quality data, dump: {e}",
                                        f"Error stopped occuring: Failed to get signal quality data, dump: {e}", 10)
            return None

    def stop(self) -> None:
        pass
