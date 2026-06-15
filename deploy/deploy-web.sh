#!/usr/bin/env bash
# Safe manual deploy of the website (dashboard SPA) to S3 + CloudFront.
#
# Mirrors the CI job in .github/workflows/deploy.yml. The CRITICAL bit is
# `--exclude "reports/*"`: the frontend bucket hosts BOTH the SPA and the agents'
# published report HTML (reports/<slug>/...). A plain `aws s3 sync --delete`
# WITHOUT this exclude DELETES every report (it's not in dist/). Always exclude it.
#
# Usage:  bash deploy/deploy-web.sh
set -euo pipefail

STAGE="${STAGE:-prod}"
STACK="${STACK:-company-urban-stack}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
BUCKET="company-urban-frontend-${STAGE}"

CF_ID="$(aws cloudformation describe-stacks --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDistributionId'].OutputValue" \
  --output text)"

echo "→ building website"
cd "$REPO/website"
npm ci
npm run build

echo "→ syncing assets (long cache) — reports/* PRESERVED, sw.js NEVER long-cached"
aws s3 sync dist/ "s3://${BUCKET}/" \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "index.html" \
  --exclude "sw.js" \
  --exclude "reports/*"

echo "→ uploading no-cache entry points"
aws s3 cp dist/index.html "s3://${BUCKET}/index.html" \
  --cache-control "no-cache" --content-type "text/html; charset=utf-8"
# sw.js is the static self-destroying worker — must never be cached, or a stale
# worker gets pinned for a year behind the CDN.
if [ -f dist/sw.js ]; then
  aws s3 cp dist/sw.js "s3://${BUCKET}/sw.js" \
    --cache-control "no-cache, no-store, must-revalidate" --content-type "application/javascript"
fi

echo "→ invalidating CloudFront ($CF_ID)"
aws cloudfront create-invalidation --distribution-id "$CF_ID" --paths "/*" \
  --query "Invalidation.Status" --output text

echo "✓ website deployed (reports preserved)."
