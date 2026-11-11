#!/bin/bash
# One-screen status of the handoff: local markers, scheduler, local solvers, VMs and the bucket markers.
cd "$(dirname "$0")/../.." || exit 1
source scripts/cloud/handoff.conf; source scripts/cloud/handoff_lib.sh
P=gs://$BUCKET/handoff/$VM
echo "== STATUS:  $(cat "$STATE/STATUS" 2>/dev/null || echo '(none)')"
echo "== markers in $STATE: $(cd "$STATE" && ls HANDOFF_* handoff.started restore.started RESTORE_DONE 2>/dev/null | tr '\n' ' ')"
echo "== scheduler: $(pgrep -af handoff_sched.sh | grep -v pgrep | head -n 3 || true)"
systemctl --user list-timers --all 2>/dev/null | grep ramjet
echo "== local solvers"
for p in /proc/[0-9]*; do p=${p#/proc/}; [[ $(cat /proc/$p/comm 2>/dev/null) =~ ^(mpirun|hisa)$ ]] || continue
  d=$(readlink /proc/$p/cwd); echo "  pid $p $(cat /proc/$p/comm) $d step=$(case_step "$d")"; done
echo "== VMs"; gcloud compute instances list --project "$PROJECT" --format="table(name,status)" 2>&1 | head -n 8
echo "== bucket $P"
echo "  HEARTBEAT: $(gcloud storage cat "$P/out/HEARTBEAT" 2>/dev/null || echo '(none)')"
for m in READY FINISHED FAILED LATEST; do x=$(gcloud storage cat "$P/out/$m" 2>/dev/null) && echo "  $m: $x"; done
gcloud storage ls "$P/RECALL" >/dev/null 2>&1 && echo "  RECALL requested"
echo "== last 15 lines of $LOG"; tail -n 15 "$LOG" 2>/dev/null
