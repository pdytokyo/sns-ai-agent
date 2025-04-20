#!/usr/bin/env bash
set -euo pipefail

TAG="$1"
STAGE="${SSH_STAGE_HOST:-57.180.242.200}"
PROD="${SSH_PROD_HOST:-52.69.83.83}"

# --- write key ---
printf '%s
' "$SSH_PRIVATE_KEY" > /tmp/deploy_key.pem
chmod 400 /tmp/deploy_key.pem

deploy () {
  HOST="$1"
  ssh -o StrictHostKeyChecking=no -i /tmp/deploy_key.pem ubuntu@"$HOST" <<REMOTE
set -e
sudo mkdir -p /opt && sudo chown \$USER /opt
[ -d /opt/sns-ai-agent/.git ] || git clone https://github.com/pdytokyo/sns-ai-agent.git /opt/sns-ai-agent
cd /opt/sns-ai-agent
git fetch --tags
git checkout $TAG
docker-compose pull
docker-compose up -d --remove-orphans
curl -sf http://localhost/health
REMOTE
}

if [ "${SIMULATE:-false}" = "true" ]; then
  echo "🚀 Deploying \$TAG in simulation mode"
else
  echo "🚀 Deploying \$TAG to real environments"
  deploy "$STAGE"
  deploy "$PROD"
  echo "✅ \$TAG deployed"
fi
