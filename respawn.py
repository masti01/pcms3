import os
from signal import SIGKILL, SIGTERM
import psutil


proceses = {
    'ircartcounter-pl': 'masti/artnos pl &',
    'ircartcounter-szl': 'masti/artnos szl &',
    'ircartcounter-csb': 'masti/artnos csb &',
    'ircartcounter-tr': 'masti/artnos tr &',
}

for pname in proceses.keys():

    # get pidfile name
    pidname = f'masti/pid/{pname}.pid'

    try:
        file = f = open(pidname, "r")
        pid = int(file.readline())
        file.close()
    except FileNotFoundError:
        pass

    #print(f'PID found:{pid}')

    if pid in psutil.pids():
        print(f'Process {pname} (PID:{pid}) running. Not respawning')
    else:
        print(f'Respawning {pname}')
        os.system(f'{proceses[pname]}')

        # kill process
        # try:
        #     os.kill(pid, SIGKILL)
        # except ProcessLookupError:
        #     print(f'Process {pid} NOT FOUND')


