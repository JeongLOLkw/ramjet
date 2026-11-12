#!/bin/bash
# GCE startup script (runs as root at every boot, idempotent). Settings come from instance metadata:
#   bucket, chains (space separated case bases), hard_stop_h.
exec >> /var/log/i4-startup.log 2>&1
md(){ curl -s -H Metadata-Flavor:Google "http://metadata.google.internal/computeMetadata/v1/instance/attributes/$1"; }
BUCKET=$(md bucket); CHAINS=$(md chains); HARD=$(md hard_stop_h)
MODE=$(curl -sf -H Metadata-Flavor:Google "http://metadata.google.internal/computeMetadata/v1/instance/attributes/mode")   # -f: missing key -> empty
echo "=== startup $(date -Is) bucket=$BUCKET chains=$CHAINS hard=$HARD mode=${MODE:-worker}"
export DEBIAN_FRONTEND=noninteractive
# --- power-off guard (D-019) -------------------------------------------------------------------------------------
# 2026-11-12 rehearsal: the VM powered itself off 3 min after a handed-over job had started. Whatever armed
# i4-poweroff.service (a stale WORKER_DONE of the previous job is the suspect), nothing stopped the already running
# `sleep 180; poweroff`. So, before anything else: record what this boot found, stop the timer service too, remove the
# stale marker and stamp the boot. The service below powers off only for a marker written AFTER this stamp and only
# once the worker has exited.
WD=/home/toto/ramjet/cases/runs/WORKER_DONE
echo "pre-state: WORKER_DONE=$([ -e $WD ] && echo "present ($(cat $WD))" || echo absent)" \
     "poweroff.service=$(systemctl is-active i4-poweroff.service) poweroff.path=$(systemctl is-active i4-poweroff.path)" \
     "worker=$(systemctl is-active i4-worker.service)" \
     "enabled=$(systemctl is-enabled i4-poweroff.path i4-poweroff.service i4-worker.service 2>&1 | tr '\n' ' ')"
echo "--- i4 units, previous boot:"; journalctl -b -1 -u i4-poweroff.service -u i4-poweroff.path -u i4-worker.service --no-pager 2>&1 | tail -n 40
echo "--- i4 units, this boot so far:"; journalctl -b 0 -u i4-poweroff.service -u i4-poweroff.path -u i4-worker.service --no-pager 2>&1 | tail -n 20
systemctl stop i4-poweroff.path i4-poweroff.service i4-worker.service 2>/dev/null
systemctl disable i4-poweroff.path i4-worker.service 2>/dev/null
rm -f $WD; touch /run/i4-boot-stamp
command -v gcloud >/dev/null || snap install google-cloud-cli --classic
id toto >/dev/null 2>&1 || useradd -m -s /bin/bash toto
if [ ! -d /usr/lib/openfoam/openfoam2512 ]; then
  apt-get update -y
  apt-get install -y git time curl ca-certificates
  curl -s https://dl.openfoam.com/add-debian-repo.sh | bash
  apt-get update -y
  apt-get install -y openfoam2512-default
fi
if [ ! -d /home/toto/ramjet ]; then
  cd /home/toto || exit 1
  gcloud storage cp "gs://$BUCKET/inputs/*.tar.gz" . || exit 1
  tar xzf repo.tar.gz && tar xzf hisa.tar.gz && tar xzf cases.tar.gz -C ramjet
  chown -R toto:toto /home/toto
fi
# (A worker that systemd may have started at boot from an older unit was stopped above: exactly one worker runs.)
# Code of the current commit (scripts/, src/, ramp L2 case files; `git archive` made by handoff.sh, hash in
# inputs/code.commit) — the repo unpacked at VM creation is older. Only tracked files are overwritten.
if gcloud storage cp "gs://$BUCKET/inputs/code.tar.gz" "gs://$BUCKET/inputs/code.commit" /tmp/ 2>/dev/null; then
  # --no-same-owner + chown: extracting as root must not hand cases/ and cases/validation/ to root (2026-11-12
  # rehearsal: the worker could then not create a new case directory there)
  tar xzf /tmp/code.tar.gz --no-same-owner -C /home/toto/ramjet && cp /tmp/code.commit /home/toto/ramjet/cases/runs/code.commit
  chown toto:toto /home/toto/ramjet /home/toto/ramjet/cases /home/toto/ramjet/cases/validation
  chown -R toto:toto /home/toto/ramjet/scripts /home/toto/ramjet/src /home/toto/ramjet/cases/runs /home/toto/ramjet/cases/validation/ramp24 2>/dev/null
  echo "code refreshed to commit $(cat /tmp/code.commit)"
fi
# numpy for scripts/yplus_check.py on the VM (rule 2 gate between levels); own unit so a busy dpkg lock cannot delay the job
python3 -c 'import numpy' 2>/dev/null || systemd-run --unit=i4-numpy --no-block apt-get -o DPkg::Lock::Timeout=900 install -y python3-numpy
# Cloud scripts follow the latest committed copy in the bucket (orchestration only; solver/case files untouched).
if gcloud storage ls "gs://$BUCKET/inputs/cloud/" >/dev/null 2>&1; then
  gcloud storage cp "gs://$BUCKET/inputs/cloud/*.sh" /home/toto/ramjet/scripts/cloud/ && \
    chmod +x /home/toto/ramjet/scripts/cloud/*.sh && chown -R toto:toto /home/toto/ramjet/scripts/cloud
fi
# A boot means "run (or finish) the job": the stale end marker was removed at the top (power-off guard).
rm -f $WD
# mode=handoff: continue one handed-over running case (handoff_vm.sh); otherwise the chain worker as before.
if [ "$MODE" = handoff ]; then EXEC="/home/toto/ramjet/scripts/cloud/handoff_vm.sh $BUCKET $HARD"
else EXEC="/home/toto/ramjet/scripts/cloud/worker.sh $BUCKET $HARD $CHAINS"; fi
cat > /etc/systemd/system/i4-worker.service <<UNIT
[Unit]
Description=I4 cloud worker
After=network-online.target
[Service]
User=toto
ExecStart=$EXEC
Restart=on-failure
RestartSec=60
UNIT
# Power off 3 min after the worker writes WORKER_DONE (final sync is done before it). Not enabled at boot on
# purpose: only this script starts it, after the stale marker is removed.
cat > /etc/systemd/system/i4-poweroff.path <<UNIT
[Path]
PathExists=/home/toto/ramjet/cases/runs/WORKER_DONE
UNIT
cat > /etc/systemd/system/i4-poweroff.service <<UNIT
[Service]
Type=oneshot
ExecStart=/bin/bash -c 'sleep 180; [ $WD -nt /run/i4-boot-stamp ] || { echo "power-off skipped: WORKER_DONE missing or older than this boot"; exit 0; }; while systemctl is-active -q i4-worker.service; do sleep 10; done; systemctl poweroff'
UNIT
systemctl daemon-reload
systemctl start i4-poweroff.path
systemctl start i4-worker.service
echo "=== startup done $(date -Is)"
gcloud storage cp /var/log/i4-startup.log "gs://$BUCKET/diag/$(hostname)/i4-startup.log" >/dev/null 2>&1   # readable without SSH
