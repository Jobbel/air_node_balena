from typing import Dict, List, Tuple, Any
import csv
import io
import logging
import os
import threading
import time
from logging.handlers import TimedRotatingFileHandler
from subprocess import STDOUT, check_output
from multiprocessing import Queue
import config
import prt


# Overwriting some parts of the TimedRotatingFileHandler to add a CSV header to every file
class ModifiedTimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename, when='h', interval=1, backupCount=0, encoding=None, delay=False, utc=False,
                 atTime=None, header=''):
        self.header = header
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime)

    def _open(self):
        stream = super()._open()
        if self.header and stream.tell() == 0:
            stream.write(self.header + self.terminator)
            stream.flush()
        return stream


class LoggingController:
    def __init__(self):
        self.formatter = logging.Formatter('%(message)s')
        logging.raiseExceptions = False
        self.raw_logger = None
        self.avg_logger = None
        self.logger_state = "off"
        self.data_queue = Queue()

        if config.LOGGING_RAW_ENABLE or config.LOGGING_AVG_ENABLE:
            # if any logging is enabled, make sure directory exists
            os.makedirs(config.LOGGING_DIRECTORY, exist_ok=True)
            # and start logging thread
            self.thread = threading.Thread(target=self._logging_worker)
            self.thread.daemon = True
            self.thread.start()

    def get_logger_state(self) -> str:
        return self.logger_state

    def log_data_to(self, logger_selector: str, data: Dict[str, Any]) -> None:
        # Save data and where to log it to in Queue as tuple
        self.data_queue.put((logger_selector, data))

    def _logging_worker(self) -> None:
        while True:
            time.sleep(0.2)
            if self.data_queue.empty():
                continue
            if os.path.exists(config.LOGGING_DIRECTORY):
                item = self.data_queue.get()
                try:
                    self._write_log_data(item)
                    self.logger_state = "working" if self.data_queue.empty() else "backlog"
                except Exception as e:
                    print(f"Failed to run {item[0]} logger, dump {e}")
                    self.logger_state = "error"
                    self._reset_loggers()
                    time.sleep(10)
            else:
                self.logger_state = "wrong path"
                self._reset_loggers()
                time.sleep(10)

    def _setup_midnightlogger(self, name, log_file, data_header, level=logging.INFO):
        handler = ModifiedTimedRotatingFileHandler(log_file, when='midnight', header=data_header)
        handler.setFormatter(self.formatter)
        handler.suffix = "%Y-%m-%d"
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)
        return logger

    def _dict_to_csv(self, data: Dict[str, Any]) -> str:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(data.keys()))
        writer.writerow(data)
        return output.getvalue().rstrip('\n')  # Remove unnecessary newline

    def _generate_csv_header_from_list(self, data: List) -> str:
        ret = ""
        for item in data:
            ret += item
            ret += ","
        return ret.rstrip(",")  # Remove last comma

    def _get_time_since_last_write(self, path: str) -> float:
        line = check_output(['tail', '-1', path], stderr=STDOUT, timeout=0.5)
        last_written_timestamp = float(line.decode("utf-8").split(",")[-3])
        return time.time() - last_written_timestamp

    def _reset_loggers(self) -> None:
        if self.raw_logger is not None:
            self.raw_logger.handlers.pop()
            self.raw_logger = None
        if self.avg_logger is not None:
            self.avg_logger.handlers.pop()
            self.avg_logger = None

    def _write_log_data(self, item: Tuple[str, Dict[str, Any]]) -> None:
        (logger_selector, data) = item

        if logger_selector == "raw":
            file = config.LOGGING_DIRECTORY + config.NODE_ID + "_raw_every_second_data.log"
            if self.raw_logger is None:
                print("Trying to generate raw logger")
                self.raw_logger = self._setup_midnightlogger('raw_logger', file,
                                                             self._generate_csv_header_from_list(list(data.keys())))
            self.raw_logger.info(self._dict_to_csv(data))

        elif logger_selector == "avg":
            file = config.LOGGING_DIRECTORY + config.NODE_ID + "_avg_every_minute_data.log"
            if self.avg_logger is None:
                print("Trying to generate avg logger")
                self.avg_logger = self._setup_midnightlogger('avg_logger', file,
                                                             self._generate_csv_header_from_list(list(data.keys())))
            self.avg_logger.info(self._dict_to_csv(data))

        else:
            print("wrong key:", logger_selector, "you cannot select a logger that does not exist")
            raise KeyError

        # now check if we just wrote successfully
        last_write_time = self._get_time_since_last_write(file)
        # print("last write for", logger_selector, round(last_write_time, 2), "seconds ago")
        if last_write_time > 1 and self.data_queue.empty():
            print(f"last {logger_selector} logger entry is too old, checking usb drive")
            raise OSError
        timeout = 2 if logger_selector == "raw" else 65
        prt.GLOBAL_ENTITY.print_once(f"{logger_selector} logger started",
                                     f"{logger_selector} logger stopped working", timeout)

    def stop(self) -> None:
        self._reset_loggers()
