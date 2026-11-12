# VM-side follow-up, SOURCED by handoff_vm.sh right after its job ended FINISHED (uploaded as handoff/<vm>/in/NEXT.sh).
# Runs the next grid level on the same VM with no laptop in the loop (decisions.md D-019):
#   1. y+ check of the finished case (CLAUDE.md rule 2) — a failure stops the chain, the next level is NOT started
#   2. prepare the next case: mesh, initial field mapped from the finished solution (D-016 (3), pre-approved
#      adjustment (c)), decomposition — the case's own `PREP_ONLY=1 Allrun`, nothing else
#   3. run it under the same supervision as the first job (run_case: heartbeat, checkpoint upload, hard stop)
# No physical/numerical setting, mesh or step count is touched here.
# Uses from handoff_vm.sh: BUCKET P W C rel tag, say marker run_case publish sync_log up down GQ.
# Default: ramp24/L1 -> ramp24/L2 (case files come with inputs/code.tar.gz). A rehearsal overrides this with
# handoff/<vm>/in/NEXT.env (next_rel=<case rel on the VM>) and in/next_case.tar.gz (the unprepared case files).
# Idempotent: after a reboot handoff_vm.sh ends FINISHED again at once and this script continues where it was.
next_main(){
  local prev_c=$C prev_rel=$rel prev_tag=$tag next_rel="" c2 t yp i
  if gcloud storage ls "$P/in/NEXT.env" >/dev/null 2>&1 && down "$P/in/NEXT.env" "$W/NEXT.env"; then
    next_rel=$(sed -n 's/^next_rel=//p' "$W/NEXT.env"); fi
  [ -z "$next_rel" ] && [ "$prev_rel" = ramp24/L1 ] && next_rel=ramp24/L2
  [ -n "$next_rel" ] || { say "NEXT: no follow-up defined for $prev_rel"; return 0; }
  c2=$PWD/cases/validation/$next_rel
  say "NEXT: $prev_rel -> $next_rel"

  # out/FINISHED must mean "the whole chain is finished": keep the first job's result under its own names
  for i in FINISHED LATEST; do gcloud storage mv "$P/out/$i" "$P/out/${i}_$prev_tag" >/dev/null 2>&1; done
  gcloud storage mv "$P/out/latest.tar.gz" "$P/out/final_$prev_tag.tar.gz" >/dev/null 2>&1
  terminal=""

  # 1. y+ of the finished case (reconstructed latest time). numpy is installed by vm_startup.sh in the background.
  # The check reads the cell centres 0/Cx, 0/Cy; a handed-over pack made before 2026-11-12 has no 0/ directory, so
  # write them again exactly as the case's Allrun does (mesh only, no field is used or changed).
  if [ ! -e "$prev_c/0/Cx" ]; then
    ( cd "$prev_c" && { [ -d 0 ] || cp -r 0.orig 0; } && postProcess -func writeCellCentres -time 0 > log.cc.vm 2>&1 ) \
      || say "NEXT: WARNING writeCellCentres failed in $prev_rel (see log.cc.vm)"; fi
  t=$(ls "$prev_c" | grep -E '^[0-9]+$' | sort -n | tail -n 1)
  for i in $(seq 90); do python3 -c 'import numpy' 2>/dev/null && break; sleep 10; done
  python3 scripts/yplus_check.py "$prev_c" "$t" wall > "$prev_c/log.yplus" 2>&1; yp=$?
  GQ storage cp "$prev_c/log.yplus" "$P/out/log.yplus_$prev_tag"
  say "NEXT: y+ check of $prev_rel at time $t: rc=$yp ($(tail -n 1 "$prev_c/log.yplus"))"
  echo "yplus $(date -Is) time $t rc $yp host $(hostname)" >> "$prev_c/run_info.txt"
  if [ $yp -ne 0 ]; then marker FAILED "rc=yplus_$yp tag=$prev_tag (next level $next_rel NOT started)"; return 0; fi
  publish "$prev_c" "$prev_rel"   # again, now with log.yplus

  # 2. prepare the next case (skipped if it is already decomposed, i.e. after a reboot)
  if [ ! -d "$c2/processor0" ]; then
    if [ ! -x "$c2/Allrun" ] && gcloud storage ls "$P/in/next_case.tar.gz" >/dev/null 2>&1; then
      down "$P/in/next_case.tar.gz" "$W/next_case.tar.gz" && mkdir -p "$c2" && tar xzf "$W/next_case.tar.gz" -C "$c2"; fi
    [ -x "$c2/Allrun" ] || { marker FAILED "rc=no case files for $next_rel"; return 0; }
    say "NEXT: preparing $next_rel (blockMesh, mapFields from $prev_rel, decomposePar)"
    if ! INIT_FROM="$prev_c" PREP_ONLY=1 "$c2/Allrun"; then
      for i in blockMesh checkMesh cc mapFields decomposePar; do
        [ -e "$c2/log.$i" ] && { tail -n 60 "$c2/log.$i" > "$W/log.$i.tail"; GQ storage cp "$W/log.$i.tail" "$P/out/prep_log.$i.tail"; }; done
      marker FAILED "rc=prepare tag=${next_rel//\//_}"; return 0
    fi
    [ -s cases/runs/code.commit ] && echo "vm-code-commit $(cat cases/runs/code.commit) host $(hostname) $(date -Is)" >> "$c2/run_info.txt"
    say "NEXT: prepared ($(grep -c . "$c2/log.mapFields") lines in log.mapFields, $(ls -d "$c2"/processor* | wc -l) processor dirs)"
  else say "NEXT: $next_rel is already decomposed — resuming"; fi
  sync_log

  # 3. run it
  rel=$next_rel
  run_case "$c2" "${next_rel//\//_}"
  if [ "$terminal" = FINISHED ]; then
    t=$(ls "$c2" | grep -E '^[0-9]+$' | sort -n | tail -n 1)
    python3 scripts/yplus_check.py "$c2" "$t" wall > "$c2/log.yplus" 2>&1; yp=$?
    GQ storage cp "$c2/log.yplus" "$P/out/log.yplus_$tag"
    say "NEXT: y+ check of $next_rel at time $t: rc=$yp ($(tail -n 1 "$c2/log.yplus"))"
    echo "yplus $(date -Is) time $t rc $yp host $(hostname)" >> "$c2/run_info.txt"
    publish "$c2" "$next_rel"
  fi
}
next_main
