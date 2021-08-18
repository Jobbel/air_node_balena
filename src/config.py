# SOFTWARE SETTINGS
NODE_ID = "testnode_balena"
DIGIT_ACCURACY = 2  # To how many decimal digits should the sensor values be rounded

# Logging settings
ENABLE_RAW_LOG = True  # Log sensor data every second
ENABLE_AVG_LOG = True  # Log sensor data every minute
# There has to be a Folder called log_data on the USB Drive
LOGGING_DIRECTORY = "/mnt/storage/log_data/"  # DONT CHANGE THIS without changing logging controller!

# MQTT settings
MQTT_BASE_TOPIC = "airdata"
MQTT_QOS = 2
MQTT_SERVER = "aang.ddnss.de"
MQTT_PORT = 1883
MQTT_USE_TLS = False
MQTT_USER = "***REMOVED***"
MQTT_PASS = "***REMOVED***"


# HARDWARE SETTINGS
HEATER_PIN = 12
HEATER_ENABLE = True  # This should only be enabled if an opc is used
HEATER_DEBUG = False  # Enable heater debug messages
HEATER_PID_ENABLE = True  # Enable PID controllers if True, use 2 point controller if False

# Oled settings
OLED_ADDRESS = 0x3c
OLED_ENABLE = True
OLED_RAW = False  # display raw data every second if true or use average data every minute if false

# SENSOR SETTINGS
# Note: to use the ADC gas sensors you must have the SHT enabled because the outside temperature is required

# OPC settings
OPC_ENABLE = True
OPC_CALI_TEMP = {"raw_low": 0, "raw_high": 100, "ref_low": 0, "ref_high": 100}
OPC_CALI_HUMID = {"raw_low": 0, "raw_high": 100, "ref_low": 0, "ref_high": 100}

# SHT31 settings
SHT_ENABLE = True
SHT_ADDRESS = 0x44
SHT_HEATER_ENABLE = True  # The SHT30 has an internal heater to remove condensation
SHT_CALI_TEMP = {"raw_low": 0, "raw_high": 100, "ref_low": 0, "ref_high": 100}
SHT_CALI_HUMID = {"raw_low": 0, "raw_high": 100, "ref_low": 0, "ref_high": 100}

# HYT sensor settings
HYT_ENABLE = False
HYT_ADDRESS = 0x28
HYT_CALI_TEMP = {"raw_low": 0, "raw_high": 100, "ref_low": 0, "ref_high": 100}
HYT_CALI_HUMID = {"raw_low": 0, "raw_high": 100, "ref_low": 0, "ref_high": 100}

# Gas sensor calibration settings
ADC_ENABLE = True

ADC_ADDRESS_A = 0x48
ADC_ADDRESS_B = 0x48

ADC_CALI_CO = {"w0": 344, "a0": 352, "sens": 0.412, "raw_low": 0, "raw_high": 100, "ref_low": 0, "ref_high": 100}
ADC_CALI_NO = {"w0": 291, "a0": 289, "sens": 0.578, "raw_low": 0, "raw_high": 100, "ref_low": 0, "ref_high": 100}
ADC_CALI_NO2 = {"w0": 230, "a0": 223, "sens": 0.395, "raw_low": 0, "raw_high": 100, "ref_low": 0, "ref_high": 100}
ADC_CALI_O3 = {"w0": 253, "a0": 252, "sens": 0.308, "raw_low": 0, "raw_high": 100, "ref_low": 0, "ref_high": 100}
