#!/bin/bash
# I2 follow-up: np = 6 only (D-009). Same settings as run_bench_sweep.sh. Waits for AC power before every run.
cd "$(dirname "$0")/.." || exit 1
export PYTHONNOUSERSITE=1 PYTHONPATH=.
PY="$HOME/miniforge3/envs/inlet/bin/python -s"
wait_ac() { until [ "$(cat /sys/class/power_supply/AC1/online 2>/dev/null)" = "1" ]; do echo "$(date +%T) waiting for AC power"; sleep 30; done; }
run() { wait_ac; echo "$(date +%T) start: $*"; $PY scripts/bench.py "$@" | tail -1 | cut -c1-300; }
for rep in 1 2; do run --solver rcf --np 6 --steps 300; done
run --solver hisa --np 6 --steps 12
echo "$(date +%T) NP6 DONE"
