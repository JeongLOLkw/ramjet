#!/bin/bash
# Pack what the VMs need and upload it to the bucket:  bundle.sh <bucket> <case base>...   e.g. flatplate/M2aw ...
# Needs a clean, committed repo (rule 9: the commit hash of the code is recorded on the VM too).
set -e
BUCKET=$1; shift
cd "$(dirname "$0")/../.."
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "tracked files modified - commit first"; exit 1; }
T=$(mktemp -d); echo "commit $(git rev-parse HEAD)"
tar czf $T/repo.tar.gz --exclude='ramjet/cases' --exclude='__pycache__' -C .. ramjet
tar czf $T/hisa.tar.gz -C "$HOME" OpenFOAM/toto-v2512
files=()
for b in "$@"; do files+=("cases/validation/${b}_L0" "cases/validation/${b}_L1" "cases/validation/${b}_L2"); done
tar czf $T/cases.tar.gz --exclude='processor*' "${files[@]}"
ls -la $T
gcloud storage cp $T/repo.tar.gz $T/hisa.tar.gz $T/cases.tar.gz "gs://$BUCKET/inputs/"
rm -rf $T
