#!/bin/bash
# I3: run all validation cases, 4 serial cases at a time, longest first.
# Waits for AC power before starting (as in I2). Log: cases/runs/i3_run.log
cd "$(dirname "$0")/.." || exit 1
LOG=cases/runs/i3_run.log
until [ "$(cat /sys/class/power_supply/AC1/online 2>/dev/null)" = "1" ]; do echo "$(date +%T) waiting for AC" >> $LOG; sleep 30; done
CASES="forwardStep/hisa_dx160 expansion/hisa_A_n200 wedge/hisa_A_n200 wedge/hisa_B_n200
forwardStep/rcf_dx160 wedge/rcf_A_n200 wedge/rcf_B_n200 expansion/rcf_A_n200 forwardStep/hisa_dx80
expansion/hisa_A_n100 wedge/hisa_A_n100 wedge/hisa_B_n100 expansion/rcf_A_n100 wedge/rcf_A_n100 wedge/rcf_B_n100
forwardStep/rcf_dx80 sod/hisa_N800 sod/rcf_N1600 expansion/hisa_A_n50 wedge/hisa_A_n50 wedge/hisa_B_n50
expansion/rcf_A_n50 wedge/rcf_A_n50 wedge/rcf_B_n50 forwardStep/rcf_dx40 sod/hisa_N400 sod/hisa_N200 sod/hisa_N100
sod/rcf_N800 sod/rcf_N400 sod/rcf_N200 sod/rcf_N100"
echo "$(date -Is) start $(git rev-parse --short HEAD)" >> $LOG
echo $CASES | tr ' ' '\n' | xargs -P 4 -I{} bash -c 'cases/validation/{}/Allrun; echo "$(date +%T) {} rc=$?" >> '"$LOG"
echo "$(date -Is) ALL DONE" >> $LOG
