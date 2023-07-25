from typing import Dict, Any
import threading
import time
from w1thermsensor import W1ThermSensor
from w1thermsensor.errors import (
    NoSensorFoundError,
    ResetValueError,
    SensorNotReadyError,
    W1ThermSensorError,
    UnsupportedSensorError,
)
import config
import prt
from generic_sensor import SensorBase


class OneWireHandler(SensorBase):
    def __init__(self):
        self.temperature = None
        self.thermocouple_temperature = None
        self.last_temperature_reading = time.time()
        self.request_data = threading.Event()
        self.request_data.set()  # set it for inital measurement

        self.available_sensors = W1ThermSensor.get_available_sensors()
        self.sensor_count = len(self.available_sensors)
        print(f"Detected: {self.sensor_count} Sensor/s on the 1-Wire Bus")
        if self.sensor_count == 0:
            # no need to continue if there is no sensor connected
            return
        
        for sensor in self.available_sensors:
            try:
                print(f"1-Wire Sensor with address: {sensor.id} has temperature: {sensor.get_temperature()}")
            except SensorNotReadyError:
                print(f"1-Wire Sensor with address: {sensor.id}, offline")

        # Set heater sensor id
        if "auto" in config.ONE_WIRE_DS_ID:
            # Autodetect id
            self.sensor = W1ThermSensor()
        else:
            # Use configured id
            self.sensor = W1ThermSensor(sensor_id=config.ONE_WIRE_DS_ID)

        # Set Resolution
        if config.ONE_WIRE_DS_RESOLUTION != 0:
            try:
                self.sensor.set_resolution(config.ONE_WIRE_DS_RESOLUTION)
            except W1ThermSensorError:
                print(f"Failed to change resolution to: {config.ONE_WIRE_DS_RESOLUTION} for sensor: {self.sensor.id}")

        print(f"Using 1-Wire Sensor with ID: {self.sensor.id} and resolution: {self.sensor.get_resolution()} for heater control")
        
        #self.thermocouple_sensor = W1ThermSensor(sensor_id="0d4c0f496ba6")

        self.thread = threading.Thread(target=self._one_wire_worker)
        self.thread.daemon = True
        self.thread.start()

    def _one_wire_worker(self) -> None:
        while True:
            if self.request_data.wait(timeout=0.01):
                try:
                    self.temperature = self.sensor.get_temperature()
                    #self.thermocouple_temperature = self.thermocouple_sensor.get_temperature()
                    self.last_temperature_reading = time.time()
                except (NoSensorFoundError, SensorNotReadyError, ResetValueError):
                    pass
                self.request_data.clear()

    def get_data(self) -> Dict[str, Any]:
        try:
            # if the sensor has not beed read in the last 2 seconds consider it to be disconnected
            if time.time() - self.last_temperature_reading > 6:
                self.request_data.set()
                raise Exception  # DS18B20 did not finish temperature measurement in time.

            temperature = self.temperature
            #thermocouple_temperature = self.thermocouple_temperature
            self.request_data.set()

            # Apply two point calibration
            temperature = self._calibrate(temperature, config.ONE_WIRE_DS_CALI)
            #thermocouple_temperature = self._calibrate(thermocouple_temperature, config.ONE_WIRE_DS_CALI)
            return {"heater_temp": temperature, "air_temp": 0}

        except Exception as e:
            prt.GLOBAL_ENTITY.print_once("Heater Temperature Sensor disconnected", "Heater Temperature Sensor back online")
            return {"heater_temp": None, "air_temp": None}

    def stop(self) -> None:
        pass
