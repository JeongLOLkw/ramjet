#!/bin/bash
# Run the I4 cases one after another (each case uses MPI np from its Allrun, default 4 — D-009).
# Usage: scripts/run_i4.sh [level ...]      e.g.  scripts/run_i4.sh 0      (coarse level only)
#        CASES="flatplate/M2aw ramp24/" scripts/run_i4.sh 0 1 2
# Level k > 0 starts from the level k-1 solution (INIT_FROM, pre-approved adjustment (c)).
# Progress lines go to cases/runs/i4_run.log — this is the file the monitor reads.
cd "$(dirname "$0")/.." || exit 1
PY="env PYTHONNOUSERSITE=1 $HOME/miniforge3/envs/inlet/bin/python -s"
LOG=cases/runs/i4_run.log
mkdir -p cases/runs
LEVELS=${*:-0 1 2}
CASES=${CASES:-"flatplate/M2aw flatplate/M5tw05 flatplate/M6Tw076 ramp24/"}
echo "$(date -Is) start $(git rev-parse --short HEAD) levels: $LEVELS cases: $CASES" >> $LOG
for lvl in $LEVELS; do
  for base in $CASES; do
    case $base in */) c=${base}L$lvl; prev=${base}L$((lvl-1));; *) c=${base}_L$lvl; prev=${base}_L$((lvl-1));; esac
    d=cases/validation/$c
    [ -x $d/Allrun ] || { echo "$(date +%T) $c MISSING" >> $LOG; continue; }
    grep -q "^end " $d/run_info.txt 2>/dev/null && { echo "$(date +%T) $c already run — skipped" >> $LOG; continue; }
    init=""
    [ "$lvl" -gt 0 ] && grep -q "rc 0" cases/validation/$prev/run_info.txt 2>/dev/null && init=$(realpath cases/validation/$prev)
    echo "$(date +%T) $c RUNNING init=${init:-uniform}" >> $LOG
    INIT_FROM=$init $d/Allrun; rc=$?
    last=$(ls $d | grep -E '^[0-9]+$' | sort -n | tail -1)
    yp="n/a"
    [ $rc -eq 0 ] && [ "$last" != "0" ] && { $PY scripts/yplus_check.py $d $last wall > $d/log.yplus 2>&1; yp=$?; }
    echo "$(date +%T) $c DONE rc=$rc last=$last yplus_rc=$yp" >> $LOG
  done
done
echo "$(date -Is) ALL DONE" >> $LOG
