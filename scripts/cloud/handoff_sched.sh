#!/bin/bash
# Run handoff.sh at <HH:MM handoff> and restore.sh at <HH:MM restore> (today's local time; a restore time before the
# handoff time means tomorrow). Only compares the clock every 30 s, so it survives the laptop sleeping.
# Test hooks: HANDOFF_CMD / RESTORE_CMD override the commands.
cd "$(dirname "$0")/../.." || exit 1
source scripts/cloud/handoff.conf; source scripts/cloud/handoff_lib.sh
export STATE LOG SAY_QUIET=1
H=$(date -d "$1" +%s) || exit 2; R=$(date -d "$2" +%s) || exit 2; [ "$R" -le "$H" ] && R=$((R + 86400))
HC=${HANDOFF_CMD:-scripts/cloud/handoff.sh}; RC=${RESTORE_CMD:-scripts/cloud/restore.sh}
SAY_QUIET="" say "handoff_sched start: handoff at $(date -d @$H +%F\ %T), restore at $(date -d @$R +%F\ %T)"
restore_launched=""
while :; do
  now=$(date +%s)
  if [ "$now" -ge "$H" ] && [ ! -e "$STATE/handoff.started" ] && [ -z "$h_ran" ]; then
    h_ran=1; say "handoff time reached: $HC"; $HC >> "$LOG" 2>&1; say "handoff command returned rc=$?"
  fi
  if [ "$now" -ge "$R" ] && [ -z "$restore_launched" ] && [ ! -e "$STATE/restore.started" ] && flock -n "$STATE/lock" true; then
    restore_launched=1; say "restore time reached: $RC"; setsid nohup $RC >> "$LOG" 2>&1 9>&- < /dev/null &
  fi
  { [ -n "$restore_launched" ] || [ -e "$STATE/restore.started" ]; } && { [ -e "$STATE/handoff.started" ] || [ -n "$h_ran" ]; } && break
  sleep "${SCHED_POLL:-30}"
done
say "handoff_sched done"
