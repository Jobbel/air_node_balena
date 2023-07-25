from typing import Dict
import time
import RPi.GPIO
from simple_pid import PID
import config
import prt
import math


# define custom exceptions describing heater conditions
class MissingDataException(Exception):
    pass


class OverheatingException(Exception):
    pass

class PIDAutoTuner:
    def __init__(self, calibration_temperature) -> None:
        self.calibration_temperature = calibration_temperature
        self.target_temp = self.calibration_temperature
        self.heating = False
        self.peak = 0.
        self.peak_time = 0.
        self.peaks = []
        self.last_pwm = 0.
        self.pwm_samples = []
        self.temp_samples = []

        self.last_power = 0

    def run(self, temp):

        if not self._tuning_in_progress:
            print("Tuning is done, final parameters:")
            self._calc_final_pid()
            Kp, Ki, Kd = self.calc_final_pid()
            print(f"Autotune: final: Kp={Kp} Ki={Ki} Kd={Kd}")

        power = 0
        now = time.time()
        self.temp_samples.append((now, temp))
        # Check if the temperature has crossed the target and
        # enable/disable the heater if so.
        if self.heating and temp >= self.target_temp:
            self.heating = False
            self._check_peaks()
            self.target_temp = self.calibration_temperature - 5.0
        elif not self.heating and temp <= self.target_temp:
            self.heating = True
            self._check_peaks()
            self.target_temp = self.calibration_temperature
        # Check if this temperature is a peak and record it if so
        if self.heating:
            power = 100
            if temp < self.peak:
                self.peak = temp
                self.peak_time = now
        else:
            power = 0
            if temp > self.peak:
                self.peak = temp
                self.peak_time = now

        if power != self.last_power:
            self.pwm_samples.append((now, power))
            self.last_power = power

        return power
    
    def _check_peaks(self):
        print(f"detected peak at: {self.peak}")
        self.peaks.append((self.peak, self.peak_time))
        if self.heating:
            self.peak = 9999999.
        else:
            self.peak = -9999999.
        if len(self.peaks) < 4:
            return
        self._calc_pid(len(self.peaks)-1)

    def _calc_pid(self, pos):
        temp_diff = self.peaks[pos][0] - self.peaks[pos-1][0]
        time_diff = self.peaks[pos][1] - self.peaks[pos-2][1]
        # Use Astrom-Hagglund method to estimate Ku and Tu
        amplitude = .5 * abs(temp_diff)
        Ku = 4. * 100 / (math.pi * amplitude)
        Tu = time_diff
        # Use Ziegler-Nichols method to generate PID parameters
        Ti = 0.5 * Tu
        Td = 0.125 * Tu
        Kp = 0.6 * Ku
        Ki = Kp / Ti
        Kd = Kp * Td
        print(f"Autotune: raw={temp_diff}/{100} Ku={Ku} Tu={Tu}  Kp={Kp} Ki={Ki} Kd={Kd}")
        return Kp, Ki, Kd
    
    def _calc_final_pid(self):
        cycle_times = [(self.peaks[pos][1] - self.peaks[pos-2][1], pos)
                       for pos in range(4, len(self.peaks))]
        midpoint_pos = sorted(cycle_times)[len(cycle_times)//2][1]
        return self._calc_pid(midpoint_pos)
    
    def _tuning_in_progress(self):
        if self.heating or len(self.peaks) < 12:
            return True
        return False
    
    def reset(self):
        pass
        # TODO: abort if exeption happens during tuning


class HeatingController:
    def __init__(self):
        self.heater_power = 0
        self.GPIO = RPi.GPIO
        self.GPIO.setmode(self.GPIO.BOARD)
        self.GPIO.setwarnings(False)
        self.GPIO.setup(config.HEATER_PIN, self.GPIO.OUT)
        self.p = self.GPIO.PWM(config.HEATER_PIN, 50)
        self.p.start(0)

        # Temperature PID
        self.pid_t = PID(20, 0.1, 0, setpoint=config.HEATER_PID_TEMP_SETPOINT, sample_time=None)
        self.pid_t.output_limits = (0, 100)
        #self.pid_t.tunings = config.HEATER_PID_TEMP_TUNING

        self.pid_autotuning_enabled = True
        self.pid_autotuner = PIDAutoTuner(calibration_temperature=45)

    def get_data(self) -> Dict[str, int]:
        return {"heater": self.heater_power}

    def update_heating(self, data: Dict[str, float]) -> None:
        try:
            heater_temp = data['heater_temp']
            #opc_humid = data['opc_humid']
            opc_temp = data['opc_temp']
            outside_humidity = data['sht_humid']
            #outside_temperature = data['sht_temp']
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
            self.heater_power = 0
            self.p.ChangeDutyCycle(self.heater_power)
            self.pid_autotuner.reset()
            # reset pid to avoid integral windup
            self.pid_t.auto_mode = False
            return
        
        if config.HEATER_DEBUG:
            print(f"temp:{heater_temp}, heater:{self.heater_power}, time:{time.time()}")
        
        try:
            if self.pid_autotuning_enabled:
                self.heater_power = self.pid_autotuner.run(temp=heater_temp)
            else:
                self.heater_power = self._run_pid_control(temp=heater_temp, target_temp=35)
        except Exception as e:
            print(e)
            self.heater_power = 0

        self.p.ChangeDutyCycle(self.heater_power)

    def _run_pid_control(self, temp: float, target_temp: float) -> float:
        power = 0
        # Only enable PID if temp not too high
        if temp < target_temp + 5:
            self.pid_t.auto_mode = True
            self.pid_t.setpoint = target_temp
            power = round(self.pid_t(temp), 2)
            if config.HEATER_DEBUG:
                print("Temperature PID: ", [round(x, 2) for x in self.pid_t.components])
        else:
            self.pid_t.auto_mode = False
        return power


    def stop(self) -> None:
        self.p.stop()
        self.GPIO.cleanup()
