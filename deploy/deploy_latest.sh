#!/usr/bin/env bash
set -euo pipefail
TAG="$1"
STAGE="$SSH_STAGE_HOST"
PROD="$SSH_PROD_HOST"

echo "$SSH_PRIVATE_KEY" > /tmp/deploy_key.pem
chmod 400 /tmp/deploy_key.pem

deploy () {
  ssh -o StrictHostKeyChecking=no -i /tmp/deploy_key.pem ubuntu@"$1" "
    set -e
    cd /opt/sns-ai-agent
    git fetch --tags
    git checkout $TAG
    docker-compose pull
    docker-compose up -d --remove-orphans
    curl -sf http://localhost/health
  "
}

deploy "$STAGE"
deploy "$PROD"

echo "✅ $TAG deployed"
