#!/bin/bash
cd /home/claude/r56
export NODEATH=1
q() { for c in "$@"; do echo "start $c $(date +%T)" >> sim_progress.txt; python3 simbot.py $c $((RANDOM%90+10)) 4000 400000 1500 >> sim_progress.txt 2>&1; done; }
q warrior priest bard smith &
q mage summoner ranger &
wait
echo ALLDONE >> sim_progress.txt
