import RPi.GPIO
import prt
from simple_pid import PID


class HeatingController(object):
    def __init__(self, config):
        self.heater_pin = config['heater_pin']
        self.pid_enable = config['heater_pid_enable']
        self.debug_enable = config['heater_debug']
        self.heater_power = 0
        self.GPIO = RPi.GPIO
        self.GPIO.setmode(self.GPIO.BOARD)
        self.GPIO.setwarnings(False)
        self.GPIO.setup(self.heater_pin, self.GPIO.OUT)
        self.p = self.GPIO.PWM(self.heater_pin, 50)
        self.p.start(0)
        # Humidity PID is reversed, heating -> humidity drops
        self.pid_h = PID(-20, -0.02, -0, setpoint=50, sample_time=None)
        self.pid_h.output_limits = (0, 100)
        # Temperature PID is normal, heating -> temperature rises
        self.pid_t = PID(20, 0.02, 0, setpoint=15, sample_time=None)
        self.pid_t.output_limits = (0, 100)

    def updateHeating(self, data):
        try:
            inside_humidity = data['opc_humid']
            inside_temperature = data['opc_temp']
            outside_humidity = data['hyt_humid']
            outside_temperature = data['hyt_temp']
            # if opc has a fault, dont heat
            if inside_temperature == 0.00 and inside_humidity == 0.00:
                raise KeyError
        except KeyError:
            self.heater_power = 0
            self.p.ChangeDutyCycle(self.heater_power)
            prt.global_entity.printOnce("Missing sensor data, disabling heater", "Heater back online")
            return

        if self.debug_enable is True:
            print(f"temp:{inside_temperature}, humid:{inside_humidity}, heater:{self.heater_power}")

        # Temp should be kept above 15 degrees, humidity below 50%
        if self.pid_enable is False:
            if inside_humidity > 50 or inside_temperature < 15:
                self.heater_power = 100
            elif inside_humidity < 45 and inside_temperature > 20:
                self.heater_power = 0
        else:
            # Humidity PID
            if inside_humidity > 45:
                self.pid_h.auto_mode = True
                pid_h_out = round(self.pid_h(inside_humidity), 2)
                if self.debug_enable is True:
                    print("Humidity PID:    ", [round(x, 2) for x in self.pid_h.components])
            else:
                self.pid_h.auto_mode = False
                pid_h_out = 0
            # Temperature PID
            if inside_temperature < 20:
                self.pid_t.auto_mode = True
                pid_t_out = round(self.pid_t(inside_temperature), 2)
                if self.debug_enable is True:
                    print("Temperature PID: ", [round(x, 2) for x in self.pid_t.components])
            else:
                self.pid_t.auto_mode = False
                pid_t_out = 0

            # Use max output from both PIDs
            self.heater_power = max(pid_h_out, pid_t_out)

        self.p.ChangeDutyCycle(self.heater_power)

    def getData(self):
        return {"heater": self.heater_power}

    def stop(self):
        self.p.stop()
        self.GPIO.cleanup()
