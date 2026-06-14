# Deployment — company-urban on AWS

Same proven pattern as the `urbangroup` project: **AWS SAM + GitHub Actions**.
Every push to `main` builds and deploys automatically (OIDC — no stored AWS keys).

- **Region:** `us-east-1`
- **Stack:** `company-urban-stack`
- **Domain:** `company-urban.newavera.co.il` (Cloudflare).

## Domain — Cloudflare proxied (recommended, no AWS changes)

After the stack is deployed, take the `CloudFrontUrl` output (`dXXXX.cloudfront.net`)
and add ONE record in Cloudflare on the `newavera.co.il` zone:

| Type  | Name           | Target                  | Proxy      |
|-------|----------------|-------------------------|------------|
| CNAME | `company-urban`| `dXXXX.cloudfront.net`  | 🟠 Proxied |

Set Cloudflare SSL/TLS mode to **Full (strict)**. Cloudflare terminates TLS for
`company-urban.newavera.co.il` and forwards to CloudFront — no ACM cert or
CloudFront Alias needed (CloudFront serves on its `*.cloudfront.net` SNI).

_Alternative (single, native CDN):_ request an ACM cert for the domain in
`us-east-1`, add `Aliases` + `ViewerCertificate` to the CloudFront distribution
in `template.yaml`, and use a **DNS-only** (grey-cloud) CNAME instead.

## The always-on box (comms + agent brains + Ran's Telegram bot)

A separate Linux VM (`44.201.4.142` / `comms.newavera.co.il`) runs the rooms
backend, the slash-command agent brains (`claude -p`), the hourly conductor
pulse (cron → `run-conductor.sh`), and Ran's Telegram bot. It is **not** part of
the SAM stack, so it has its own delivery — now wired into the same push:

- **Auto (CI):** the `deploy-box` job in [deploy.yml](.github/workflows/deploy.yml)
  runs [deploy/deploy-box.sh](deploy/deploy-box.sh) on every push to `main`.
  Needs one repo secret — **`BOX_SSH_KEY`** = the contents of `~/.ssh/cu_box.pem`.
  Until that secret is set, the job no-ops cleanly (CI stays green).
- **Manual:** `bash deploy/deploy-box.sh` (tar-over-ssh; works from Git Bash too,
  no rsync needed).
- **What it syncs:** `comms/backend`, `.claude/commands`, `Agents` (cores +
  STYLE), `goals/brands/structure/interfaces`, `deploy`. **Preserved on the box:**
  `schedule/Schedule.md` (זובין live-edits it), `output/`, and `.env` (secrets via
  `deploy/sync-box-env.sh`).

## Architecture (phased)

| Phase | Component | AWS |
|-------|-----------|-----|
| **A (now)** | Dashboard (Vite/React, static) | S3 + CloudFront |
| B | comms backend (FastAPI) | Lambda + API Gateway (HTTP API) |
| B | Guy — WhatsApp webhook + Priority | Lambda + DynamoDB |
| C | Zubin (the only scheduled job) | EventBridge → container runner (`claude -p`) |

The dashboard is self-contained: Vite inlines the vault markdown (`?raw`) at
build time, so no live file reads are needed in production.

## One-time prerequisite (GitHub)

A **dedicated** OIDC deploy role `company-urban-deploy` already exists in the AWS
account — separate from urbangroup, with S3/IAM/Lambda/DynamoDB permissions
scoped to `company-urban-*` so CI cannot touch any other system. Its trust is
locked to `repo:boazeng/company-urban:*`.

Only one step remains — add the GitHub secret on this repo
(`boazeng/company-urban` → Settings → Secrets and variables → Actions):

- `AWS_DEPLOY_ROLE_ARN` = `arn:aws:iam::824980746386:role/company-urban-deploy`

After that, every push to `main` deploys automatically.

> The first deploy was run locally with the account owner's credentials, so the
> site is already live; the secret only enables hands-off auto-deploy.

## Phase B — Guy's WhatsApp webhook

Deployed by the same SAM stack: a Python Lambda (`guy/` via `lambda_handler.py`
+ Mangum) behind the HTTP API at **`/api/whatsapp/webhook`**, with 5 DynamoDB
tables (`company-urban-{bot-scripts,sessions,messages,service-calls,prompts}-prod`).

> The Guy Lambda has a binary dep (pydantic-core) → it must be built on Linux.
> Deploy it **via GitHub Actions** (the ubuntu runner builds correct wheels),
> not a local Windows `sam build`. (Locally you'd need `sam build --use-container`
> with Docker running.)

WhatsApp secrets (add to the repo's Actions secrets when ready to cut over):

- `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_VERIFY_TOKEN`
  (the existing maintenance number), optional `OPENAI_API_KEY`.

Remaining steps to make Guy answer (after the stack is deployed):

1. **Seed** the `guy-parking-service` script into `company-urban-bot-scripts-prod`
   (one-time; from the local script source via `guy/seed_guy.py` against DynamoDB).
2. **Set** the WhatsApp secrets above and redeploy.
3. **Cut over** the Meta webhook for the maintenance number to
   `GuyWebhookUrl` (stack output) — this moves the number from urbangroup to Guy.
4. **Priority ERP** (real service calls) — port the connector behind Guy's
   pluggable integration flags (`EQUIPMENT_READER_*`, `SERVICE_CALL_WRITER_*`).

## Deploy

Automatic on push to `main`. To run the steps manually:

```bash
sam deploy --template-file template.yaml --stack-name company-urban-stack \
  --region us-east-1 --capabilities CAPABILITY_IAM \
  --no-confirm-changeset --no-fail-on-empty-changeset \
  --s3-bucket aws-sam-cli-managed-default-samclisourcebucket-ebw2dr9e8ezp \
  --parameter-overrides Stage=prod

cd website && npm ci && npm run build
aws s3 sync website/dist/ s3://company-urban-frontend-prod/ --delete \
  --cache-control "public, max-age=31536000, immutable" --exclude "index.html"
aws s3 cp website/dist/index.html s3://company-urban-frontend-prod/index.html \
  --cache-control "public, max-age=0, must-revalidate"
```

The CloudFront URL is printed as the `CloudFrontUrl` stack output.
