# 🔬 Deep-research worker (Fargate per-job — Phase 1)

Runs a heavy `/dafna … דוח מלא` deep research **in an isolated container**, so it
never competes with the small comms box. This is the **compute plane** for
long-running agent work (30 min+). Phase 1 here is the container itself, validated
locally; the AWS/Fargate wiring (ECR + ECS task-def + trigger from comms + result
postback) comes in later phases.

## Files
- `Dockerfile` — the worker image (claude CLI + the vault subset דפנה reads).
- `run-research.sh` — entrypoint: runs `claude -p`, prints the report, optionally posts it back to a comms room.

## Build (context = repo root, so the COPYs find `.claude/`, `Agents/`, …)
```bash
docker build -f deploy/research-worker/Dockerfile -t tact-research-worker .
```

## Test locally
Use your Anthropic API key (same one the box uses).

```bash
# 1) Smoke test — proves claude CLI + auth work inside the container (cheap):
docker run --rm -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  --entrypoint claude tact-research-worker -p "reply with OK"

# 2) Full deep research (takes minutes; prints the report to stdout):
docker run --rm \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e TOPIC="שוק חברות מתקני חניה בישראל" \
  tact-research-worker
```

`COMMS_API` + `ROOM_ID` env vars enable posting the report back to a comms room —
left for Phase 3 (the comms backend needs a `POST /rooms/{id}/post` endpoint first).

## Inputs (env)
| Var | Required | Meaning |
|-----|----------|---------|
| `ANTHROPIC_API_KEY` | ✅ | auth for `claude -p` |
| `TOPIC` | ✅ | the market/topic to research |
| `CMD` | — | slash command (default `/dafna`) |
| `AGENT` | — | agent name for postback (default `דפנה`) |
| `COMMS_API` + `ROOM_ID` | — | post the finished report back to this room |

## Next phases (not built yet)
2. AWS: ECR repo + ECS Fargate task-def + IAM + networking in `template.yaml`, deployed via CI.
3. Wiring: comms triggers `ecs:RunTask` on a deep request (fast ack); container posts the report back via `POST /rooms/{id}/post`.
