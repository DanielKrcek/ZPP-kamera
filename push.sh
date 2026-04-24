#!/usr/bin/env bash
set -euo pipefail

# Push the repo to the Unitree Go2 over the direct link.
# Usage: ./push.sh [user@host] [remote-path]

REMOTE="${1:-unitree@192.168.123.18}"
REMOTE_PATH="${2:-~/spanish-inquisition}"

rsync -avz --delete --partial \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='.idea/' \
  --exclude='.vscode/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='unitree-go2-research/' \
  ./ "${REMOTE}:${REMOTE_PATH}/"
