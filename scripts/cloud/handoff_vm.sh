#!/bin/bash
# VM side of a handoff (run by i4-worker.service as toto):  handoff_vm.sh <bucket> <hard stop hours>
# Unpacks the job from the bucket, resumes it (Allrestart.sh), reports a HEARTBEAT every 30 s, uploads the newest
# checkpoint every 5 min and ends with exactly one marker: READY (stopped at a checkpoint on RECALL / hard stop),
# FINISHED (reached endTime, rc 0) or FAILED. Idempotent across crashes/reboots; always exits 0 (Restart=on-failure).
cd "$(dirname "$0")/../.." || exit 1
BUCKET=$1; HARD=${2:-12}; mkdir -p cases/runs
LOG=$PWD/cases/runs/handoff_vm.log
source scripts/cloud/handoff_lib.sh
source /usr/lib/openfoam/openfoam2512/etc/bashrc >/dev/null 2>&1
P=gs://$BUCKET/handoff/$(hostname); W=$(mktemp -d); sha=""; terminal=""
sync_log(){ GQ storage cp "$LOG" "$P/out/handoff_vm.log"; }
finish(){ trap - EXIT; say "finish (terminal marker: ${terminal:-none})"; sync_log
  [ -n "$terminal" ] && [ -n "$sha" ] && touch "cases/runs/handoff_done_$sha"
  echo "handoff $(date -Is) ${terminal:-no-marker}" > cases/runs/WORKER_DONE; exit 0; }
trap finish EXIT
marker(){ put_text "$2" "$P/out/$1" && terminal=$1; }   # marker NAME TEXT
say "handoff_vm start host=$(hostname) hard=${HARD}h"

# --- the job --------------------------------------------------------------------------------------------------
down "$P/in/JOB" "$W/JOB"
[ -s "$W/JOB" ] || { say "no JOB at $P/in/JOB"; exit 0; }
jget(){ sed -n "s/^$1=//p" "$W/JOB"; }
rel=$(jget case); tag=$(jget tag); sha=$(jget sha256); C=$PWD/cases/validation/$rel
if [ -e "cases/runs/handoff_done_$sha" ]; then say "job $sha already finished"; terminal=""; exit 0; fi
if [ ! -e "cases/runs/handoff_unpacked_$sha" ]; then
  down "$P/in/$tag.tar.gz" "$W/job.tar.gz"
  if [ "$(sha256sum "$W/job.tar.gz" 2>/dev/null | cut -d' ' -f1)" != "$sha" ]; then
    say "sha256 mismatch or download failed"; marker FAILED "rc=sha256 mismatch/download"; exit 0; fi
  rm -rf "$C"   # fresh job: no leftover time dirs of an earlier job on this VM may pose as the latest checkpoint
  mkdir -p "$C" && tar xzf "$W/job.tar.gz" -C "$C" && touch "cases/runs/handoff_unpacked_$sha" || { marker FAILED "rc=unpack"; exit 0; }
  say "unpacked $rel (step $(jget step))"
else say "continuing from what is on disk ($rel)"; fi
prune_newer "$C" "$(latest_complete_step "$C")"   # a crash may have left a partial time dir
[ -e "cases/runs/handoff_start_$sha" ] || date +%s > "cases/runs/handoff_start_$sha"
start=$(cat "cases/runs/handoff_start_$sha"); end=$(awk '$1=="endTime"{gsub(";","",$2); print $2}' "$C/system/controlDict")
L0=$(wc -l < "$C/log.solver" 2>/dev/null || echo 0)   # lines before this run: carried-over log, ignore for step/speed

# --- helpers --------------------------------------------------------------------------------------------------
hb(){ local s; s=$(case_step "$C" "$L0"); s=${s:-$(latest_complete_step "$C")}
  put_text "time=$(date -Is) step=${s:-0} sps=$(sps_from_log "$C" 200) state=$1 end=$end tag=$tag" "$P/out/HEARTBEAT"; }
upload_pack(){ # upload_pack <step|ALL>   -> sets sha_out; returns 1 if packing/upload failed
  if [ "$1" = ALL ]; then pack_case_final "$C" "$W/out.tar.gz"; else pack_case "$C" "$1" "$W/out.tar.gz"; fi || return 1
  sha_out=$(sha256sum "$W/out.tar.gz" | cut -d' ' -f1)
  up "$W/out.tar.gz" "$P/out/latest.tar.gz" && put_text "step=$1 sha256=$sha_out" "$P/out/LATEST"; }
tail_log(){ tail -n 300 "$C/log.solver" > "$W/log.solver.tail"; GQ storage cp "$W/log.solver.tail" "$P/out/log.solver.tail"; }
stopped_at(){ # stopped_at <reason>: wait for a checkpoint, stop the solver, upload, READY
  hb stopping; local n; n=$(wait_checkpoint "$C" 1500 "$L0")
  [ -n "$n" ] || { stop_case "$C"; marker FAILED "rc=no checkpoint at $1"; return; }
  stop_case "$C" "$n"; echo "handoff-stop $(date -Is) step $n host $(hostname) reason $1" >> "$C/run_info.txt"
  if upload_pack "$n"; then marker READY "step=$n reason=$1 sha256=$sha_out"; else marker FAILED "rc=upload at $1"; fi; }

# --- run ------------------------------------------------------------------------------------------------------
scripts/cloud/Allrestart.sh "$C" > /dev/null 2>&1 & AP=$!
say "Allrestart started (pid $AP), end=$end"
last_up=0; last_step=""
while :; do
  if ! kill -0 $AP 2>/dev/null; then
    wait $AP; rc=$?
    if [ $rc -eq 0 ]; then hb done
      if upload_pack ALL; then marker FINISHED "step=$(case_step "$C" "$L0") rc=0 sha256=$sha_out"; else marker FAILED "rc=upload final"; fi
    else say "solver rc $rc"; tail_log; marker FAILED "rc=$rc"; fi
    break
  fi
  hb running
  if (( SECONDS - last_up >= 300 )); then
    last_up=$SECONDS; s=$(latest_complete_step "$C"); t=$(case_step "$C" "$L0")
    if [ -n "$s" ] && [ "$s" != "$last_step" ] && [ -n "$t" ] && [ "$t" -ge $((s + 2)) ]; then
      upload_pack "$s" && last_step=$s && say "synced checkpoint $s"; fi
    tail_log; sync_log
  fi
  r=""; gcloud storage ls "$P/RECALL" >/dev/null 2>&1 && r=recall
  [ -z "$r" ] && (( $(date +%s) - start >= HARD * 3600 )) && r=hard_stop
  if [ -n "$r" ]; then say "stopping: $r"; stopped_at $r; break; fi
  sleep 30
done
exit 0
