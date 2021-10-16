#!/bin/bash
cd ~/pw/core || exit
time /home/masti/venvwrapper python3 pwb.py masti/m-sandbox.py -page:"Pomoc:Krok pierwszy - edytowanie" -text:"{{/podstrona}}" -summary:"resetowanie brudnopisu" -always
time /home/masti/venvwrapper python3 pwb.py masti/m-sandbox.py -page:"Pomoc:Krok drugi - formatowanie" -text:"{{/podstrona}}" -summary:"resetowanie brudnopisu" -always
time /home/masti/venvwrapper python3 pwb.py masti/m-sandbox.py -page:"Pomoc:Krok trzeci - linki" -text:"{{/podstrona}}" -summary:"resetowanie brudnopisu" -always
time /home/masti/venvwrapper python3 pwb.py masti/m-sandbox.py -page:"Pomoc:Krok czwarty - grafiki" -text:"{{/podstrona}}" -summary:"resetowanie brudnopisu" -always
time /home/masti/venvwrapper python3 pwb.py masti/m-sandbox.py -page:"Pomoc:Krok piąty - szablony" -text:"{{/podstrona}}" -summary:"resetowanie brudnopisu" -always