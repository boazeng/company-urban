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

## Architecture (phased)

| Phase | Component | AWS |
|-------|-----------|-----|
| **A (now)** | Dashboard (Vite/React, static) | S3 + CloudFront |
| B | comms backend (FastAPI) | Lambda + API Gateway (HTTP API) |
| B | Guy — WhatsApp webhook + Priority | Lambda + DynamoDB |
| C | Zubin (the only scheduled job) | EventBridge → container runner (`claude -p`) |

The dashboard is self-contained: Vite inlines the vault markdown (`?raw`) at
build time, so no live file reads are needed in production.

## One-time prerequisites (AWS / GitHub)

The `urbangroup` repo already deploys to this AWS account via an OIDC role, so
reuse it — two small edits:

1. **GitHub secret** on this repo (`boazeng/company-urban`):
   - `AWS_DEPLOY_ROLE_ARN` = the same role ARN used by urbangroup.

2. **Extend the IAM role trust policy** to allow this repo. Add the
   `company-urban` repo to the OIDC `sub` condition alongside urbangroup, e.g.:
   ```json
   "token.actions.githubusercontent.com:sub": [
     "repo:boazeng/urbangroup:*",
     "repo:boazeng/company-urban:*"
   ]
   ```

That's it — the role's existing permissions (CloudFormation, S3, CloudFront)
already cover this stack. The SAM-managed deploy bucket is shared per-account.

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
