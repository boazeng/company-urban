#!/usr/bin/env bash
# Deploy Ran's Telegram bot to the company-urban box as an always-on systemd service.
#
# Why this exists: the bot is a long-polling process (telegram getUpdates) — it is
# NOT a Lambda and NOT part of the `comms` web service. It must run always-on, so it
# gets its own systemd unit. The `comms` service (rooms web backend) is separate and
# is left untouched by this script.
#
# It syncs the bot + its brain to an ASCII path on the box (so the systemd unit has no
# Hebrew path), installs deps in a dedicated venv, installs/refreshes the unit, starts it.
#
# Prereqs:
#   1. The box .env already has RAN_BOT_TOKEN + RAN_TELEGRAM_CHAT_ID + ANTHROPIC_API_KEY
#      + RAN_TOKEN — run `bash deploy/sync-box-env.sh` first if unsure.
#   2. You have the box SSH key (default ~/.ssh/cu_box.pem).
#
# Usage (from the machine that has the repo + the box key):
#   bash deploy/deploy-ran-bot-box.sh
set -euo pipefail

BOX_IP="${BOX_IP:-44.201.4.142}"
KEY="${BOX_KEY:-$HOME/.ssh/cu_box.pem}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
RAN="$REPO/Agents/מנכ״ל/רן"            # source (local) — Hebrew path, quoted everywhere
DEST="/home/ubuntu/company-urban/ran_bot"  # target (box) — ASCII
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=no "ubuntu@$BOX_IP")

echo "→ creating ASCII bot dir on the box: $DEST"
"${SSH[@]}" "mkdir -p '$DEST/RAN_BOT_TELEGRAM'"

echo "→ syncing the brain (ran_core, ran_orchestrator) + the thin telegram channel"
scp -i "$KEY" -o StrictHostKeyChecking=no \
  "$RAN/ran_core.py" "$RAN/ran_orchestrator.py" \
  "ubuntu@$BOX_IP:$DEST/"
scp -i "$KEY" -o StrictHostKeyChecking=no \
  "$RAN/RAN_BOT_TELEGRAM/ran_telegram_bot.py" \
  "$RAN/RAN_BOT_TELEGRAM/requirements.txt" \
  "ubuntu@$BOX_IP:$DEST/RAN_BOT_TELEGRAM/"

echo "→ creating venv + installing deps (python-telegram-bot, requests, icalendar...)"
# If venv creation fails with 'ensurepip is not available', run once on the box:
#   sudo apt-get update && sudo apt-get install -y python3-venv
"${SSH[@]}" "cd '$DEST' && (test -d .venv || python3 -m venv .venv) && \
  .venv/bin/pip install -q --upgrade pip && \
  .venv/bin/pip install -q -r RAN_BOT_TELEGRAM/requirements.txt"

echo "→ installing systemd unit ran-telegram.service"
scp -i "$KEY" -o StrictHostKeyChecking=no \
  "$REPO/deploy/ran-telegram.service" \
  "ubuntu@$BOX_IP:/tmp/ran-telegram.service"
"${SSH[@]}" "sudo mv /tmp/ran-telegram.service /etc/systemd/system/ran-telegram.service && \
  sudo systemctl daemon-reload && \
  sudo systemctl enable ran-telegram && \
  sudo systemctl restart ran-telegram && sleep 2 && \
  systemctl is-active ran-telegram"

echo
echo "✓ done. Ran's Telegram bot should be live now."
echo "  Test:  send '/start' (or 'היי רן') to @Ran_myassist_bot from your phone."
echo "  Note:  the bot starts with drop_pending_updates=True — old queued messages are"
echo "         discarded, so message it again AFTER it's up."
echo "  Logs:  ${SSH[*]} 'journalctl -u ran-telegram -n 50 --no-pager'"
echo "  Stop:  ${SSH[*]} 'sudo systemctl stop ran-telegram'"
