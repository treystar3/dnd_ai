#!/bin/bash
cd /home/claude/r56
export SIM_TARGET=150 SIM_FAR_LEVEL=95
q() { for p in "$@"; do c=${p%:*}; s=${p#*:}; echo "start $c $s $(date +%T)" >> sim_full2.txt; python3 simbot.py $c $s 6000 900000 3300 >> sim_full2.txt 2>&1; done; }
q warrior:42 mage:66 summoner:25 priest:33 ranger:46 &
q bard:68 smith:86 paladin:10 monk:21 warlock:92 &
wait
echo ALLDONE >> sim_full2.txt
