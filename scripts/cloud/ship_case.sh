#!/bin/bash
# Send a prepared (decomposed, NOT running) case to a stopped VM and start it there in handoff mode:
#   ship_case.sh [--dry-run] --case <dir> --vm <name> [--hard-stop-h N] [--wait-h N] [--prereq "<case> <case> ..."]
# The case must be decomposed (processor*/0 from `PREP_ONLY=1 Allrun`, or a later checkpoint). Waits (polling every
# 5 min, up to --wait-h hours) until the VM is TERMINATED and every prerequisite case shows `end ... rc 0` in the
# bucket, i.e. the VM has finished what it was doing. The VM side is handoff_vm.sh (same path as handoff.sh).
# Nothing is created or deleted: an existing VM is started (CLAUDE.md rule 7, decisions.md D-018).
cd "$(dirname "$0")/../.." || exit 1
source scripts/cloud/handoff.conf
case_arg=""; hard=40; wait_h=8; prereq=""
while [ $# -gt 0 ]; do case $1 in
  --dry-run) DRY_RUN=1;; --case) case_arg=$2; shift;; --vm) VM=$2; shift;; --hard-stop-h) hard=$2; shift;;
  --wait-h) wait_h=$2; shift;; --prereq) prereq=$2; shift;;
  *) echo "usage: $0 [--dry-run] --case dir --vm name [--hard-stop-h N] [--wait-h N] [--prereq \"cases\"]" >&2; exit 2;; esac; shift; done
export DRY_RUN
source scripts/cloud/handoff_lib.sh
c=$(realpath "$case_arg") || exit 2
P=gs://$BUCKET/handoff/$VM; GC="--zone $ZONE --project $PROJECT"
case $c in $REPO/cases/validation/*) rel=${c#$REPO/cases/validation/};; *) rel=$(basename "$c");; esac
tag=${rel//\//_}
exec 8> "$STATE/lock_ship_$VM"; flock -n 8 || { say "ship_case: another ship to $VM is in progress"; exit 0; }
[ -d "$c/processor0" ] || { say "ship_case: $rel is not decomposed"; exit 1; }
[ -z "$(case_mpirun_pids "$c")" ] || { say "ship_case: a solver is running in $rel — use handoff.sh"; exit 1; }
N=$(latest_complete_step "$c"); N=${N:-0}
say "ship_case: $rel (step $N) -> $VM, hard stop ${hard} h, prerequisites: ${prereq:-none}"

# --- wait until the VM is free ----------------------------------------------------------------------------------
t0=$SECONDS
while :; do
  why=""
  vs=$(gcloud compute instances describe "$VM" $GC --format='value(status)' 2>>"$LOG") || why="gcloud failed"
  [ -z "$why" ] && [ "$vs" != TERMINATED ] && why="VM is $vs"
  for q in $prereq; do
    [ -n "$why" ] && break
    l=$(gcloud storage cat "gs://$BUCKET/results/validation/$q/run_info.txt" 2>>"$LOG" | tail -n 1)
    [[ $l =~ ^end\ .*\ rc\ 0$ ]] || why="prerequisite $q not finished (${l:-no run_info})"
  done
  [ -z "$why" ] && break
  if [ -n "$DRY_RUN" ]; then say "DRY-RUN: not free yet ($why); a real run would poll every 5 min for ${wait_h} h"; break; fi
  (( SECONDS - t0 > wait_h * 3600 )) && { status "ship_case: $VM not free after ${wait_h} h ($why) — $rel NOT started"; exit 1; }
  sleep 300
done

# --- pack, upload, start ------------------------------------------------------------------------------------------
if [ -n "$DRY_RUN" ]; then
  say "DRY-RUN would pack:"; _pack_list "$c" "$N" | sed 's/^/    /'
  say "DRY-RUN would upload to $P/in/, set metadata mode=handoff hard_stop_h=$hard, max-run-duration $((hard + 2))h, start $VM"
  exit 0
fi
tar=$STATE/pack_$tag.tar.gz
pack_case "$c" "$N" "$tar" || { status "ship_case: pack failed"; exit 1; }
sha=$(sha256sum "$tar" | cut -d' ' -f1)
rinfo(){ awk -v k="$1" '$1==k{print $2; exit}' "$c/run_info.txt"; }
end=$(awk '$1=="endTime"{gsub(";","",$2); print $2}' "$c/system/controlDict")
pub=no; [[ $c == $REPO/cases/validation/* ]] && pub=yes   # only repo cases are published to results/validation
printf 'case=%s\ntag=%s\nstep=%s\nnp=%s\ncommit=%s\ndirty=%s\nsha256=%s\nend=%s\npublish=%s\n' "$rel" "$tag" "$N" "$(rinfo np)" "$(rinfo commit)" "$(rinfo dirty_files)" "$sha" "$end" "$pub" > "$STATE/JOB_$VM"
# code of the current commit for the VM (y+ check, follow-up case files); hash goes into the VM's run_info.txt (rule 9)
[ -z "$(git status --porcelain --untracked-files=no -- scripts src cases/validation/ramp24/L2)" ] || say "WARNING: tracked code files differ from HEAD — the VM gets HEAD"
git archive --format=tar.gz -o "$STATE/code.tar.gz" HEAD scripts src cases/validation/ramp24/L2 && git rev-parse HEAD > "$STATE/code.commit" \
  || { status "ship_case: git archive failed"; exit 1; }
clean_bucket "$P" || { status "ship_case: could not clear old markers in $P — $rel NOT started"; exit 1; }
up "$tar" "$P/in/$tag.tar.gz" && up "$STATE/JOB_$VM" "$P/in/JOB" || { status "ship_case: upload failed"; exit 1; }
GQ storage cp scripts/cloud/*.sh "gs://$BUCKET/inputs/cloud/" || { status "ship_case: script upload failed"; exit 1; }
up "$STATE/code.tar.gz" "gs://$BUCKET/inputs/code.tar.gz" && up "$STATE/code.commit" "gs://$BUCKET/inputs/code.commit" || { status "ship_case: code upload failed"; exit 1; }
# optional VM-side follow-up (sourced by handoff_vm.sh after FINISHED); without NEXT_SH an old one is removed
if [ -n "${NEXT_SH:-}" ]; then up "$NEXT_SH" "$P/in/NEXT.sh" || { status "ship_case: NEXT.sh upload failed"; exit 1; }
else gcloud storage rm "$P/in/NEXT.sh" "$P/in/NEXT.env" "$P/in/next_case.tar.gz" >/dev/null 2>&1; fi
echo "shipped $(date -Is) step $N to $VM" >> "$c/run_info.txt"
GQ compute instances add-metadata "$VM" $GC --metadata "mode=handoff,hard_stop_h=$hard" \
  --metadata-from-file startup-script=scripts/cloud/vm_startup.sh || { status "ship_case: add-metadata failed"; exit 1; }
# GCE forces a STOP after max-run-duration (cost guard outside the VM); it must outlast the worker's own hard stop
GQ compute instances set-scheduling "$VM" $GC --max-run-duration="$((hard + 2))h" --instance-termination-action=STOP \
  || say "WARNING: set-scheduling failed — the VM keeps its previous max-run-duration"
GQ compute instances start "$VM" $GC || { status "ship_case: start $VM failed"; exit 1; }
if wait_heartbeat "$P" "$tag" "$N" 1200 && confirm_alive "$P" "$tag" 360; then   # 6 more minutes: 2026-11-12 power-off defect
  printf 'case=%s\ntag=%s\nvm=%s\nstep=%s\nend=%s\ntime=%s\n' "$c" "$tag" "$VM" "$N" "$end" "$(date -Is)" > "$STATE/SHIPPED_$tag"
  status "SHIP OK: $rel is running on $VM ($HB)"
else
  G compute instances stop "$VM" $GC >> "$LOG" 2>&1
  status "ship_case: no running heartbeat from $VM within 20 min (last: ${HB:-none}) — VM stopped, $rel NOT running"
  exit 1
fi
