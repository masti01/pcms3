import os
from signal import SIGKILL, SIGTERM
import psutil
from datetime import datetime

proceses = {
    'ircartcounter-pl': 'masti/artnos pl &',
    'ircartcounter-szl': 'masti/artnos szl &',
    'ircartcounter-csb': 'masti/artnos csb &',
    'ircartcounter-tr': 'masti/artnos tr &',
}


with open("masti/pid/respawn.log", "a") as logfile:

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
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {pname} (PID:{pid}) is dead... respawning...')
            logfile.write(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {pname} (PID:{pid}) is dead... respawning...')
            os.system(f'{proceses[pname]}')

            # kill process
            # try:
            #     os.kill(pid, SIGKILL)
            # except ProcessLookupError:
            #     print(f'Process {pid} NOT FOUND')


