import csv
import io
import logging
import os
import time
from logging.handlers import TimedRotatingFileHandler
from subprocess import STDOUT, check_output

import prt
import yaml

config = yaml.safe_load(open("config.yml"))

formatter = logging.Formatter('%(message)s')
logging.raiseExceptions = False
raw_logger = None
avg_logger = None


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


def setupMidnightlogger(name, log_file, data_header, level=logging.INFO):
    # handler = ModifiedTimedRotatingFileHandler(log_file, when='M', interval=1, header=data_header)
    handler = ModifiedTimedRotatingFileHandler(log_file, when='midnight', header=data_header)
    handler.setFormatter(formatter)
    handler.suffix = "%Y-%m-%d"
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


def dictToCSV(dict):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(dict.keys()))
    writer.writerow(dict)
    return output.getvalue().rstrip('\n')  # Remove unnecessary newline


def generateCSVHeaderFromList(list):
    ret = ""
    for item in list:
        ret += item
        ret += ","
    return ret.rstrip(",")  # Remove last comma


def getTimeSinceLastWrite(path):
    line = check_output(['tail', '-1', path], stderr=STDOUT, timeout=0.1)
    last_written_timestamp = float(line.decode("utf-8").split(",")[-3])
    return time.time() - last_written_timestamp

def resetLoggers():
    global raw_logger, avg_logger
    if raw_logger is not None:
        raw_logger.handlers.pop()
        raw_logger = None
    if avg_logger is not None:
        avg_logger.handlers.pop()
        avg_logger = None


def logDataTo(logger_selector, data):
    global raw_logger, avg_logger

    # Check if USB Stick is correctly mounted, if not reset loggers
    if os.path.exists(config['logging_directory']) is False:
        prt.global_entity.printOnce("No USB Drive detected, not logging any data",
                                    "USB Drive detected, restarted logging")
        resetLoggers()
    else:
        try:
            if logger_selector == "raw":
                file = config['logging_directory'] + config['node_id'] + "_raw_every_second_data.log"
                if raw_logger is None:
                    print("Trying to generate raw logger")
                    raw_logger = setupMidnightlogger('raw_logger', file, generateCSVHeaderFromList(list(data.keys())))
                raw_logger.info(dictToCSV(data))
                if getTimeSinceLastWrite(file) > 0.5:
                    print("last raw logger entry is too old, checking usb drive")
                    raise OSError
                else:
                    prt.global_entity.printOnce("Raw logger started","Raw logger stopped working")
            elif logger_selector == "avg":
                file = config['logging_directory'] + config['node_id'] + "_avg_every_minute_data.log"
                if avg_logger is None:
                    print("Trying to generate avg logger")
                    avg_logger = setupMidnightlogger('avg_logger', file, generateCSVHeaderFromList(list(data.keys())))
                avg_logger.info(dictToCSV(data))
                if getTimeSinceLastWrite(file) > 0.5:
                    print("last avg logger entry is too old, checking usb drive")
                    raise OSError
                else:
                    prt.global_entity.printOnce("Avg logger started", "Avg logger stopped working", 65)
        except:
            print(f"Failed to generate {logger_selector} logger, checking usb drive")
            resetLoggers()
            os.system("fsck -y /dev/sda1  > /dev/null")
