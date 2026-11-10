#!/bin/bash
# I2 speed sweep: rhoCentralFoam (300 steps, 2 repeats) and HiSA (12 steps), np = 1 2 4 8.
# Waits for AC power before every run (CLAUDE.md/plan: 전원 연결 권장; 배터리 방전 방지).
cd "$(dirname "$0")/.." || exit 1
export PYTHONNOUSERSITE=1 PYTHONPATH=.
PY="$HOME/miniforge3/envs/inlet/bin/python -s"
wait_ac() { until [ "$(cat /sys/class/power_supply/AC1/online 2>/dev/null)" = "1" ]; do echo "$(date +%T) waiting for AC power"; sleep 30; done; }
run() { wait_ac; echo "$(date +%T) start: $*"; $PY scripts/bench.py "$@" | tail -1 | cut -c1-300; }
for rep in 1 2; do for n in 1 2 4 8; do run --solver rcf --np $n --steps 300; done; done
for n in 8 4 2 1; do run --solver hisa --np $n --steps 12; done
echo "$(date +%T) SWEEP DONE"
