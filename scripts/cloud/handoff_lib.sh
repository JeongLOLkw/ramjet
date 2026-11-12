# Shared helpers for the handoff scripts (sourced, locally and on the VM). Needs $LOG (and $STATE locally) set.
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
export PATH=$PATH:$HOME/google-cloud-sdk/bin
for _v in STATE LOG; do [ -n "${!_v:-}" ] && case ${!_v} in /*) ;; *) printf -v "$_v" %s "$REPO/${!_v}";; esac; done
[ -n "${LOG:-}" ] && mkdir -p "$(dirname "$LOG")"
[ -n "${STATE:-}" ] && mkdir -p "$STATE"

say(){ local l; l="$(date -Is) $*"; echo "$l" >> "${LOG:-/dev/null}"; [ -n "${SAY_QUIET:-}" ] || echo "$l"; }
status(){ [ -n "${DRY_RUN:-}" ] || echo "$(date -Is) $*" > "$STATE/STATUS"; say "STATUS: $*"; }

# gcloud wrapper: with DRY_RUN=1 only prints commands that would change something. GQ = same, output to $LOG.
_dry(){
  [ -n "${DRY_RUN:-}" ] || return 1
  case "$*" in
    "compute instances start"*|"compute instances stop"*|"compute instances add-metadata"*|"compute instances delete"*|"compute instances set-scheduling"*|"storage rm"*|"storage mv"*) ;;
    "storage cp"*|"storage rsync"*) case ${!#} in gs://*) ;; *) return 1;; esac;;
    *) return 1;;
  esac
  say "DRY-RUN gcloud $*"
}
G(){ _dry "$@" && return 0; gcloud "$@"; }
GQ(){ _dry "$@" && return 0; gcloud "$@" >/dev/null 2>>"${LOG:-/dev/null}"; }
# upload with up to 5 tries
up(){ local i; for i in 1 2 3 4 5; do GQ storage cp "$1" "$2" && return 0; sleep 10; done; return 1; }
down(){ local i; for i in 1 2 3 4 5; do gcloud storage cp "$1" "$2" >/dev/null 2>>"${LOG:-/dev/null}" && return 0; sleep 10; done; return 1; }
put_text(){ local t; t=$(mktemp); printf '%s\n' "$1" > "$t"; up "$t" "$2"; local r=$?; rm -f "$t"; return $r; }
# detached start (closes the lock fds so a long-running child does not hold flock)
detach(){ setsid nohup "$@" >> "${LOG:-/dev/null}" 2>&1 9>&- < /dev/null & }

# Remove the markers of an earlier job under gs://.../handoff/<vm> and CHECK they are gone: a stale RECALL would stop
# the new job at once and a stale HEARTBEAT could be mistaken for the new one.  clean_bucket <P>
clean_bucket(){
  [ -n "${DRY_RUN:-}" ] && { say "DRY-RUN would remove $1/out/** and $1/RECALL"; return 0; }
  gcloud storage rm -r "$1/out" >/dev/null 2>&1; gcloud storage rm "$1/RECALL" >/dev/null 2>&1
  local left; left=$(gcloud storage ls "$1/out/**" "$1/RECALL" 2>/dev/null)
  [ -z "$left" ] || { say "clean_bucket: still there: $(tr '\n' ' ' <<<"$left")"; return 1; }
}
# Wait until the VM reports a running solver of THIS job past step N.  wait_heartbeat <P> <tag> <N> <max s>; sets HB
wait_heartbeat(){
  local t0=$SECONDS s; HB=""
  while (( SECONDS - t0 < $4 )); do
    sleep 20
    HB=$(gcloud storage cat "$1/out/HEARTBEAT" 2>/dev/null) || continue
    s=$(sed -n 's/.*step=\([0-9]*\).*/\1/p' <<<"$HB")
    [[ $HB == *state=running* ]] && [[ " $HB " == *" tag=$2 "* ]] && [ "${s:-0}" -gt "$3" ] && return 0
  done
  return 1
}
# After a first good heartbeat: watch for <max s> more; fail if the VM leaves RUNNING, the heartbeat belongs to another
# job or reports no running solver, or the step did not advance over the whole period.  confirm_alive <P> <tag> <max s>
confirm_alive(){
  local t0=$SECONDS vs s s0
  s0=$(sed -n 's/.*step=\([0-9]*\).*/\1/p' <<<"$HB")
  while (( SECONDS - t0 < $3 )); do
    sleep 30
    vs=$(gcloud compute instances describe "$VM" --zone "$ZONE" --project "$PROJECT" --format='value(status)' 2>/dev/null) || continue
    [ "$vs" = RUNNING ] || { HB="VM is $vs"; return 1; }
    HB=$(gcloud storage cat "$1/out/HEARTBEAT" 2>/dev/null) || continue
    [[ " $HB " == *" tag=$2 "* ]] && [[ $HB == *state=running* || $HB == *state=done* ]] || return 1
  done
  s=$(sed -n 's/.*step=\([0-9]*\).*/\1/p' <<<"$HB"); [ "${s:-0}" -gt "${s0:-0}" ]
}

# ---- case inspection -------------------------------------------------------------------------------------
_times(){ ls -1 "$1" 2>/dev/null | grep -E '^[1-9][0-9]*$' | sort -rn; }   # numeric time dirs > 0, newest first
_n(){ ls -A "$1" | wc -l; }
# Largest time present in ALL processor* whose entry count equals that of the previous checkpoint (or the only one).
latest_complete_step(){
  local c=$1 t p prev ok
  for t in $(_times "$c/processor0"); do
    ok=1
    for p in "$c"/processor*; do
      [ -d "$p/$t" ] || { ok=0; break; }
      prev=$(_times "$p" | awk -v t="$t" '$1<t{print; exit}')
      [ -z "$prev" ] || [ "$(_n "$p/$t")" = "$(_n "$p/$prev")" ] || { ok=0; break; }
    done
    [ $ok = 1 ] && { echo "$t"; return; }
  done
}
# Last "Time = N" in log.solver (optionally only after the first <skip> lines: a log carried over from elsewhere).
case_step(){ tail -n +$(( ${2:-0} + 1 )) "$1/log.solver" 2>/dev/null | grep -a '^Time = ' | tail -n 1 | awk '{print $3}'; }
# Seconds per step from the ClockTime of the last n steps (only the latest uninterrupted run segment); "NA" if unknown.
sps_from_log(){
  tail -n $(( ${2:-500} * 40 )) "$1/log.solver" 2>/dev/null | grep -ao 'ClockTime = [0-9]*' | tail -n $(( ${2:-500} + 1 )) |
    awk '{v=$3; if (n && v<last) {n=0}; if (!n) first=v; last=v; n++} END{if (n>1) printf "%.2f\n",(last-first)/(n-1); else print "NA"}'
}
# Wait for a NEW complete checkpoint (newer than at call time) and for log.solver to be >= 2 steps beyond it.
wait_checkpoint(){
  local c=$1 max=$2 skip=${3:-0} base s t0=$SECONDS
  base=$(latest_complete_step "$c"); base=${base:-0}
  while (( SECONDS - t0 < max )); do
    s=$(latest_complete_step "$c")
    if [ -n "$s" ] && [ "$s" -gt "$base" ]; then
      t=$(case_step "$c" "$skip"); [ -n "$t" ] && [ "$t" -ge $((s + 2)) ] && { echo "$s"; return 0; }
    fi
    sleep 5
  done
  latest_complete_step "$c"; return 1
}

# ---- stopping --------------------------------------------------------------------------------------------
# pids whose cwd is exactly dir $1 and whose process name matches regex $2
_pids_in(){ local d p; d=$(realpath "$1"); for p in /proc/[0-9]*; do p=${p#/proc/}
  [ "$(readlink "/proc/$p/cwd" 2>/dev/null)" = "$d" ] && [[ $(cat "/proc/$p/comm" 2>/dev/null) =~ $2 ]] && echo "$p"; done; return 0; }
case_mpirun_pids(){ _pids_in "$1" '^(mpirun|mpiexec|orterun|prterun)$'; }
# remove time dirs newer than step $2 (incomplete writes)
prune_newer(){ local p t; [ -n "$2" ] || return 0
  for p in "$1"/processor*; do for t in $(_times "$p"); do [ "$t" -gt "$2" ] && rm -rf "${p:?}/$t"; done; done; return 0; }
# true if pid runs "<shell> <path>/{Allrun,Allrestart.sh,run_i4.sh,local_resume.sh} ..." (not "bash -c '...text...'")
_is_runner(){ local -a av; mapfile -d '' -t av < "/proc/$1/cmdline" 2>/dev/null
  [[ ${av[0]##*/} =~ ^(ba)?sh$ ]] && [[ ${av[1]##*/} =~ ^(Allrun|Allrestart\.sh|run_i4\.sh|local_resume\.sh)$ ]]; }
stop_case(){
  local c=$1 step=$2 m a pp k i
  local -a mp; mapfile -t mp < <(case_mpirun_pids "$c")
  if [ ${#mp[@]} -gt 0 ]; then
    local -a anc=()   # parent scripts, innermost first; collected BEFORE signalling (a killed child disappears from /proc)
    for m in "${mp[@]}"; do
      a=$m
      while pp=$(sed 's/.*) //' "/proc/$a/stat" 2>/dev/null | awk '{print $2}'); [ -n "$pp" ] && [ "$pp" -gt 1 ]; do
        _is_runner "$pp" && anc+=("$pp")
        a=$pp
      done
    done
    for ((i=${#anc[@]}-1; i>=0; i--)); do say "stop_case: SIGTERM parent script ${anc[i]}"; kill -TERM "${anc[i]}" 2>/dev/null; done   # outermost first
    say "stop_case: SIGTERM mpirun ${mp[*]}"; kill -TERM "${mp[@]}" 2>/dev/null
    for i in $(seq 30); do [ -z "$(_pids_in "$c" '^(hisa|mpirun)$')" ] && break; sleep 1; done
    k=$(_pids_in "$c" '^(hisa|mpirun)$' | tr '\n' ' ')
    [ -n "$k" ] && { say "stop_case: SIGKILL leftovers $k"; kill -KILL $k 2>/dev/null; sleep 1; }
  fi
  prune_newer "$c" "$step"
}

# ---- packing ---------------------------------------------------------------------------------------------
# Paths (relative to the case) that go into a tar; step = one checkpoint or ALL
_pack_list(){ ( cd "$1" || exit 1; local e p t
  for e in system constant 0.orig Allrun case_info.txt run_info.txt log.* postProcessing; do [ -e "$e" ] && echo "$e"; done
  for p in processor*; do [ -d "$p" ] || continue; [ -d "$p/constant" ] && echo "$p/constant"
    if [ "$2" = ALL ]; then for t in $(_times "$p") 0; do [ -d "$p/$t" ] && echo "$p/$t"; done; else [ -d "$p/$2" ] && echo "$p/$2"; fi
  done ) }
_pack(){ _pack_list "$1" "$2" | tar czf "$3" -C "$1" -T -; [ $? -le 1 ]; }   # rc 1 = "file changed while read" (log growing)
pack_case(){ _pack "$1" "$2" "$3"; }
pack_case_final(){ _pack "$1" ALL "$2"; }
