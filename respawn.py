import os
from os import kill
from os import getpid
from signal import SIGKILL


pidname = f'masti/pid/ircartcounter-pl.pid'

try:
    file = f = open(pidname, "r")
    pid = int(file.readline())
    file.close()
except FileNotFoundError:
    pass

print(f'PID found:{pid}')
try:
    os.kill(pid, SIGKILL)
except ProcessLookupError:
    print(f'Process {pid} NOT FOUND')
