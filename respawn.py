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

# enable logging
with open("masti/pid/respawn.log", "a") as logfile:

    # run for all processes
    for pname in proceses.keys():

        # get pidfile name
        pidname = f'masti/pid/{pname}.pid'

        try:
            file = open(pidname, "r")
            pid = int(file.readline())
            file.close()
        except FileNotFoundError:
            pid = None

        # check if proper process still running
        if pid not in psutil.pids():
            print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {pname} (PID:{pid}) is dead... respawning...')
            logfile.write(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {pname} (PID:{pid}) is dead... respawning...\n')
            os.system(f'{proceses[pname]}')



