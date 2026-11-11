#!/bin/bash
# One case through its finer levels:  chain.sh <case base> <level...>     e.g. chain.sh flatplate/M2aw 1 2
# Idempotent (safe to start again after a crash/reboot): finished levels are skipped, an interrupted level
# resumes from its latest checkpoint (Allrestart.sh), a new level starts from the previous level's solution
# (pre-approved adjustment (c)). Same failure 3 times -> stop (CLAUDE.md 오류 3회 정지 규칙) and exit nonzero.
cd "$(dirname "$0")/../.." || exit 1
base=$1; shift
prev=cases/validation/${base}_L0
mkdir -p cases/runs
for lvl in "$@"; do
  c=cases/validation/${base}_L$lvl
  if [ "$(tail -n1 "$c/run_info.txt" 2>/dev/null | awk '{print $1, $(NF-1), $NF}')" = "end rc 0" ]; then prev=$c; continue; fi
  tries=0
  while :; do
    echo "$(date +%T) $c start try $tries" >> cases/runs/cloud_chain.log
    if ls "$c"/processor0 2>/dev/null | grep -qE '^[1-9][0-9]*$'; then
      scripts/cloud/Allrestart.sh "$c"; rc=$?
    else
      INIT_FROM=$(realpath "$prev") "$c/Allrun"; rc=$?
    fi
    echo "$(date +%T) $c rc=$rc" >> cases/runs/cloud_chain.log
    [ $rc -eq 0 ] && break
    tries=$((tries+1)); [ $tries -ge 3 ] && exit $rc
    sleep 30
  done
  prev=$c
done
