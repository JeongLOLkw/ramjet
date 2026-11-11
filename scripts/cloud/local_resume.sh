#!/bin/bash
# Continue a case locally after a handoff (or finish a case that the cloud already completed):  local_resume.sh <case dir>
# Like scripts/run_i4.sh: after rc 0 run the y+ check and log a DONE line to $I4_LOG (default cases/runs/i4_run.log).
cd "$(dirname "$0")/../.." || exit 1
source scripts/cloud/handoff.conf; source scripts/cloud/handoff_lib.sh
PY=${PY:-env PYTHONNOUSERSITE=1 $HOME/miniforge3/envs/inlet/bin/python -s}
I4_LOG=${I4_LOG:-$REPO/cases/runs/i4_run.log}
c=$(realpath "$1") || exit 1
case $c in $REPO/cases/validation/*) rel=${c#$REPO/cases/validation/};; *) rel=$(basename "$c");; esac
last=$(tail -n 1 "$c/run_info.txt" 2>/dev/null)
if [[ $last =~ ^end\ .*\ rc\ 0$ ]]; then   # the cloud finished it: only reconstruct
  say "local_resume $rel: case already finished (rc 0), reconstructing only"
  source /usr/lib/openfoam/openfoam2512/etc/bashrc >/dev/null 2>&1
  ( cd "$c" && reconstructPar -newTimes > log.reconstructPar 2>&1 && tail -n 300 log.solver > log.solver.tail ); rc=$?
  [ $rc -eq 0 ] || rc=90
else
  say "local_resume $rel: restarting solver from the latest checkpoint"
  scripts/cloud/Allrestart.sh "$c"; rc=$?
fi
t=$(ls "$c" | grep -E '^[0-9]+$' | sort -n | tail -n 1); yp="n/a"
if [ $rc -eq 0 ] && [ "$t" != 0 ]; then $PY scripts/yplus_check.py "$c" "$t" wall > "$c/log.yplus" 2>&1; yp=$?; fi
echo "$(date +%T) $rel DONE rc=$rc last=$t yplus_rc=$yp (resumed after handoff)" >> "$I4_LOG"
say "local_resume $rel: rc=$rc last=$t yplus_rc=$yp"
if [ $rc -eq 0 ] && [ "$yp" = 0 ] && [ -n "$AFTER_DONE_CMD" ]; then
  say "running AFTER_DONE_CMD: $AFTER_DONE_CMD"; bash -c "$AFTER_DONE_CMD" >> "$LOG" 2>&1
fi
exit $rc
