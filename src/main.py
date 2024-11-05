import datetime
import logging
import sys
import time
from signal import signal, SIGINT, SIGTERM
from typing import List, Dict, Any, Optional
from types import FrameType
import pandas as pd
from apscheduler.schedulers.blocking import BlockingScheduler
import config
import prt
from system_metrics import (
    get_cpu_temp,
    get_cpu_usage,
    get_uptime,
    get_disk_usage,
    get_usb_drive_usage,
    get_total_data_usage,
    get_ram_usage,
)
from adc_handler import ADCHandler
from heating_controller import HeatingController
from hyt_handler import HYTHandler
from logging_controller import LoggingController
from modem_handler import ModemHandler
from modem_handler_dbus import ModemHandlerDBus
from mqtt_controller import MQTTController
from oled_controller import OLEDController
from one_wire_handler import OneWireHandler
from opc_handler import OPCHandler
from prt import OncePrinter
from sht_handler import SHTHandler
from internet_watchdog import InternetWatchdog


### GLOBAL VARS ###
# List for storing and averaging sensor data dicts
minute_data = []

### GLOBAL INSTANCES ###
# This scheduler calls the everySecond and everyMinute functions
scheduler = BlockingScheduler()
# This instantiates the single OncePrinter used across all modules
prt.GLOBAL_ENTITY = OncePrinter()
# This reads gps and signal strength data from the modem periodically
if config.GPS_POLL_USE_DBUS:
    modem = ModemHandlerDBus()
else:
    modem = ModemHandler()
# This object will log average and raw data to a usb drive
logg = LoggingController()
# This instantiates a mqtt object and tries to connect if configured
if config.MQTT_ENABLE:
    mqtt = MQTTController()
# Start measurement air heater controller if configured
if config.HEATER_ENABLE:
    heat = HeatingController()
# Start oled display controller if configured
if config.OLED_ENABLE:
    oled = OLEDController()
# This watchdog keeps the internet connection alive by restarting the modem
if config.INTERNET_WATCHDOG_ENABLE:
    watchdog = InternetWatchdog(interval=config.INTERNET_WATCHDOG_INTERVAL, modem_handler_instance=modem)


### SENSOR INIT ###
try:
    if config.OPC_ENABLE:
        opc = OPCHandler()
    if config.SHT_ENABLE:
        sht = SHTHandler()
    if config.HYT_ENABLE:
        hyt = HYTHandler()
    if config.ADC_ENABLE:
        adc = ADCHandler()
    if config.ONE_WIRE_ENABLE:
        one_wire = OneWireHandler()
    print("Sensor startup successful")
except Exception as e:
    print(f"Sensor startup failed, dump: {e}")
    sys.exit()

time.sleep(10)  # Wait for all sensors to come online


def get_all_data() -> Dict[str, float]:
    ret = {}
    # get sensor data
    if config.OPC_ENABLE:
        ret.update(opc.get_data())
    if config.SHT_ENABLE:
        ret.update(sht.get_data())
    if config.HYT_ENABLE:
        ret.update(hyt.get_data())
    if config.ADC_ENABLE:
        ret.update(adc.get_data())
    if config.ONE_WIRE_ENABLE:
        ret.update(one_wire.get_data())
    # get telemetry
    if config.HEATER_ENABLE:
        ret.update(heat.get_data())
    ret.update(modem.get_data())
    return ret


def calculate_mean_data(collected_data: List[Dict[str, float]]) -> Optional[Dict[str, float]]:
    try:
        mean_df = pd.DataFrame(collected_data).mean()
        ret = mean_df.fillna(0).to_dict()
    except ValueError as e:
        print(f"Averaging minute data failed, skipping this minute. Error dump: {e}")
        return None
    # Make sure lat/lon coordinates have 6 decimal digits while the rest has the configured amount
    return {
        key: round(val, config.DIGIT_ACCURACY if key not in ["lat", "lon"] else 6)
        for key, val in ret.items()
    }


def append_timestamps_to(data: Dict[str, Any]) -> Dict[str, Any]:
    ret = dict(data)
    ret["timestamp"] = time.time()
    ret["timestamp_hr"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ret["timestamp_gps"] = modem.get_gps_timestamp()
    return ret


def generate_publishing_message(mean_data: Dict[str, float]) -> Dict[str, Any]:
    # move these 5 averaged telemetry entries from data to tele
    heater_buffer = mean_data.pop("heater", 0)
    lat_buffer = mean_data.pop("lat", 0)
    lon_buffer = mean_data.pop("lon", 0)
    alt_buffer = mean_data.pop("alt", 0)
    rssi_buffer = mean_data.pop("rssi", 0)
    # now there is only averaged sensor data in mean_data
    ret = {
        "node_id": config.NODE_ID,
        "data": mean_data,
        "tele": {
            "heater": heater_buffer,
            "lat": lat_buffer,
            "lon": lon_buffer,
            "alt": alt_buffer,
            "rssi": rssi_buffer,
            "data_used": get_total_data_usage(),
            "disk_used": get_disk_usage(),
            "usb_used": get_usb_drive_usage(),
            "ram_usage": get_ram_usage(),
            "cpu_load": get_cpu_usage(),
            "cpu_temp": get_cpu_temp(),
            "uptime": get_uptime(),
            "modem_num": modem.get_mm_number(),
            "logger_state": logg.get_logger_state(),
            "logger_queue": logg.get_logger_queue_size(),
            "rsync_runtime": logg.get_last_rsync_runtime(),
        },
    }
    return append_timestamps_to(ret)


def remove_raw_data_from(data: Dict[str, Any]) -> Dict[str, Any]:
    return {key: val for key, val in data.items() if not key.startswith("RAW_")}


def remove_none_from(data: Dict[str, Any]) -> Dict[str, Any]:
    return {key: 0 if val is None else val for key, val in data.items()}


def update_oled_display(data: Dict[str, Any]) -> None:
    data_clean = remove_raw_data_from(data)
    mqtt_state = mqtt.get_connected() if config.MQTT_ENABLE else False
    modem_mm = modem.get_mm_number()
    log_state = logg.get_logger_state()
    oled.update_view(data_clean, mqtt_state, modem_mm, log_state)


def every_second() -> None:
    second_data = get_all_data()
    minute_data.append(second_data)
    if config.HEATER_ENABLE:
        heat.update_heating(second_data)
    if config.OLED_ENABLE and config.OLED_RAW:
        update_oled_display(second_data)
    if config.LOGGING_RAW_ENABLE:
        # Remove None (missing sensor data) to get 0 entries in CSV Log
        logg.log_data_to("raw", append_timestamps_to(remove_none_from(second_data)))
    if not config.MQTT_PUBLISH_EVERY_SECOND:
        return
    if config.PUBLISH_RAW_OPC_AND_ADC:
        mqtt.publish_data(generate_publishing_message(remove_none_from(second_data)))
    else:
        mqtt.publish_data(generate_publishing_message(remove_raw_data_from(second_data)))


def every_minute() -> None:
    avg_data = calculate_mean_data(minute_data)
    minute_data.clear()
    if avg_data is None:
        return
    if config.OLED_ENABLE and not config.OLED_RAW:
        update_oled_display(avg_data)
    if config.LOGGING_AVG_ENABLE:
        # Average data does not contain None, see calculate_mean_data()
        logg.log_data_to("avg", append_timestamps_to(avg_data))
    if not config.MQTT_ENABLE:
        return
    if config.MQTT_PUBLISH_EVERY_SECOND:
        return
    if config.PUBLISH_RAW_OPC_AND_ADC:
        mqtt.publish_data(generate_publishing_message(avg_data))
    else:
        mqtt.publish_data(generate_publishing_message(remove_raw_data_from(avg_data)))


def exit_handler(signum: int, _frame: Optional[FrameType]) -> None:
    print("Received Signal: ", str(signum), "\nCleaning up")
    # Stop heater with highest priority
    if config.HEATER_ENABLE:
        heat.stop()
        print("Heater controller stopped")
    scheduler.shutdown(wait=False)
    modem.stop()
    logg.stop()
    ### Sensor cleanup ###
    if config.SHT_ENABLE:
        sht.stop()
    if config.OLED_ENABLE:
        oled.stop()
    if config.OPC_ENABLE:
        opc.stop()
    if config.HYT_ENABLE:
        hyt.stop()
    if config.ADC_ENABLE:
        adc.stop()
    if config.ONE_WIRE_ENABLE:
        one_wire.stop()
    if config.MQTT_ENABLE:
        mqtt.stop()
    print("Cleanup completed")
    sys.exit(0)

def get_next_full_minute():
    return datetime.datetime.now().replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)


def main() -> None:
    # capture exit signals (from tini if running in docker container)
    signal(SIGINT, exit_handler)
    signal(SIGTERM, exit_handler)

    # Comment these out if you want to see console logs
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("raw_logger").propagate = False
    logging.getLogger("avg_logger").propagate = False

    # Scheduler setup and blocking start call
    scheduler.add_job(every_second, "interval", seconds=1)
    scheduler.add_job(every_minute, "interval", minutes=1, next_run_time=get_next_full_minute())
    scheduler.start()


if __name__ == "__main__":
    main()
