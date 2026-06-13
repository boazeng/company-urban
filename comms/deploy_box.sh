#!/usr/bin/env bash
# Pull the latest repo and cleanly restart the comms backend on the box (Linux).
#
# Why this exists: the box was getting half-synced (e.g. a new agents.py next to
# an old app.py, and a missing zubin_core.py) — a partial file copy, not a clean
# pull. That leaves the API serving an inconsistent mix. This script brings ALL
# files to one commit and fully restarts uvicorn (killing orphaned --reload
# children that otherwise keep serving stale code).
#
# Usage on the box:
#   bash comms/deploy_box.sh
set -euo pipefail

cd "$(dirname "$0")/.."          # repo root
export VAULT="${VAULT:-$PWD}"    # zubin_core/cmd_brain read VAULT (Schedule.md, /conductor cwd)

echo "→ git pull (bring every file to the same latest commit)"
git pull --ff-only origin main

echo "→ stopping any running comms backend (incl. orphaned --reload children)"
pkill -f "uvicorn app:app" 2>/dev/null || true
sleep 1

echo "→ starting comms backend on :5181 (no --reload — avoids stale orphans)"
cd comms/backend
nohup python3 -m uvicorn app:app --port 5181 >> comms.box.log 2>&1 &
sleep 2

echo "→ /agents now reports:"
curl -s http://127.0.0.1:5181/agents || true
echo
echo "✓ done. Sanity check: the JSON above should include a \"roles\" field, and"
echo "  chatting with זובין should no longer raise a zubin_core.py error."
