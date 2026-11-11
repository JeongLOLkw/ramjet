#!/bin/bash
# Create the bucket and the worker VMs.  *** Creates billable cloud resources (CLAUDE.md rule 7). ***
# Usage: launch.sh <project> <bucket> "<chains VM A>" "<chains VM B>"
#   e.g. launch.sh project-... ramjet-i4-xxx "flatplate/M2aw flatplate/M5tw05" "flatplate/M6Tw076"
P=$1; BUCKET=$2; A=$3; B=$4; Z=us-central1-a; HARD=${HARD_STOP_H:-26}
S="$(dirname "$0")/vm_startup.sh"
gcloud storage buckets describe "gs://$BUCKET" --project "$P" >/dev/null 2>&1 || \
  gcloud storage buckets create "gs://$BUCKET" --project "$P" --location us-central1 --uniform-bucket-level-access
mk(){ # name type chains
  gcloud compute instances create "$1" --project "$P" --zone $Z --machine-type "$2" \
    --image-family ubuntu-2404-lts-amd64 --image-project ubuntu-os-cloud \
    --boot-disk-size 60GB --boot-disk-type pd-balanced --scopes cloud-platform \
    --metadata "^:^bucket=$BUCKET:chains=$3:hard_stop_h=$HARD" --metadata-from-file startup-script="$S"
}
mk ramjet-i4-a t2d-standard-8 "$A"
[ -n "$B" ] && mk ramjet-i4-b t2d-standard-4 "$B"
