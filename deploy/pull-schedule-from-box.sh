#!/usr/bin/env bash
# Pull the box's live Schedule.md back into the repo.
#
# זובין edits the schedule on the box (add/remove/update events), so the box copy
# is the live source of truth. Run this when you want those changes reflected in
# git and on the website (which inlines schedule/Schedule.md at build time).
#
# Usage (from the machine with the repo + box key):
#   bash deploy/pull-schedule-from-box.sh
#   git diff schedule/Schedule.md   # review זובין's changes
#   git add schedule/Schedule.md && git commit && git push   # publish to the website
set -euo pipefail

BOX_IP="${BOX_IP:-44.201.4.142}"
KEY="${BOX_KEY:-$HOME/.ssh/cu_box.pem}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"

scp -i "$KEY" -o StrictHostKeyChecking=no \
  "ubuntu@$BOX_IP:/home/ubuntu/company-urban/schedule/Schedule.md" \
  "$REPO/schedule/Schedule.md"

echo "✓ pulled box Schedule.md → repo."
echo "  Review:  git diff schedule/Schedule.md"
echo "  Publish: git add schedule/Schedule.md && git commit && git push  (rebuilds the website)"
