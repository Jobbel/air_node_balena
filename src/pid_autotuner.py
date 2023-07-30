import time
import math

class PIDAutoTuner:
    def __init__(self, calibration_temperature) -> None:
        self.calibration_temperature = calibration_temperature
        self._param_init()

    def _param_init(self):
        self.target_temp = self.calibration_temperature
        self.heating = False
        self.peak = 0.
        self.peak_time = 0.
        self.peaks = []
        self.last_pwm = 0.
        self.pwm_samples = []
        self.temp_samples = []
        self.last_power = 0
        self.tuning_completed = False
    
    def get_target_temp(self) -> int:
        return self.target_temp

    def run(self, current_temp):
        power = 0
        if self.tuning_completed:
            return power
        
        now = time.time()
        self.temp_samples.append((now, current_temp))
        if self.heating and current_temp >= self.target_temp:
            self.heating = False
            self._check_peaks()
            self.target_temp = self.calibration_temperature - 3.5
        elif not self.heating and current_temp <= self.target_temp:
            self.heating = True
            self._check_peaks()
            self.target_temp = self.calibration_temperature
        # Check if this temperature is a peak and record it if so
        if self.heating:
            power = 100
            if current_temp < self.peak:
                self.peak = current_temp
                self.peak_time = now
        else:
            power = 0
            if current_temp > self.peak:
                self.peak = current_temp
                self.peak_time = now

        # If commended power changed sample it
        if power != self.last_power:
            self.pwm_samples.append((now, power))
            self.last_power = power

        if not self.heating and len(self.peaks) >= 12:
            Kp, Ki, Kd = self._calc_final_pid()
            print(f"Heater PID autotuning is done, final parameters: Kp={Kp} Ki={Ki} Kd={Kd}")
            self.tuning_completed = True
            self.target_temp = 0

        return power
    
    def _check_peaks(self):
        if len(self.peaks) == 0:
            print(f"Starting Heater PID Autotuning at calibration temperature:{self.calibration_temperature}")
        print(f"detected peak at:{self.peak}, peak:{len(self.peaks) + 1}/12")
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
        # Use Ziegler-Nichols method to generate PID or PI parameters
        if False:
            Ti = 0.5 * Tu
            Td = 0.125 * Tu
            Kp = 0.6 * Ku
            Ki = Kp / Ti
            Kd = Kp * Td
        else:
            Ti = 0.8 * Tu
            Kp = 0.4 * Ku
            Ki = Kp / Ti
            Kd = 0
        print(f"Autotune PID: raw={temp_diff}/{100} Ku={Ku} Tu={Tu}  Kp={Kp} Ki={Ki} Kd={Kd}")
        return Kp, Ki, Kd
    
    def _calc_final_pid(self):
        cycle_times = [(self.peaks[pos][1] - self.peaks[pos-2][1], pos)
                       for pos in range(4, len(self.peaks))]
        midpoint_pos = sorted(cycle_times)[len(cycle_times)//2][1]
        return self._calc_pid(midpoint_pos)
    
    def reset(self):
        self._param_init()
