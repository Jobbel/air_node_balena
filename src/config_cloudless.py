# SOFTWARE SETTINGS
NODE_ID = "testnode"
DIGIT_ACCURACY = 2  # To how many decimal digits should the sensor values be rounded
PUBLISH_RAW_OPC_AND_ADC = True

# Watchdog settings
INTERNET_WATCHDOG_ENABLE = True
INTERNET_WATCHDOG_INTERVAL = 900  # in seconds
INTERNET_WATCHDOG_MODEM_POWER_PIN = 11  # Pin which can switch modem power

# Logging settings
LOGGING_RAW_ENABLE = True  # Log sensor data every second
LOGGING_AVG_ENABLE = True  # Log sensor data every minute
LOGGING_DIRECTORY = "/data/log_data/"  # /data/log_data/ for persistent storage on SD, /mnt/storage for USB Drive
LOGGING_RSYNC_ENABLE = True  # Whether to use rsync to copy files from LOGGING_DIRECTORY to USB Stick regularly
LOGGING_RSYNC_INTERVAL = 600  # in seconds
LOGGING_RSYNC_DEBUG = False

# MQTT settings
MQTT_ENABLE = True
MQTT_BASE_TOPIC = "airdata"
MQTT_QOS = 2
MQTT_SERVER = "aang.ddnss.de"
MQTT_PORT = 1883
MQTT_USE_TLS = False
MQTT_USER = ""
MQTT_PASS = ""

# GPS settings
GPS_POLL_ENABLE = True

# HARDWARE SETTINGS
HEATER_ENABLE = True  # This should only be enabled if an opc is used
HEATER_PIN = 12
HEATER_DEBUG = False  # Enable heater debug messages
HEATER_PID_ENABLE = True  # Enable PID controllers if True, use 2 point controller if False
HEATER_PID_TEMP_TUNING = (20, 0.02, 0)  # Has to be positive to counter falling temperature
HEATER_PID_HUMID_TUNING = (-20, -0.02, -0)  # Has to be negative to counter rising humidity
HEATER_PID_TEMP_SETPOINT = 15
HEATER_PID_HUMID_SETPOINT = 50

# Oled settings
OLED_ENABLE = True
OLED_ADDRESS = 0x3c
OLED_PORT = 11  # pi4 use port 6, pi3 use port 11 and dtoverlay: "vc4-fkms-v3d","i2c-gpio,i2c_gpio_sda=22,i2c_gpio_scl=23"
OLED_RAW = True  # display raw data every second if true or use average data every minute if false

# SENSOR SETTINGS
# Note: to use the ADC gas sensors you must have the SHT enabled because the outside temperature is required
# {"raw_low": 0, "raw_high": 1, "ref_low": 0, "ref_high": 1} disables the two point calibration

# OPC settings
OPC_ENABLE = True
OPC_CALI_TEMP = {"raw_low": 0, "raw_high": 1, "ref_low": 0, "ref_high": 1}
OPC_CALI_HUMID = {"raw_low": 0, "raw_high": 1, "ref_low": 0, "ref_high": 1}

# SHT31 settings
SHT_ENABLE = True
SHT_ADDRESS = 0x44
SHT_HEATER_ENABLE = False  # The SHT30 has an internal heater to remove condensation, redo calibration if changed
SHT_CALI_TEMP = {"raw_low": 0, "raw_high": 1, "ref_low": 0, "ref_high": 1}
SHT_CALI_HUMID = {"raw_low": 0, "raw_high": 1, "ref_low": 0, "ref_high": 1}

# ONE WIRE settings (DS18B20 on heater)
ONE_WIRE_ENABLE = True  # Has to be enabled and connected if heater control is used
ONE_WIRE_DS_ID = "auto"  # Address string like 01145c262cc5 if multiple sensors are used, use "auto" to autodetect
ONE_WIRE_DS_RESOLUTION = 12 # 12bit -> 800ms, 11bit -> 400ms, 10 bit -> 200ms, 9bit -> 100ms conversion time, 0 to use default
ONE_WIRE_DS_CALI = {"raw_low": 0, "raw_high": 1, "ref_low": 0, "ref_high": 1}

# HYT sensor settings
HYT_ENABLE = False
HYT_ADDRESS = 0x28
HYT_CALI_TEMP = {"raw_low": 0, "raw_high": 1, "ref_low": 0, "ref_high": 1}
HYT_CALI_HUMID = {"raw_low": 0, "raw_high": 1, "ref_low": 0, "ref_high": 1}

# Gas sensor calibration settings
ADC_ENABLE = True # this requires SHT to be enabled because it uses the outside temperature

ADC_ADDRESS_A = 0x48
ADC_ADDRESS_B = 0x49

ADC_CALI_CO = {"w0": 344, "a0": 352, "sens": 0.412, "raw_low": 0, "raw_high": 1, "ref_low": 0, "ref_high": 1}
ADC_CALI_NO = {"w0": 291, "a0": 289, "sens": 0.578, "raw_low": 0, "raw_high": 1, "ref_low": 0, "ref_high": 1}
ADC_CALI_NO2 = {"w0": 230, "a0": 223, "sens": 0.395, "raw_low": 0, "raw_high": 1, "ref_low": 0, "ref_high": 1}
ADC_CALI_O3 = {"w0": 253, "a0": 252, "sens": 0.308, "raw_low": 0, "raw_high": 1, "ref_low": 0, "ref_high": 1}
