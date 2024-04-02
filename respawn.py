import os
from signal import SIGKILL, SIGTERM
import psutil
from datetime import datetime

import pywikibot
from pywikibot import config

proceses = {
    'ircartcounter-pl': 'masti/artnos pl &',
    'ircartcounter-szl': 'masti/artnos szl &',
    'ircartcounter-csb': 'masti/artnos csb &',
    'ircartcounter-tr': 'masti/artnos tr &',
}


def main(*args):
    local_args = pywikibot.handle_args(args)
    for arg in local_args:
        if arg ==  '-force':
            force = True
        else:
            force = False

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
                logfile.write(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {pname} (File:{pidname} NOT FOUND\n')
                pid = None

            if force:
                print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {pname} (PID:{pid}) killing...')
                logfile.write(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {pname} (PID:{pid}) killing...\n')
                os.system(f'kill -9 {pid}')

            # check if proper process still running
            if pid not in psutil.pids():
                print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {pname} (PID:{pid}) is dead... respawning...')
                logfile.write(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {pname} (PID:{pid}) is dead... respawning...\n')
                os.system(f'{proceses[pname]}')

if __name__ == '__main__':
    main()