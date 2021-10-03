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


class LoggingController(object):
    def __init__(self):
        self.formatter = logging.Formatter('%(message)s')
        logging.raiseExceptions = False
        self.raw_logger = None
        self.avg_logger = None
        self.logger_state = None
        self.q = Queue()

        if config.LOGGING_RAW_ENABLE or config.LOGGING_AVG_ENABLE:
            # if any logging is enabled, make sure directory exists
            os.makedirs(config.LOGGING_DIRECTORY, exist_ok=True)
            # and start logging thread
            self.t = threading.Thread(target=self.loggingWorker)
            self.t.setDaemon(True)
            self.t.start()

    def getLoggerState(self):
        return self.logger_state

    def logDataTo(self, logger_selector, data):
        # Save data and where to log it to in Queue as touple
        self.q.put((logger_selector, data))

    def loggingWorker(self):
        while True:
            if not self.q.empty():
                if os.path.exists(config.LOGGING_DIRECTORY):
                    item = self.q.get()
                    try:
                        self.writelogData(item)
                        self.logger_state = "working" if self.q.empty() else "backlog"
                    except Exception as e:
                        print(e)
                        print(f"Failed to generate {item[0]} logger")
                        self.logger_state = "error"
                        self.resetLoggers()
                        time.sleep(10)
                else:
                    self.logger_state = "wrong path"
                    self.resetLoggers()
                    time.sleep(10)
            time.sleep(0.2)


    def setupMidnightlogger(self, name, log_file, data_header, level=logging.INFO):
        handler = ModifiedTimedRotatingFileHandler(log_file, when='midnight', header=data_header)
        handler.setFormatter(self.formatter)
        handler.suffix = "%Y-%m-%d"
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)
        return logger

    def dictToCSV(self, dict):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(dict.keys()))
        writer.writerow(dict)
        return output.getvalue().rstrip('\n')  # Remove unnecessary newline

    def generateCSVHeaderFromList(self, list):
        ret = ""
        for item in list:
            ret += item
            ret += ","
        return ret.rstrip(",")  # Remove last comma

    def getTimeSinceLastWrite(self, path):
        line = check_output(['tail', '-1', path], stderr=STDOUT, timeout=0.1)
        last_written_timestamp = float(line.decode("utf-8").split(",")[-3])
        return time.time() - last_written_timestamp

    def resetLoggers(self):
        if self.raw_logger is not None:
            self.raw_logger.handlers.pop()
            self.raw_logger = None
        if self.avg_logger is not None:
            self.avg_logger.handlers.pop()
            self.avg_logger = None

    def writelogData(self, item):
        (logger_selector, data) = item

        if logger_selector == "raw":
            file = config.LOGGING_DIRECTORY + config.NODE_ID + "_raw_every_second_data.log"
            if self.raw_logger is None:
                print("Trying to generate raw logger")
                self.raw_logger = self.setupMidnightlogger('raw_logger', file, self.generateCSVHeaderFromList(list(data.keys())))
            self.raw_logger.info(self.dictToCSV(data))

        elif logger_selector == "avg":
            file = config.LOGGING_DIRECTORY + config.NODE_ID + "_avg_every_minute_data.log"
            if self.avg_logger is None:
                print("Trying to generate avg logger")
                self.avg_logger = self.setupMidnightlogger('avg_logger', file, self.generateCSVHeaderFromList(list(data.keys())))
            self.avg_logger.info(self.dictToCSV(data))

        else:
            print("wrong key:", logger_selector, "you cannot select a logger that does not exist")
            raise KeyError

        # now check if we just wrote successfully
        last_write_time = self.getTimeSinceLastWrite(file)
        #print("last write for", logger_selector, round(last_write_time, 2), "seconds ago")
        if last_write_time > 1 and self.q.empty():
            print(f"last {logger_selector} logger entry is too old, checking usb drive")
            raise OSError
        else:
            timeout = 2 if logger_selector == "raw" else 65
            prt.global_entity.printOnce(f"{logger_selector} logger started", f"{logger_selector} logger stopped working", timeout)

    def stop(self):
        self.resetLoggers()
