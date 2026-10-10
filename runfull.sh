#!/bin/bash
cd /home/claude/r56
export SIM_TARGET=150 SIM_FAR_LEVEL=95
q() { for c in "$@"; do echo "start $c $(date +%T)" >> sim_full.txt; python3 simbot.py $c $((RANDOM%90+10)) 6000 900000 3300 >> sim_full.txt 2>&1; done; }
q warrior mage summoner priest ranger &
q bard smith paladin monk warlock &
wait
echo ALLDONE >> sim_full.txt
