import os
from ast import literal_eval
# This config file tries to get cloud defined environment variable
try:
    # SOFTWARE SETTINGS
    NODE_ID = os.environ['RESIN_DEVICE_NAME_AT_INIT']
    DIGIT_ACCURACY = int(os.environ['DIGIT_ACCURACY'])  # To how many decimal digits should the sensor values be rounded
    PUBLISH_RAW_OPC_AND_ADC = os.environ['PUBLISH_RAW_OPC_AND_ADC'] in 'True'

    # Watchdog settings
    INTERNET_WATCHDOG_ENABLE = os.environ['INTERNET_WATCHDOG_ENABLE'] in 'True'
    INTERNET_WATCHDOG_INTERVAL = int(os.environ['INTERNET_WATCHDOG_INTERVAL'])  # in seconds
    INTERNET_WATCHDOG_MODEM_POWER_PIN = int(os.environ['INTERNET_WATCHDOG_MODEM_POWER_PIN'])  # Pin which can switch modem power

    # Logging settings
    LOGGING_RAW_ENABLE = os.environ['LOGGING_RAW_ENABLE'] in 'True'  # Log sensor data every second
    LOGGING_AVG_ENABLE = os.environ['LOGGING_AVG_ENABLE'] in 'True'  # Log sensor data every minute
    LOGGING_DIRECTORY = os.environ['LOGGING_DIRECTORY']
    LOGGING_RSYNC_ENABLE = os.environ['LOGGING_RSYNC_ENABLE'] in 'True'  # Whether to use rsync to copy files from LOGGING_DIRECTORY to USB Stick regularly
    LOGGING_RSYNC_INTERVAL = int(os.environ['LOGGING_RSYNC_INTERVAL'])  # How ofter to call rsync in seconds
    LOGGING_RSYNC_DEBUG = os.environ['LOGGING_RSYNC_DEBUG'] in 'True'

    # MQTT settings
    MQTT_ENABLE = os.environ['MQTT_ENABLE'] in 'True'
    MQTT_BASE_TOPIC = os.environ['MQTT_BASE_TOPIC']
    MQTT_QOS = int(os.environ['MQTT_QOS'])
    MQTT_SERVER = os.environ['MQTT_SERVER']
    MQTT_PORT = int(os.environ['MQTT_PORT'])
    MQTT_USE_TLS = os.environ['MQTT_USE_TLS'] in 'True'
    MQTT_USER = os.environ['MQTT_USER']
    MQTT_PASS = os.environ['MQTT_PASS']

    # GPS settings
    GPS_POLL_ENABLE = os.environ['GPS_POLL_ENABLE'] in 'True'

    # HARDWARE SETTINGS
    HEATER_ENABLE = os.environ['HEATER_ENABLE'] in 'True'  # This should only be enabled if an opc is used
    HEATER_PIN = int(os.environ['HEATER_PIN'])
    HEATER_DEBUG = os.environ['HEATER_DEBUG'] in 'True'  # Enable heater debug messages
    HEATER_PID_ENABLE = os.environ['HEATER_PID_ENABLE'] in 'True'  # Enable PID controllers if True, use 2 point controller if False
    HEATER_PID_TEMP_TUNING = literal_eval(os.environ.get("HEATER_PID_TEMP_TUNING"))
    HEATER_PID_HUMID_TUNING = literal_eval(os.environ.get("HEATER_PID_HUMID_TUNING"))
    HEATER_PID_TEMP_SETPOINT = int(os.environ['HEATER_PID_TEMP_SETPOINT'])
    HEATER_PID_HUMID_SETPOINT = int(os.environ['HEATER_PID_HUMID_SETPOINT'])

    # Oled settings
    OLED_ENABLE = os.environ['OLED_ENABLE'] in 'True'
    OLED_ADDRESS = int(os.environ['OLED_ADDRESS'], 16)
    OLED_PORT = int(os.environ['OLED_PORT'])
    OLED_RAW = os.environ['OLED_RAW'] in 'True'  # display raw data every second if true or use average data every minute if false

    # SENSOR SETTINGS
    # Note: to use the ADC gas sensors you must have the SHT enabled because the outside temperature is required
    # {"raw_low": 0, "raw_high": 1, "ref_low": 0, "ref_high": 1} disables the two point calibration

    # OPC settings
    OPC_ENABLE = os.environ['OPC_ENABLE'] in 'True'
    OPC_CALI_TEMP = literal_eval(os.environ.get("OPC_CALI_TEMP"))
    OPC_CALI_HUMID = literal_eval(os.environ.get("OPC_CALI_HUMID"))

    # SHT31 settings
    SHT_ENABLE = os.environ['SHT_ENABLE'] in 'True'
    SHT_ADDRESS = int(os.environ['SHT_ADDRESS'], 16)
    SHT_HEATER_ENABLE = os.environ['SHT_HEATER_ENABLE'] in 'True'  # The SHT30 has an internal heater to remove condensation, redo calibration if changed
    SHT_CALI_TEMP = literal_eval(os.environ.get("SHT_CALI_TEMP"))
    SHT_CALI_HUMID = literal_eval(os.environ.get("SHT_CALI_HUMID"))

    # HYT sensor settings
    HYT_ENABLE = os.environ['HYT_ENABLE'] in 'True'
    HYT_ADDRESS = int(os.environ['HYT_ADDRESS'], 16)
    HYT_CALI_TEMP = literal_eval(os.environ.get("HYT_CALI_TEMP"))
    HYT_CALI_HUMID = literal_eval(os.environ.get("HYT_CALI_HUMID"))

    # Gas sensor calibration settings
    ADC_ENABLE = os.environ['ADC_ENABLE'] in 'True'  # this requires SHT to be enabled

    ADC_ADDRESS_A = int(os.environ['ADC_ADDRESS_A'], 16)
    ADC_ADDRESS_B = int(os.environ['ADC_ADDRESS_B'], 16)

    ADC_CALI_CO = literal_eval(os.environ.get("ADC_CALI_CO"))
    ADC_CALI_NO = literal_eval(os.environ.get("ADC_CALI_NO"))
    ADC_CALI_NO2 = literal_eval(os.environ.get("ADC_CALI_NO2"))
    ADC_CALI_O3 = literal_eval(os.environ.get("ADC_CALI_O3"))
except Exception as e:
    print(f"Failed to load cloud config from environment, using default config instead. Error at: {e}")
    from config_cloudless import *
