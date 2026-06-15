#!/usr/bin/env bash
# Entrypoint for the deep-research worker container.
# Runs the full deep research headless, prints the report, and (if a comms room
# is given) posts it back into that room. No chat timeout — this is the job.
set -euo pipefail

: "${TOPIC:?TOPIC env required (the market/topic to research)}"
: "${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY env required}"
CMD="${CMD:-/dafna}"
AGENT="${AGENT:-דפנה}"
COMMS_API="${COMMS_API:-}"   # e.g. https://comms.newavera.co.il
ROOM_ID="${ROOM_ID:-}"

cd "${VAULT:-/vault}"
# Remove CLAUDECODE so claude -p doesn't refuse as a "nested session".
unset CLAUDECODE 2>/dev/null || true

echo "→ deep research starting: ${TOPIC}"
PROMPT="${CMD} ${TOPIC}

(מצב: דוח מלא — בצע את המחקר המעמיק המלא)"

# --dangerously-skip-permissions: this is a single-purpose isolated container, so
# all of דפנה's declared tools (WebSearch/WebFetch/Read/Write/Bash) run unattended.
if REPORT="$(claude -p "${PROMPT}" --dangerously-skip-permissions 2>&1)"; then
  status="ok"
else
  status="failed"
fi

echo "===== REPORT (${status}) ====="
printf '%s\n' "${REPORT}"
echo "================================"

# Optional: post the finished report back into a comms room (Phase 3 adds the
# /rooms/{id}/post endpoint on the comms backend). Skipped if not configured.
if [ -n "${COMMS_API}" ] && [ -n "${ROOM_ID}" ]; then
  if [ "${status}" = "ok" ]; then
    text="✅ סיימתי את המחקר המעמיק:

${REPORT}"
  else
    text="(${AGENT}: המחקר נכשל — ${REPORT})"
  fi
  body="$(jq -n --arg a "${AGENT}" --arg t "${text}" '{agent:$a, text:$t}')"
  if curl -fsS -X POST "${COMMS_API}/rooms/${ROOM_ID}/post" \
        -H 'Content-Type: application/json' -d "${body}" >/dev/null; then
    echo "→ posted report to room ${ROOM_ID}"
  else
    echo "→ postback failed (non-fatal)"
  fi
fi

[ "${status}" = "ok" ]
