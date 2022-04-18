import time as t
import os
import sys


class StorageLog():
    def __init__(self):
        self.file = 'storage.log'
        self.path = '/tmp'
        self.fullname = f"{self.path}/{self.file}"
        self._create_log()

    def _create_log(self):
        if not os.path.exists(self.fullname):
            if os.access(self.path, os.W_OK):
                self._open_log()
            else:
                print("Can`t create log file")
                sys.exit()
        else:
            self._open_log()

    def _open_log(self):
        self.fh = open(self.fullname, 'a')

    def write(self, type, message):
        current_time = t.strftime("%m/%d/%Y %H:%M:%S", t.localtime())
        self.fh.write(f"[{current_time}] [{type}] {message}\n")
        self.fh.flush()
