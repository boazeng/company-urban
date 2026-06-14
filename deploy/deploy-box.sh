#!/usr/bin/env bash
# Full box deploy in one shot — everything the box needs, from any machine with
# ssh+tar (Windows Git Bash included) and in CI. NO rsync dependency.
#
# Syncs the vault subset the box runs on (comms backend, slash-command engines,
# bespoke cores + STYLE files, and the context dirs agents read), (re)deploys
# Ran's Telegram bot, and restarts the services.
#
# PRESERVED on the box (never overwritten, never in the transfer set):
#   • schedule/Schedule.md — זובין live-edits it on the box
#   • output/              — runtime data (rooms, logs, agent outputs)
#   • .env                 — secrets (managed by deploy/sync-box-env.sh)
#
# Usage:  bash deploy/deploy-box.sh        (run by CI on push, or by hand)
set -euo pipefail

BOX_IP="${BOX_IP:-44.201.4.142}"
KEY="${BOX_KEY:-$HOME/.ssh/cu_box.pem}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEST="/home/ubuntu/company-urban"
RAN_SRC="$DEST/Agents/מנכ״ל/רן"   # the Hebrew path, evaluated ON the box (Linux UTF-8 = fine)
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=no "ubuntu@$BOX_IP")
cd "$REPO"

echo "→ [1/4] syncing vault subset (tar-over-ssh, with excludes — no rsync needed)"
tar czf - \
  --exclude='__pycache__' --exclude='*.pyc' --exclude='*.bak' \
  --exclude='.venv' --exclude='node_modules' \
  comms .claude/commands Agents goals brands structure interfaces deploy \
  | "${SSH[@]}" "mkdir -p '$DEST' && tar xzf - -C '$DEST'"

echo "→ [2/4] seeding Schedule.md only if absent (זובין's live copy is left untouched)"
if "${SSH[@]}" "mkdir -p '$DEST/schedule' && test -f '$DEST/schedule/Schedule.md'"; then
  echo "   present — left untouched"
else
  tar czf - schedule/Schedule.md | "${SSH[@]}" "tar xzf - -C '$DEST'"
  echo "   seeded (was absent)"
fi

echo "→ [3/4] refreshing Ran's Telegram bot (ASCII ran_bot/) from the synced cores"
"${SSH[@]}" "set -e
  mkdir -p '$DEST/ran_bot/RAN_BOT_TELEGRAM'
  cp '$RAN_SRC/ran_core.py' '$RAN_SRC/ran_orchestrator.py' '$DEST/ran_bot/'
  cp '$RAN_SRC/RAN_BOT_TELEGRAM/ran_telegram_bot.py' '$RAN_SRC/RAN_BOT_TELEGRAM/requirements.txt' '$DEST/ran_bot/RAN_BOT_TELEGRAM/'
  cd '$DEST/ran_bot'
  test -d .venv || python3 -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r RAN_BOT_TELEGRAM/requirements.txt
  sudo cp '$DEST/deploy/ran-telegram.service' /etc/systemd/system/ran-telegram.service"

echo "→ [4/4] clearing bytecode, reloading systemd, restarting services"
"${SSH[@]}" "rm -rf '$DEST/comms/backend/__pycache__'
  sudo systemctl daemon-reload
  sudo systemctl restart comms
  sudo systemctl enable ran-telegram >/dev/null 2>&1 || true
  sudo systemctl restart ran-telegram
  sleep 2
  echo \"   comms=\$(systemctl is-active comms) ran-telegram=\$(systemctl is-active ran-telegram)\""

echo "→ public /agents now reports:"
curl -s "https://comms.newavera.co.il/agents" | head -c 500 || true
echo
echo "✓ box fully deployed (comms + command engines + cores + Ran bot)."
echo "  Sanity: the /agents JSON above should now include \"דרור\","
echo "  and ran-telegram should be active. Send '/start' to @Ran_myassist_bot."