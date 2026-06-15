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
# S3 persistence: an agent's deliverables live under s3://<bucket>/<slug>/.
# Slug defaults to the command name (/dafna → dafna), matching its output/ dir.
AGENT_OUTPUT_BUCKET="${AGENT_OUTPUT_BUCKET:-}"
OUTPUT_SLUG="${OUTPUT_SLUG:-${CMD#/}}"

cd "${VAULT:-/vault}"
OUTPUT_DIR="output/${OUTPUT_SLUG}"
S3_PREFIX=""
[ -n "${AGENT_OUTPUT_BUCKET}" ] && S3_PREFIX="s3://${AGENT_OUTPUT_BUCKET}/${OUTPUT_SLUG}/"
# Remove CLAUDECODE so claude -p doesn't refuse as a "nested session".
unset CLAUDECODE 2>/dev/null || true

# Pull the agent's prior materials so it can reference/build on them (non-fatal:
# first run has nothing, and a sync hiccup shouldn't block the research).
if [ -n "${S3_PREFIX}" ]; then
  mkdir -p "${OUTPUT_DIR}"
  if aws s3 sync "${S3_PREFIX}" "${OUTPUT_DIR}/" --only-show-errors; then
    echo "→ pulled prior materials from ${S3_PREFIX}"
  else
    echo "→ no prior materials / pull failed (non-fatal)"
  fi
fi

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

# Persist the agent's deliverables to S3 so they survive this ephemeral container
# (and are available to the next run). Only on success — a failed run may have left
# a half-written dir. Non-fatal: the report still posts back even if the sync fails.
saved_note=""
if [ "${status}" = "ok" ] && [ -n "${S3_PREFIX}" ] && [ -d "${OUTPUT_DIR}" ]; then
  if aws s3 sync "${OUTPUT_DIR}/" "${S3_PREFIX}" --only-show-errors; then
    echo "→ saved deliverables to ${S3_PREFIX}"
    saved_note="

📁 התוצרים נשמרו ב-S3: ${S3_PREFIX}"
  else
    echo "→ S3 save failed (non-fatal)"
  fi
fi

# Optional: post the finished report back into a comms room (Phase 3 adds the
# /rooms/{id}/post endpoint on the comms backend). Skipped if not configured.
if [ -n "${COMMS_API}" ] && [ -n "${ROOM_ID}" ]; then
  if [ "${status}" = "ok" ]; then
    text="✅ סיימתי את המחקר המעמיק:

${REPORT}${saved_note}"
  else
    text="(${AGENT}: המחקר נכשל — ${REPORT})"
  fi
  body="$(jq -n --arg a "${AGENT}" --arg t "${text}" '{agent:$a, text:$t}')"
  hdr=(-H 'Content-Type: application/json')
  [ -n "${POST_TOKEN:-}" ] && hdr+=(-H "X-Post-Token: ${POST_TOKEN}")
  if curl -fsS -X POST "${COMMS_API}/rooms/${ROOM_ID}/post" "${hdr[@]}" -d "${body}" >/dev/null; then
    echo "→ posted report to room ${ROOM_ID}"
  else
    echo "→ postback failed (non-fatal)"
  fi
fi

[ "${status}" = "ok" ]
