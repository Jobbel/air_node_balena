import time
import threading

# This variable is used to share the same instance of OncePrinter across all modules.
# This way only one msg list and only one thread are created
global_entity = None

# The purpose of this thread is to turn frequently occuring identical print statements into
# a start message printed at the first time calling the printOnce method and an end message printed if the last time
# a printOnce message was called is farther in the past then the timeout. This keeps the log files readable
# this: print("modem error")
# modem error
# modem error
# modem error
# modem error
# ...
# gets turned into :prt.global_entity.printOnce("modem error started", "modem error ended")
# modem error started
# modem error ended

class OncePrinter(object):
    def __init__(self):
        self.msgs = {}
        self.t = threading.Thread(target=self.handlePrints)
        self.t.setDaemon(True)
        self.t.start()

    def handlePrints(self):
        # Every second this checks if errors stopped occurring and prints the end message
        while True:
            for msg in list(self.msgs.keys()):
                if time.time() - self.msgs[msg]['time'] > int(self.msgs[msg]['timeout']):
                    if self.msgs[msg]["end"] is not False:
                        print(self.msgs[msg]["end"])
                    del self.msgs[msg]
            time.sleep(1)


    def printOnce(self, msg, end_msg, timeout=2):
        if msg not in self.msgs:
            print(msg)
        self.msgs[msg] = {"time": time.time(), "end": end_msg, "timeout": timeout}
