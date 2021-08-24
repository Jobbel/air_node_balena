import datetime
import logging
import time

import config
import prt
import psutil
from adc_handler import ADCHandler
from apscheduler.schedulers.blocking import BlockingScheduler
from heating_controller import HeatingController
from hyt_handler import HYTHandler
from logging_controller import LoggingController
from modem_handler import ModemHandler
from mqtt_controller import MQTTController
from oled_controller import OLEDController
from opc_handler import OPCHandler
from prt import OncePrinter
from requests import get
from sht_handler import SHTHandler

### GLOBAL VARS ###
prt.global_entity = OncePrinter()  # This instantiates the OncePrinter used across all modules
modem = ModemHandler()  # This reads gps and signal strength data from the modem periodically
mqtt = MQTTController()  # This instantiates an mqtt object and tries to connect
logg = LoggingController()  # This object will log average and raw data to a usb drive
if config.HEATER_ENABLE:
    heat = HeatingController()
if config.OLED_ENABLE:
    oled = OLEDController()

minute_data = []  # Container for storing and averaging sensor data
public_ip = "unknown"

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
    print("Sensor startup successful")
except:
    print("Sensor startup failed!")


def getCPUTemp():
    try:
        temp_file = open('/sys/class/thermal/thermal_zone0/temp')
        return round(float(temp_file.read()) / 1000, 2)
    except:
        return 0


def getUptime():
    try:
        temp_file = open('/proc/uptime', 'r')
        uptime_seconds = round(float(temp_file.readline().split()[0]))
        return str(datetime.timedelta(seconds=uptime_seconds))
    except:
        return 0


def getDiskUsage():
    try:
        return psutil.disk_usage('/mnt/storage').percent
    except:
        prt.global_entity.printOnce("Failed to fetch disk usage", "Successfully fetching disk usage again", 62)
        return 0


def getTotalDataUsage():
    for device in ['wwan0', 'wwp1s0u1u3i5', 'wwp1s0u1u4i5', 'ppp0']:
        try:
            netio = psutil.net_io_counters(pernic=True)
            net_usage = netio[device].bytes_sent + netio[device].bytes_recv
            return round(net_usage / 1000000, 2)
        except:
            pass
    prt.global_entity.printOnce("Failed to fetch data usage", "Successfully fetching data usage again", 62)
    return 0


def updatePublicIP():
    global public_ip
    try:
        public_ip = get('https://api.ipify.org').text
    except:
        print("failed to fetch public ip")
        public_ip = "unknown"


def getAllData():
    ret = {}
    # get sensors
    if config.OPC_ENABLE:
        ret.update(opc.getData())
    if config.SHT_ENABLE:
        ret.update(sht.getData())
    if config.HYT_ENABLE:
        ret.update(hyt.getData())
    # we need the current temperature for the gas sensor formula
    if config.ADC_ENABLE:
        ret.update(adc.getData(ret))
    # get telemetry
    if config.HEATER_ENABLE:
        ret.update(heat.getData())
    ret.update(modem.getData())
    return ret


def calculateMeanData(minute_data):
    mean_dict = {}
    for key in minute_data[0].keys():
        try:
            if key not in ["lat", "lon", "alt"]:  # latitude and longitude need a higher rounding accuracy
                mean_dict[key] = round(sum(d[key] for d in minute_data) / len(minute_data), config.DIGIT_ACCURACY)
            else:
                i_list = [d[key] for d in minute_data if d[key] != 0]  # intermediate list without 0s
                if i_list:
                    mean_dict[key] = round(sum(i_list) / len(i_list), (config.DIGIT_ACCURACY if key == "alt" else 6))
                else:
                    # if there are only zeros in the list handle division by zero
                    mean_dict[key] = 0.0
        except:
            print(key, "not available, did the sensor die ?")
    return mean_dict


def appendTimestampsTo(data):
    ret = dict(data)
    ret['timestamp'] = time.time()
    ret['timestamp_hr'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ret['timestamp_gps'] = modem.getGPSTimestamp()
    return ret


def generatePublishingMessage(mean_data):
    # move these 5 averaged telemetry entries from data to tele
    heater_buffer = mean_data.pop("heater")
    lat_buffer = mean_data.pop("lat")
    lon_buffer = mean_data.pop("lon")
    alt_buffer = mean_data.pop("alt")
    rssi_buffer = mean_data.pop("rssi")
    # now there is only averaged sensor data in mean_data
    ret = {"node_id": config.NODE_ID,
           "data": mean_data,
           "tele": {
               "heater": heater_buffer,
               "lat": lat_buffer,
               "lon": lon_buffer,
               "alt": alt_buffer,
               "rssi": rssi_buffer,
               "data_used": getTotalDataUsage() if config.GPS_POLL_ENABLE else 0,
               "disk_used": getDiskUsage() if config.LOGGING_RAW_ENABLE or config.LOGGING_AVG_ENABLE else 0,
               "cpu_load": psutil.cpu_percent(),
               "cpu_temp": getCPUTemp(),
               "uptime": getUptime(),
               "public_ip": public_ip,
               "modem_num": modem.getMMNumber(),
               "logger_state": logg.getLoggerState()
           }}
    return appendTimestampsTo(ret)


def everySecond():
    raw_data = getAllData()
    minute_data.append(raw_data)
    if config.HEATER_ENABLE:
        heat.updateHeating(raw_data)
    if config.OLED_ENABLE and config.OLED_RAW:
        oled.updateView(raw_data, mqtt.getConnected(), modem.getMMNumber(), logg.getLoggerState())
    if config.LOGGING_RAW_ENABLE:
        logg.logDataTo("raw", appendTimestampsTo(raw_data))


def everyMinute():
    avg_data = calculateMeanData(minute_data)
    minute_data.clear()
    if config.OLED_ENABLE and not config.OLED_RAW:
        oled.updateView(avg_data, mqtt.getConnected(), modem.getMMNumber(), logg.getLoggerState())
    if config.LOGGING_AVG_ENABLE:
        logg.logDataTo("avg", appendTimestampsTo(avg_data))
    mqtt.publishData(generatePublishingMessage(avg_data))


try:
    # Comment these out if you want to see console logs
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logging.getLogger('raw_logger').propagate = False
    logging.getLogger('avg_logger').propagate = False

    # update Public IP once on startup
    updatePublicIP()

    # Scheduler setup and blocking start call
    sched = BlockingScheduler()
    sched.add_job(everySecond, 'interval', seconds=1)
    sched.add_job(everyMinute, 'interval', minutes=1)
    sched.add_job(updatePublicIP, 'interval', hours=1)
    sched.start()

except KeyboardInterrupt:
    ### Sensor cleanup ###
    print("Cleaning up")
    sched.shutdown()
    modem.stop()
    logg.stop()
    if config.HEATER_ENABLE:
        heat.stop()
    if config.OLED_ENABLE:
        oled.stop()
    if config.OPC_ENABLE:
        opc.stop()
    if config.SHT_ENABLE:
        sht.stop()
    if config.HYT_ENABLE:
        hyt.stop()
    if config.ADC_ENABLE:
        adc.stop()
    print("Cleanup completed")
