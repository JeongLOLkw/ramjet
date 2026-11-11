#!/bin/bash
# Copy the results from the bucket into cases/validation:  pull.sh <bucket>
cd "$(dirname "$0")/../.." || exit 1
gcloud storage rsync -r "gs://$1/results/validation" cases/validation
mkdir -p cases/runs/cloud && gcloud storage rsync -r "gs://$1/results" cases/runs/cloud --exclude='^validation/.*'
