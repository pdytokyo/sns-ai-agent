#!/usr/bin/env bash
set -euo pipefail
TAG="$1"
STAGE="$SSH_STAGE_HOST"
PROD="$SSH_PROD_HOST"
deploy(){ ssh -o StrictHostKeyChecking=no ubuntu@"$1" "set -e;cd /opt/sns-ai-agent;git fetch --tags;git checkout $TAG;docker-compose pull;docker-compose up -d --remove-orphans;curl -sf http://localhost/health"; }
deploy "$STAGE"
deploy "$PROD"
echo "✅ $TAG deployed"
