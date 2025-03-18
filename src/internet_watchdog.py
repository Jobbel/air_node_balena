import socket
import time
import threading
import RPi.GPIO
import config
from typing import Type
from modem_handler import ModemHandler
import subprocess

class InternetWatchdog:
    def __init__(self, interval: int = 60 * 60, modem_handler_instance: Type[ModemHandler] = None):
        self.interval = interval
        self.modem_handler_instance = modem_handler_instance
        self.error_counter = 0
        self.GPIO = RPi.GPIO
        self.GPIO.setmode(self.GPIO.BOARD)
        self.GPIO.setwarnings(False)
        self.GPIO.setup(config.INTERNET_WATCHDOG_MODEM_POWER_PIN, self.GPIO.OUT)
        self.GPIO.output(config.INTERNET_WATCHDOG_MODEM_POWER_PIN, False)
        print(f"Internet watchdog enabled, checking connection every: {self.interval} seconds")
        self.thread = threading.Thread(target=self._watchdog_worker)
        self.thread.daemon = True
        self.thread.start()

    def get_error_count(self) -> int:
        return self.error_counter

    def _watchdog_worker(self) -> None:
        while True:
            time.sleep(self.interval)
            # TODO: only check modem handler if gps poll is on to avoid modem restat loop
            if self._internet_connected() and self.modem_handler_instance.get_mm_number() != -1:
                self.error_counter = 0
                continue
            self.error_counter += 1
            print(f"No Internet connection / Modem found, restarting Modem. Counter:{self.error_counter}")
            if self._reset_modem():
                continue
            self._restart_modem()

    def _restart_modem(self) -> None:
        self.GPIO.output(config.INTERNET_WATCHDOG_MODEM_POWER_PIN, True)
        time.sleep(5)
        self.GPIO.output(config.INTERNET_WATCHDOG_MODEM_POWER_PIN, False)

    def _reset_modem(self) -> bool:
        try:
            modem_number = self.modem_handler_instance.get_mm_number()
            if modem_number == -1:
                print("No Modem Found. cannot reset")
                return False
            print(f"Resetting modem {modem_number}")
            result = subprocess.run(
                ["mmcli", "-m", str(modem_number), "--reset"],
                capture_output=True,
                text=True,
                check=True
            )
            print("Modem reset successful:", result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            print("Error resetting modem:", e.stderr)
            return False

    # Adopted from: https://stackoverflow.com/questions/3764291
    def _internet_connected(self, host: str = "1.1.1.1", port: int = 53, timeout: int = 10) -> bool:
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except socket.error:
            return False


if __name__ == "__main__":
    wd = InternetWatchdog(10)
    while True:
        time.sleep(1)
