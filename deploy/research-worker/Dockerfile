# Deep-research worker — runs a heavy `/dafna ... דוח מלא` headless via `claude -p`,
# fully isolated from the comms box. Phase 1: build + run locally. The AWS/Fargate
# wiring (ECR, task-def, trigger from comms) comes in later phases.
FROM node:22-slim

# claude CLI + the small tools the entrypoint and the agent's Bash tool need.
# awscli: the entrypoint syncs the agent's deliverables to/from S3 (creds come
# from the ECS task role at runtime — no static keys).
RUN apt-get update && apt-get install -y --no-install-recommends \
      git curl jq ca-certificates ripgrep awscli \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code \
    && npm cache clean --force

# claude -p refuses --dangerously-skip-permissions as root → run as a non-root user.
RUN useradd -m -u 10001 researcher
ENV VAULT=/vault HOME=/home/researcher
WORKDIR /vault

# The vault subset דפנה reads at runtime: her command + STYLE + company context.
# (Only what the research needs — not the whole repo.)
COPY .claude/commands ./.claude/commands
COPY Agents ./Agents
COPY goals ./goals
COPY brands ./brands
COPY structure ./structure
COPY interfaces ./interfaces

COPY deploy/research-worker/run-research.sh /usr/local/bin/run-research.sh
COPY deploy/research-worker/md_to_html.py /usr/local/bin/md_to_html.py
# strip CR so the shebang works even if the file was checked out with CRLF (Windows)
RUN sed -i 's/\r$//' /usr/local/bin/run-research.sh \
    && chmod +x /usr/local/bin/run-research.sh \
    && chown -R researcher:researcher /vault /home/researcher

USER researcher

# Inputs are passed as env at run time:
#   ANTHROPIC_API_KEY  (required) — auth for claude -p
#   TOPIC              (required) — the market/topic to research
#   CMD                (default /dafna) · AGENT (default דפנה)
#   COMMS_API + ROOM_ID (optional) — post the finished report back to a comms room
ENTRYPOINT ["/usr/local/bin/run-research.sh"]
