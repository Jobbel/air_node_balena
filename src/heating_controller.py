from typing import Dict
import time
import RPi.GPIO
from simple_pid import PID
import config
import prt
import numpy as np
from pid_autotuner import PIDAutoTuner


# define custom exceptions describing heater conditions
class MissingDataException(Exception):
    pass


class OverheatingException(Exception):
    pass


class HeatingController:
    def __init__(self):
        self.heater_power = 0
        self.target_temp = 0
        self.GPIO = RPi.GPIO
        self.GPIO.setmode(self.GPIO.BOARD)
        self.GPIO.setwarnings(False)
        self.GPIO.setup(config.HEATER_PIN, self.GPIO.OUT)
        self.p = self.GPIO.PWM(config.HEATER_PIN, 50)
        self.p.start(0)
        # Temperature PID
        self.pid_t = PID(20, 0.1, 0, setpoint=-100, sample_time=None)
        self.pid_t.output_limits = (0, int(np.clip(config.HEATER_MAX_POWER, 5, 100)))  # allow 5% to 100% power limits
        self.pid_t.tunings = config.HEATER_PID_TEMP_TUNING

        self.pid_autotuning_enabled = config.HEATER_PID_AUTOTUNER_ENABLE
        self.pid_autotuner = PIDAutoTuner(
            calibration_temperature=config.HEATER_PID_AUTOTUNER_CALIBRATION_TEMPERATURE,
            relay_hysteresis_delta=config.HEATER_PID_AUTOTUNER_RELAY_HYSTERESIS_DELTA,
        )
        
    def get_data(self) -> Dict[str, int]:
        return {"heater": self.heater_power, "heater_set": self.target_temp}

    def update_heating(self, data: Dict[str, float]) -> None:
        heater_temp = data['heater_temp']
        outside_humidity = data['sht_humid']
        opc_temp = data['opc_temp']
        #outside_temperature = data['sht_temp']
        #opc_humid = data['opc_humid']

        try:
            # if ds temp sensor or sht has a fault, dont heat
            if heater_temp is None or outside_humidity is None or opc_temp is None:
                prt.GLOBAL_ENTITY.print_once("Missing sensor data, disabling heater", "Heater back online")
                raise MissingDataException
            # if heater temperature is too high dont continue heating
            if heater_temp > 55:
                prt.GLOBAL_ENTITY.print_once("Overheating, disabling heater", "Cooled down, Heater back online")
                raise OverheatingException
            # if opc temperature is too high dont continue heating
            if opc_temp > 55:
                prt.GLOBAL_ENTITY.print_once("OPC overheating, disabling heater", "OPC cooled down, Heater back online")
                raise OverheatingException
        except (MissingDataException, OverheatingException):
            self.target_temp = -100
            self.heater_power = 0
            self.p.ChangeDutyCycle(self.heater_power)
            self.pid_autotuner.reset()
            # reset pid to avoid integral windup
            self.pid_t.auto_mode = False
            return

        if config.HEATER_DEBUG:
            print(f"temp:{heater_temp}, heater_target:{self.target_temp}, heater_power:{self.heater_power}, outside_humidity:{outside_humidity}")
        
        try:
            if self.pid_autotuning_enabled:
                self.target_temp = self.pid_autotuner.get_target_temp()
                self.heater_power = self.pid_autotuner.run(current_temp=heater_temp)
            else:
                self.target_temp = self._calculate_dehumidification_temperature(outside_humidity=outside_humidity)
                self.heater_power = self._run_pid_control(current_temp=heater_temp, target_temp=self.target_temp)
        except Exception as e:
            prt.GLOBAL_ENTITY.print_once(f"Heater fault, dump: {e}", "Heater fault stopped, dump: {e}")
            self.heater_power = 0

        self.p.ChangeDutyCycle(self.heater_power)

    def _calculate_dehumidification_temperature(self, outside_humidity: float) -> float:
        # constrain HEATER_MIN_TEMP to avoid too high temperatures
        setpoint_temperature = int(np.clip(config.HEATER_MIN_TEMP, -100, 22))
        if outside_humidity >= 50:
            # Use Setpoint Temp Polynomial
            setpoint_temperature = 0.0084 * outside_humidity * outside_humidity - 0.73 * outside_humidity + 37.653
            # Constrain to 0 to 50 °C range
            setpoint_temperature = round(np.clip(setpoint_temperature, 0, 50), 1)
        return setpoint_temperature

    def _run_pid_control(self, current_temp: float, target_temp: float) -> float:
        power = 0
        # Only enable PID if temp not too high
        if current_temp < target_temp + 5:
            self.pid_t.auto_mode = True
            self.pid_t.setpoint = target_temp
            power = round(self.pid_t(current_temp), 2)
            if config.HEATER_DEBUG:
                print("Temperature PID: ", [round(x, 2) for x in self.pid_t.components])
        else:
            self.pid_t.auto_mode = False
        return power


    def stop(self) -> None:
        self.p.ChangeDutyCycle(0)
        self.p.stop()
        self.GPIO.cleanup()
