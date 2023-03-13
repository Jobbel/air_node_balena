import socket
import time
import threading
import RPi.GPIO
import config


class InternetWatchdog:
    def __init__(self, interval: int = 60 * 60):
        self.interval = interval
        self.GPIO = RPi.GPIO
        self.GPIO.setmode(self.GPIO.BOARD)
        self.GPIO.setwarnings(False)
        self.GPIO.setup(config.INTERNET_WATCHDOG_MODEM_POWER_PIN, self.GPIO.OUT)
        self.GPIO.output(config.INTERNET_WATCHDOG_MODEM_POWER_PIN, False)
        print(f"Internet watchdog enabled, checking connection every: {self.interval} seconds")
        self.thread = threading.Thread(target=self._watchdog_worker)
        self.thread.daemon = True
        self.thread.start()

    def _watchdog_worker(self) -> None:
        while True:
            time.sleep(self.interval)
            if self._internet_connected():
                continue
            print("No Internet connection found, restarting Modem")
            self._restart_modem()

    def _restart_modem(self) -> None:
        self.GPIO.output(config.INTERNET_WATCHDOG_MODEM_POWER_PIN, True)
        time.sleep(5)
        self.GPIO.output(config.INTERNET_WATCHDOG_MODEM_POWER_PIN, False)

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
