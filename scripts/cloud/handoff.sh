#!/bin/bash
# Hand the running local I4 job to the cloud VM:  handoff.sh [--dry-run] [--case <dir>] [--vm <name>] [--state <dir>] [--force]
# Stops the local solver right after a complete checkpoint, uploads it, boots the VM in handoff mode and checks that
# it is running. If anything fails after the local stop, the VM is stopped again and the case resumes locally.
# Marker files in $STATE: handoff.started, HANDOFF_DONE | HANDOFF_FAILED | HANDOFF_SKIPPED | HANDOFF_NONE, STATUS.
cd "$(dirname "$0")/../.." || exit 1
_log_env=${LOG-}; source scripts/cloud/handoff.conf
case_arg=""; force=""; state_arg=""
while [ $# -gt 0 ]; do case $1 in
  --dry-run) DRY_RUN=1;; --case) case_arg=$2; shift;; --vm) VM=$2; shift;; --state) STATE=$2; state_arg=1; shift;; --force) force=1;;
  *) echo "usage: $0 [--dry-run] [--case dir] [--vm name] [--state dir] [--force]" >&2; exit 2;; esac; shift; done
[ -z "$_log_env" ] && [ -n "$state_arg" ] && LOG=$STATE/handoff.log
export DRY_RUN
source scripts/cloud/handoff_lib.sh
P=gs://$BUCKET/handoff/$VM; GC="--zone $ZONE --project $PROJECT"
mark(){ if [ -n "$DRY_RUN" ]; then say "DRY-RUN would create marker $1"; else printf '%s\n' "${2:-$(date -Is)}" > "$STATE/$1"; fi; }
PS=$(command -v powershell.exe || echo /mnt/c/WINDOWS/System32/WindowsPowerShell/v1.0/powershell.exe)   # PATH may lack it (systemd)
popup(){ [ -n "$DRY_RUN" ] || { setsid nohup "$PS" -NoProfile -Command "(New-Object -ComObject WScript.Shell).Popup('ramjet: $1',0,'ramjet',64)" >/dev/null 2>&1 9>&- < /dev/null & } 2>/dev/null; return 0; }

exec 9> "$STATE/lock"; flock -n 9 || exit 0
[ -e "$STATE/handoff.started" ] && [ -z "$force" ] && exit 0
mark handoff.started
[ -n "$DRY_RUN" ] && say "DRY-RUN: nothing will be stopped, uploaded or started"

# --- 2. which case --------------------------------------------------------------------------------------------
job=""; others=()
while read -r pid cwd; do
  [ -z "$pid" ] && continue
  if [ -n "$case_arg" ]; then [ "$cwd" = "$(realpath "$case_arg")" ] && [ -z "$job" ] && job=$cwd
  elif [[ $cwd == $REPO/cases/validation/* ]]; then
    if [ -z "$job" ]; then job=$cwd; elif [ "$cwd" != "$job" ]; then say "another repo job also running, left alone: $cwd"; fi
  else others+=("$cwd"); fi
done < <(for p in /proc/[0-9]*; do p=${p#/proc/}; [[ $(cat /proc/$p/comm 2>/dev/null) =~ ^(mpirun|mpiexec)$ ]] && echo "$p $(readlink /proc/$p/cwd)"; done)
if [ -z "$job" ]; then status "nothing running — nothing to hand off"; mark HANDOFF_NONE; exit 0; fi
case $job in $REPO/cases/validation/*) rel=${job#$REPO/cases/validation/};; *) rel=$(basename "$job");; esac
tag=${rel//\//_}
say "job: $job (tag $tag, step $(case_step "$job"), vm $VM)"

# --- 3. cloud prerequisite (read-only) ------------------------------------------------------------------------
skip=""
vs=$(gcloud compute instances describe "$VM" $GC --format='value(status)' 2>>"$LOG") || skip="gcloud failed (VM status)"
[ -z "$skip" ] && [ "$vs" != TERMINATED ] && skip="VM $VM is $vs"
for q in $PREREQ_CASE; do   # one or more cases (space separated) that must have ended with rc 0 on that VM
  [ -n "$skip" ] && break
  l=$(gcloud storage cat "gs://$BUCKET/results/validation/$q/run_info.txt" 2>>"$LOG" | tail -n 1) || true
  [[ $l =~ ^end\ .*\ rc\ 0$ ]] || skip="prerequisite $q not finished (last line: ${l:-none})"
done
if [ -n "$skip" ]; then
  status "cloud busy/unreachable — local run left untouched ($skip)"
  if [ -z "$DRY_RUN" ]; then mark HANDOFF_SKIPPED; exit 0; fi
  say "DRY-RUN: a real run would stop here; continuing to show the plan"
fi

# --- 4. checkpoint, stop --------------------------------------------------------------------------------------
for o in "${others[@]}"; do
  if [ -n "$DRY_RUN" ]; then say "DRY-RUN would stop diagnostic mpirun in $o"; else say "stopping diagnostic mpirun in $o"; stop_case "$o"; fi
done
lsps=$(sps_from_log "$job"); say "local speed: $lsps s/step"
if [ -n "$DRY_RUN" ]; then
  say "DRY-RUN would wait <=900 s for the next complete checkpoint (newest now: $(latest_complete_step "$job")), then stop_case"
  say "DRY-RUN would pack:" ; _pack_list "$job" "$(latest_complete_step "$job")" | sed 's/^/    /'
  say "DRY-RUN VM $VM would be started in handoff mode, then HEARTBEAT polled 15 min; on failure local_resume.sh"
  exit 0
fi
N=$(wait_checkpoint "$job" 900) || say "WARNING: no new checkpoint within 900 s, using newest complete step '$N'"
[ -n "$N" ] || { status "no complete checkpoint found - local run left untouched"; mark HANDOFF_SKIPPED; exit 0; }
stop_case "$job" "$N"
echo "handoff-stop $(date -Is) step $N host $(hostname)" >> "$job/run_info.txt"
say "stopped at step $N"

fail(){ # after the local stop: bring the VM down; continue locally only if LOCAL_FALLBACK=1 (D-019: default 0)
  say "FAILED: $1"; G compute instances stop "$VM" $GC >> "$LOG" 2>&1
  mark HANDOFF_FAILED "case=$job"
  if [ "${LOCAL_FALLBACK:-0}" = 1 ]; then
    detach scripts/cloud/local_resume.sh "$job"
    status "HANDOFF FAILED — resumed locally ($1)"; popup "HANDOFF FAILED - resumed locally"
  else
    status "HANDOFF FAILED — nothing is running: $rel stays stopped at step $N locally, VM $VM stopped ($1)"
    popup "HANDOFF FAILED - nothing is running"
  fi
  exit 0; }

# --- 5. pack, upload ------------------------------------------------------------------------------------------
tar=$STATE/pack_$tag.tar.gz
pack_case "$job" "$N" "$tar" || fail "pack"
sha=$(sha256sum "$tar" | cut -d' ' -f1)
rinfo() { awk -v k="$1" '$1==k{print $2; exit}' "$job/run_info.txt"; }
end=$(awk '$1=="endTime"{gsub(";","",$2); print $2}' "$job/system/controlDict")
pub=no; [[ $job == $REPO/cases/validation/* ]] && pub=yes   # only repo cases are published to results/validation
printf 'case=%s\ntag=%s\nstep=%s\nnp=%s\ncommit=%s\ndirty=%s\nsha256=%s\nend=%s\npublish=%s\n' "$rel" "$tag" "$N" "$(rinfo np)" "$(rinfo commit)" "$(rinfo dirty_files)" "$sha" "$end" "$pub" > "$STATE/JOB"
# code of the current commit for the VM (y+ check, follow-up case files); the hash goes into the VM's run_info.txt (rule 9)
[ -z "$(git status --porcelain --untracked-files=no -- scripts src cases/validation/ramp24/L2)" ] || say "WARNING: tracked code files differ from HEAD — the VM gets HEAD"
git archive --format=tar.gz -o "$STATE/code.tar.gz" HEAD scripts src cases/validation/ramp24/L2 && git rev-parse HEAD > "$STATE/code.commit" || fail "git archive"
clean_bucket "$P" || fail "old markers in $P could not be removed"
up "$tar" "$P/in/$tag.tar.gz" && up "$STATE/JOB" "$P/in/JOB" || fail "upload"
GQ storage cp scripts/cloud/*.sh "gs://$BUCKET/inputs/cloud/" || fail "upload scripts"
up "$STATE/code.tar.gz" "gs://$BUCKET/inputs/code.tar.gz" && up "$STATE/code.commit" "gs://$BUCKET/inputs/code.commit" || fail "upload code"
[ -n "$NEXT_SH" ] && { up "$NEXT_SH" "$P/in/NEXT.sh" || fail "upload NEXT.sh"; say "follow-up script: $NEXT_SH"; }
say "uploaded $(du -h "$tar" | cut -f1), sha256 $sha"

# --- 6. boot the VM in handoff mode ---------------------------------------------------------------------------
GQ compute instances add-metadata "$VM" $GC --metadata "mode=handoff,hard_stop_h=$HARD_STOP_H" \
  --metadata-from-file startup-script=scripts/cloud/vm_startup.sh || fail "add-metadata"
# GCE forces a STOP after max-run-duration (cost guard outside the VM); it must outlast the worker's own hard stop
GQ compute instances set-scheduling "$VM" $GC --max-run-duration="$((HARD_STOP_H + 2))h" --instance-termination-action=STOP \
  || say "WARNING: set-scheduling failed — the VM keeps its previous max-run-duration"
GQ compute instances start "$VM" $GC || fail "start VM"

# --- 7. wait for a running heartbeat that is past the handoff step ---------------------------------------------
wait_heartbeat "$P" "$tag" "$N" 900 || fail "no running heartbeat of $tag past step $N within 15 min (last: ${HB:-none})"
# 2026-11-12 rehearsal: the VM powered itself off 3 min after a good first heartbeat. Keep watching for 6 min.
say "first heartbeat ok ($HB) — watching for 6 more minutes"
confirm_alive "$P" "$tag" 360 || fail "VM/solver did not stay up for 6 min after the first heartbeat (${HB:-none})"
hb=$HB
printf 'case=%s\ntag=%s\nvm=%s\nstep=%s\nlocal_sps=%s\nend=%s\ntime=%s\n' "$job" "$tag" "$VM" "$N" "$lsps" "$end" "$(date -Is)" > "$STATE/HANDOFF_DONE"
status "HANDOFF OK — safe to close the laptop (cloud $hb)"
popup "handoff OK - you can close the laptop"
exit 0
