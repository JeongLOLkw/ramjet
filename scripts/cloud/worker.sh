#!/bin/bash
# VM worker:  worker.sh <bucket> <hard stop hours> <case base>...
# Runs one chain (levels 1 and 2) per case in parallel, syncs results to the bucket every 5 min, stops everything
# at the hard time limit (cost guard), does a final sync and then deletes this VM (CLAUDE.md rules 7, 8).
cd "$(dirname "$0")/../.." || exit 1
BUCKET=$1; HARD=$2; shift 2
mkdir -p cases/runs
LOG=cases/runs/cloud_worker.log
say(){ echo "$(date -Is) $*" >> $LOG; }
sync_once(){
  gcloud storage rsync -r cases/validation "gs://$BUCKET/results/validation" >> cases/runs/cloud_sync.log 2>&1
  local r=$?
  gcloud storage rsync -r cases/runs "gs://$BUCKET/results/runs-$(hostname)" >> cases/runs/cloud_sync.log 2>&1
  return $r
}
source /usr/lib/openfoam/openfoam2512/etc/bashrc >/dev/null 2>&1
command -v hisa >/dev/null || { say "FATAL hisa not found"; sync_once; exit 1; }
say "worker start: chains=$* hard_stop=${HARD}h host=$(hostname)"
start=$(date +%s)
( while :; do sleep 300; sync_once; done ) & SYNC=$!
pids=()
for b in "$@"; do
  scripts/cloud/chain.sh "$b" 1 2 > "cases/runs/chain_${b//\//_}.log" 2>&1 & pids+=($!)
done
stopped=0
while :; do
  alive=0; for p in "${pids[@]}"; do kill -0 "$p" 2>/dev/null && alive=1; done
  [ $alive -eq 0 ] && break
  if [ $(( ($(date +%s)-start)/3600 )) -ge "$HARD" ]; then
    say "HARD STOP after ${HARD}h: killing solvers"; stopped=1
    pkill -f chain.sh; pkill -x hisa; sleep 5; break
  fi
  sleep 60
done
rcs=""; for p in "${pids[@]}"; do wait "$p"; rcs="$rcs $?"; done
kill $SYNC 2>/dev/null
ok=1; for i in 1 2 3 4 5; do sync_once && { ok=0; break; }; sleep 30; done
say "worker finished rcs:$rcs hard_stopped=$stopped final_sync_rc=$ok"
echo "rcs:$rcs hard_stopped=$stopped final_sync_rc=$ok $(date -Is)" > cases/runs/WORKER_DONE
sync_once
if [ $ok -eq 0 ]; then
  zone=$(curl -s -H Metadata-Flavor:Google http://metadata.google.internal/computeMetadata/v1/instance/zone | awk -F/ '{print $NF}')
  say "deleting VM $(hostname) in $zone"
  gcloud compute instances delete "$(hostname)" --zone "$zone" --quiet >> $LOG 2>&1
else
  say "final sync FAILED - VM kept for manual rescue"
fi
