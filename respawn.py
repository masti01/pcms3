import os
from signal import SIGKILL

proceses = {
    'ircartcounter-pl': 'masti/artnos pl &',
}

for pname in proceses.keys():
    # pidname = f'masti/pid/ircartcounter-pl.pid'
    pidname = f'masti/pid/{pname}.pid'

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

    print(f'Respawning {pidname}')
    os.system(f'{proceses[pidname]}')
