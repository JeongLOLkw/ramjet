#!/bin/bash
# GCE startup script (runs as root at every boot, idempotent). Settings come from instance metadata:
#   bucket, chains (space separated case bases), hard_stop_h.
exec >> /var/log/i4-startup.log 2>&1
md(){ curl -s -H Metadata-Flavor:Google "http://metadata.google.internal/computeMetadata/v1/instance/attributes/$1"; }
BUCKET=$(md bucket); CHAINS=$(md chains); HARD=$(md hard_stop_h)
echo "=== startup $(date -Is) bucket=$BUCKET chains=$CHAINS hard=$HARD"
export DEBIAN_FRONTEND=noninteractive
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
cat > /etc/systemd/system/i4-worker.service <<UNIT
[Unit]
Description=I4 cloud worker
After=network-online.target
[Service]
User=toto
ExecStart=/home/toto/ramjet/scripts/cloud/worker.sh $BUCKET $HARD $CHAINS
Restart=on-failure
RestartSec=60
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now i4-worker.service
echo "=== startup done $(date -Is)"
