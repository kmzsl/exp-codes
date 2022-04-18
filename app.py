import os
import sys

lib_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(lib_path + '/libs')

from StorageHttp import StorageHttp
from StorageMemory import StorageMemory
from StorageLog import StorageLog

if __name__ == '__main__':
    app = StorageHttp()
    app.set_property('storage', StorageMemory())
    app.set_property('log', StorageLog())
    app.event_loop()