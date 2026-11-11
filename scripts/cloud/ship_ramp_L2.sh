#!/bin/bash
# Ramp L2 on the cloud (decisions.md D-018):  ship_ramp_L2.sh [--when-l1-done] [--dry-run]
# 1. prepare cases/validation/ramp24/L2 locally (mesh, initial field mapped from the L1 solution — D-016 (3),
#    decomposition for np 8) with `PREP_ONLY=1 Allrun`; 2. ship it to VM A (t2d-standard-8) once that VM has finished
#    the flat-plate L2 cases (ship_case.sh waits for that). Idempotent: does nothing if L2 was already shipped.
# --when-l1-done: first wait (checking every minute) until L1 has finished with rc 0 AND its y+ check passed
#    (DONE line in cases/runs/i4_run.log). Meant to be left running in the background; needs no Claude.
cd "$(dirname "$0")/../.." || exit 1
source scripts/cloud/handoff.conf
wait_l1=""; dry=""
for a in "$@"; do case $a in --when-l1-done) wait_l1=1;; --dry-run) dry=--dry-run; export DRY_RUN=1;; *) echo "usage: $0 [--when-l1-done] [--dry-run]" >&2; exit 2;; esac; done
source scripts/cloud/handoff_lib.sh
L1=cases/validation/ramp24/L1; L2=cases/validation/ramp24/L2
VMA=${VMA:-ramjet-i4-a}; PRE=${PRE:-flatplate/M2aw_L2 flatplate/M5tw05_L2}
exec 7> "$STATE/lock_ramp_L2"; flock -n 7 || exit 0
[ -e "$STATE/SHIPPED_ramp24_L2" ] && { say "ship_ramp_L2: already shipped"; exit 0; }
l1_done(){ [[ $(tail -n 1 $L1/run_info.txt 2>/dev/null) =~ ^end\ .*\ rc\ 0$ ]] && [ -z "$(case_mpirun_pids $L1)" ] &&
           grep -qE ' ramp24/L1 DONE rc=0 .* yplus_rc=0' cases/runs/i4_run.log 2>/dev/null; }
if [ -n "$wait_l1" ]; then
  say "ship_ramp_L2: waiting for ramp L1 (rc 0 + y+ pass)"
  until l1_done; do [ -n "$dry" ] && { say "DRY-RUN: L1 not done yet"; break; }; sleep 60; done
fi
[ -n "$dry" ] || l1_done || { status "ship_ramp_L2: ramp L1 is not finished with rc 0 and a passed y+ check — L2 NOT started"; exit 1; }
if [ ! -d $L2/processor0 ]; then
  if [ -n "$dry" ]; then say "DRY-RUN would run: INIT_FROM=$L1 PREP_ONLY=1 $L2/Allrun"
  else
    say "ship_ramp_L2: preparing L2 (blockMesh, mapFields from L1, decomposePar)"
    INIT_FROM=$(realpath $L1) PREP_ONLY=1 $L2/Allrun || { status "ship_ramp_L2: L2 preparation FAILED (see $L2/log.*)"; exit 1; }
  fi
fi
scripts/cloud/ship_case.sh $dry --case $L2 --vm "$VMA" --hard-stop-h 40 --wait-h 10 --prereq "$PRE"
