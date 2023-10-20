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
        self.get_data_called = False

        self.available_sensors = W1ThermSensor.get_available_sensors()
        self.sensor_count = len(self.available_sensors)
        print(f"Detected: {self.sensor_count} Sensor/s on the 1-Wire Bus")

        # TODO: remove this for production
        self.enable_thermocouple = self.sensor_count > 1

        if self.sensor_count == 0:
            # no need to continue if there is no sensor connected
            print("No heater temperature sensor detected, please check the connection")
            return
        
        for sensor in self.available_sensors:
            try:
                print(f"1-Wire Sensor with address: {sensor.id} has temperature: {sensor.get_temperature()}")
            except Exception:
                print(f"1-Wire Sensor with address: {sensor.id}, offline")

        # Set heater sensor id
        if "auto" in config.ONE_WIRE_DS_ID:
            # Autodetect id
            self.sensor = W1ThermSensor()
        else:
            # Use configured id
            # TODO: check if configured id is actually connected an in available_sensors
            self.sensor = W1ThermSensor(sensor_id=config.ONE_WIRE_DS_ID)

        # Set Resolution
        if config.ONE_WIRE_DS_RESOLUTION != 0:
            try:
                self.sensor.set_resolution(config.ONE_WIRE_DS_RESOLUTION)
            except W1ThermSensorError:
                print(f"Failed to change resolution to: {config.ONE_WIRE_DS_RESOLUTION} for sensor: {self.sensor.id}")

        print(f"Using 1-Wire Sensor with ID: {self.sensor.id} and resolution: {self.sensor.get_resolution()} bit for heater control")
        
        if self.enable_thermocouple:
            self.thermocouple_sensor = W1ThermSensor(sensor_id="0d4c0f496ba6")
            print("Using thermocouple temperature sensor")

        self.thread = threading.Thread(target=self._one_wire_worker)
        self.thread.daemon = True
        self.thread.start()

    def _one_wire_worker(self) -> None:
        while True:
            if self.request_data.wait(timeout=0.01):
                try:
                    self.temperature = self.sensor.get_temperature()
                    self.last_temperature_reading = time.time()
                    if self.enable_thermocouple:
                        self.thermocouple_temperature = self.thermocouple_sensor.get_temperature()
                    self.request_data.clear()
                except (NoSensorFoundError, SensorNotReadyError, ResetValueError):
                    time.sleep(0.5)

    def get_data(self) -> Dict[str, Any]:
        try:
            # if the sensor has not been read in the last 3 seconds consider it to be disconnected
            if time.time() - self.last_temperature_reading > 6 and self.get_data_called:
                self.request_data.set()
                raise Exception  # DS18B20 did not finish temperature measurement in time.
            self.get_data_called = True

            temperature = self.temperature
            if self.enable_thermocouple:
                thermocouple_temperature = self.thermocouple_temperature
            self.request_data.set()

            # Apply two point calibration
            temperature = self._calibrate(temperature, config.ONE_WIRE_DS_CALI)
            if self.enable_thermocouple:
                thermocouple_temperature = self._calibrate(thermocouple_temperature, config.ONE_WIRE_DS_CALI)
                return {"heater_temp": temperature, "air_temp": thermocouple_temperature}
            return {"heater_temp": temperature}

        except Exception as e:
            prt.GLOBAL_ENTITY.print_once(f"Heater Temperature Sensor disconnected, dump: {e}", f"Heater Temperature Sensor back online, dump: {e}")
            if self.enable_thermocouple:
                return {"heater_temp": None, "air_temp": None}
            return {"heater_temp": None}

    def stop(self) -> None:
        pass
