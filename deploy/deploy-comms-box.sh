#!/usr/bin/env bash
# Deploy the comms backend from THIS machine to the box, then restart it.
#
# Why this exists: the box (/home/ubuntu/company-urban) is NOT a git checkout —
# it is updated by copying files (same model as sync-box-env.sh). Copying files
# one at a time left it half-synced (a new agents.py beside an old app.py, and a
# missing zubin_core.py), which broke זובין. This script pushes the WHOLE
# comms/backend as one consistent set and restarts the systemd service, so the
# box can never end up with a mismatched mix again.
#
# Usage (from the machine that has the repo + the box key):
#   bash deploy/deploy-comms-box.sh
set -euo pipefail

BOX_IP="${BOX_IP:-44.201.4.142}"
KEY="${BOX_KEY:-$HOME/.ssh/cu_box.pem}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEST="/home/ubuntu/company-urban"
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=no "ubuntu@$BOX_IP")

echo "→ syncing comms/backend/*.py (app, agents, cmd_brain, exec_brain, zubin_core, db)"
scp -i "$KEY" -o StrictHostKeyChecking=no \
  "$REPO"/comms/backend/*.py \
  "ubuntu@$BOX_IP:$DEST/comms/backend/"

echo "→ seeding schedule/Schedule.md only if absent (זובין edits it live on the box)"
"${SSH[@]}" "mkdir -p $DEST/schedule"
if "${SSH[@]}" "test -f $DEST/schedule/Schedule.md"; then
  echo "   Schedule.md already on the box — leaving זובין's live copy untouched"
  echo "   (to capture his edits into the repo/website: bash deploy/pull-schedule-from-box.sh)"
else
  scp -i "$KEY" -o StrictHostKeyChecking=no \
    "$REPO/schedule/Schedule.md" \
    "ubuntu@$BOX_IP:$DEST/schedule/Schedule.md"
fi

echo "→ clearing stale bytecode + restarting the comms service"
"${SSH[@]}" "rm -rf $DEST/comms/backend/__pycache__; sudo systemctl restart comms; sleep 2; systemctl is-active comms"

echo "→ public /agents now reports:"
curl -s https://comms.newavera.co.il/agents || true
echo
echo "✓ done. Sanity check: the JSON above includes a \"roles\" field, and"
echo "  chatting with זובין should respond (no zubin_core.py error)."
echo
echo "NOTE: bespoke cores under Agents/ (ronit_core, ran_core) are NOT synced by"
echo "this script — they rarely change. If you edit one, scp it to the box too."
