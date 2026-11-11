#!/bin/bash
# Bring a handed-off job back:  restore.sh [--dry-run] [--state <dir>] [--force] [--force-recall] [--local-only] [--case <dir>]
# Decides whether to recall the job from the VM, downloads the newest result, resumes/finishes it locally with
# local_resume.sh and makes sure the VM is stopped. Dry run: one read-only pass, prints what it would do.
cd "$(dirname "$0")/../.." || exit 1
_log_env=${LOG-}; source scripts/cloud/handoff.conf
force=""; frecall=""; local_only=""; case_arg=""; state_arg=""
while [ $# -gt 0 ]; do case $1 in
  --dry-run) DRY_RUN=1;; --state) STATE=$2; state_arg=1; shift;; --force) force=1;; --force-recall) frecall=1;;
  --local-only) local_only=1;; --case) case_arg=$2; shift;; --vm) VM=$2; shift;;
  *) echo "usage: $0 [--dry-run] [--state dir] [--force] [--force-recall] [--local-only] [--case dir]" >&2; exit 2;; esac; shift; done
[ -z "$_log_env" ] && [ -n "$state_arg" ] && LOG=$STATE/handoff.log
export DRY_RUN
source scripts/cloud/handoff_lib.sh
P=gs://$BUCKET/handoff/$VM; GC="--zone $ZONE --project $PROJECT"
kv(){ tr " " "\n" < "$1" | sed -n "s/^$2=//p" | head -n 1; }   # kv file key (key=value per line or per word)
dry(){ [ -n "$DRY_RUN" ]; }

exec 9> "$STATE/lock"; flock 9      # wait: handoff.sh may still be finishing
[ -e "$STATE/restore.started" ] && [ -z "$force" ] && exit 0
dry || : > "$STATE/restore.started"

# --- emergency: no cloud contact ------------------------------------------------------------------------------
if [ -n "$local_only" ]; then
  c=$case_arg
  for f in HANDOFF_DONE HANDOFF_FAILED; do [ -z "$c" ] && [ -f "$STATE/$f" ] && c=$(kv "$STATE/$f" case); done
  [ -d "$c" ] || { status "local-only: no case known (use --case)"; exit 0; }
  if [ -n "$(case_mpirun_pids "$c")" ]; then status "local-only: $c already running"; exit 0; fi
  say "WARNING: local-only restore; the VM may still be running and must be stopped by hand (gcloud compute instances stop $VM $GC)"
  dry && { say "DRY-RUN would start local_resume.sh $c"; exit 0; }
  detach scripts/cloud/local_resume.sh "$c"; status "local-only: resumed locally (VM NOT touched - stop it by hand)"; exit 0
fi

[ -f "$STATE/HANDOFF_DONE" ] || { status "nothing was handed off — nothing to restore"; exit 0; }
case_dir=$(kv "$STATE/HANDOFF_DONE" case); tag=$(kv "$STATE/HANDOFF_DONE" tag); lsps=$(kv "$STATE/HANDOFF_DONE" local_sps)

# --- wait until gcloud works ----------------------------------------------------------------------------------
t0=$SECONDS
until gcloud storage ls "gs://$BUCKET/" >/dev/null 2>&1; do
  dry && { say "DRY-RUN: gcloud not reachable"; exit 0; }
  (( SECONDS - t0 > 6*3600 )) && { status "gcloud unreachable for 6 h — try restore.sh --local-only"; exit 0; }
  sleep 60
done

fetch_and_resume(){ # fetch_and_resume <marker file>: download latest.tar.gz, verify, back up, extract, resume locally
  local want dl bk
  want=$(kv "$1" sha256); dl=$STATE/dl_$tag.tar.gz; bk=$STATE/backup_${tag}_$(date +%Y%m%d_%H%M%S)
  if dry; then say "DRY-RUN would download $P/out/latest.tar.gz (sha256 $want), back up into $bk, extract into $case_dir, start local_resume.sh"; return 0; fi
  if [ -n "$(case_mpirun_pids "$case_dir")" ]; then status "a solver is running in $case_dir — NOT overwriting it"; return 1; fi
  local i ok=""   # the bucket copy is the only place with the cloud progress: retry for about 30 min (flaky network)
  for i in $(seq 20); do
    down "$P/out/latest.tar.gz" "$dl" && [ "$(sha256sum "$dl" | cut -d' ' -f1)" = "$want" ] && { ok=1; break; }
    say "download/sha256 check failed (try $i/20)"; sleep 30
  done
  if [ -n "$ok" ]; then
    mkdir -p "$bk"; ( cd "$case_dir" && cp -a log.solver log.time run_info.txt postProcessing "$bk/" 2>/dev/null )
    tar xzf "$dl" -C "$case_dir" || { status "extract failed — local checkpoint kept"; return 1; }
    detach scripts/cloud/local_resume.sh "$case_dir"; return 0
  fi
  say "download/sha256 check FAILED — resuming locally from the old checkpoint (the VM still holds the result)"
  detach scripts/cloud/local_resume.sh "$case_dir"; return 1
}

# --- decide ---------------------------------------------------------------------------------------------------
deadline=$(( $(date +%s) + (HARD_STOP_H + 1) * 3600 )); first=1; result=""
while :; do
  files=$(gcloud storage ls "$P/out/" 2>/dev/null)
  if   grep -q '/FINISHED$' <<<"$files"; then m=FINISHED
  elif grep -q '/READY$'    <<<"$files"; then m=READY
  elif grep -q '/FAILED$'   <<<"$files"; then m=FAILED
  else m=""; fi
  if [ -n "$m" ]; then
    gcloud storage cat "$P/out/$m" > "$STATE/marker_$m" 2>/dev/null
    if [ "$m" = FAILED ]; then
      status "cloud run FAILED ($(head -n 1 "$STATE/marker_FAILED")) — resuming locally from the local checkpoint"
      dry || { down "$P/out/log.solver.tail" "$STATE/cloud_log.solver.tail"; down "$P/out/handoff_vm.log" "$STATE/cloud_handoff_vm.log"
               detach scripts/cloud/local_resume.sh "$case_dir"; }
      result="FAILED"
    else
      fetch_and_resume "$STATE/marker_$m"; result="$m rc=$?"
      status "cloud result $m ($(head -n 1 "$STATE/marker_$m")) handled ($result)"
    fi
    break
  fi
  # VM off without a terminal marker (crash, forced stop): take the newest checkpoint it synced, else the local one
  vs=$(gcloud compute instances describe "$VM" $GC --format='value(status)' 2>/dev/null)
  if [ "$vs" = TERMINATED ] && ! gcloud storage ls "$P/out/" 2>/dev/null | grep -qE '/(FINISHED|READY|FAILED)$'; then
    if gcloud storage cat "$P/out/LATEST" > "$STATE/marker_LATEST" 2>/dev/null && [ -s "$STATE/marker_LATEST" ]; then
      status "VM $VM is off without a result marker — taking its last synced checkpoint ($(head -n 1 "$STATE/marker_LATEST"))"
      fetch_and_resume "$STATE/marker_LATEST"; result="LATEST rc=$?"
    else
      status "VM $VM is off and synced nothing — resuming locally from the local checkpoint"
      dry || detach scripts/cloud/local_resume.sh "$case_dir"; result="VM_OFF_NO_DATA"
    fi
    break
  fi
  hb=$(gcloud storage cat "$P/out/HEARTBEAT" 2>/dev/null)
  csps=$(sed -n 's/.*sps=\([0-9.]*\).*/\1/p' <<<"$hb")
  if [ -n "$first" ] && [ -n "$hb" ] && { [ -n "$csps" ] || [ -n "$frecall" ]; }; then
    first=""; step=$(sed -n 's/.*step=\([0-9]*\).*/\1/p' <<<"$hb")
    end=$(sed -n 's/.*end=\([0-9]*\).*/\1/p' <<<"$hb"); rem=$(( ${end:-0} - ${step:-0} ))
    if [ -n "$frecall" ] || { [ -n "$csps" ] && [[ $lsps =~ ^[0-9.]+$ ]] && awk -v r=$rem -v c=$csps -v l=$lsps -v g=$RECALL_GAIN_S 'BEGIN{exit !(r*(c-l)>g)}'; }; then
      dry && say "DRY-RUN would upload $P/RECALL" || put_text "recall $(date -Is)" "$P/RECALL"
      status "recall requested (step $step/$end, cloud $csps s/step vs local $lsps)"
    else status "left in the cloud (faster or nearly as fast: step $step/$end, cloud $csps s/step vs local $lsps)"; fi
  fi
  dry && { say "DRY-RUN: heartbeat='${hb:-none}' markers='$(tr '\n' ' ' <<<"$files")' — would keep polling every 2 min"; exit 0; }
  if (( $(date +%s) > deadline )); then status "no terminal marker after $((HARD_STOP_H+1)) h — stopping the VM, resuming locally"; result=TIMEOUT
    G compute instances stop "$VM" $GC >> "$LOG" 2>&1; detach scripts/cloud/local_resume.sh "$case_dir"; break; fi
  sleep 120
done

# --- the VM must end up stopped -------------------------------------------------------------------------------
t0=$SECONDS; vs=""
while (( SECONDS - t0 < 600 )); do
  vs=$(gcloud compute instances describe "$VM" $GC --format='value(status)' 2>/dev/null); [ "$vs" = TERMINATED ] && break; sleep 30; done
[ "$vs" = TERMINATED ] || { say "VM $VM is '$vs' after 10 min — stopping it"; G compute instances stop "$VM" $GC >> "$LOG" 2>&1; }
dry && exit 0
date -Is > "$STATE/RESTORE_DONE"
status "RESTORE DONE ($result); VM $VM was ${vs:-unknown} (stopped if it was not TERMINATED)"
exit 0
