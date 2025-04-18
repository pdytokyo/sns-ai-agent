
set -e

VERSION=$1

if [ -z "$VERSION" ]; then
  echo "Error: Version tag not provided"
  echo "Usage: bash deploy/deploy_latest.sh <version_tag>"
  exit 1
fi

echo "Deploying version $VERSION..."

STAGE_HOST="${SSH_STAGE_HOST}"
STAGE_HEALTH_URL="http://${SSH_STAGE_HOST}/health"

PROD_HOST="${SSH_PROD_HOST}"
PROD_HEALTH_URL="http://${SSH_PROD_HOST}/health"

echo "Deploying to staging environment..."
echo "Simulating deployment to staging environment (${STAGE_HOST})..."
echo "SSH connection would execute:"
echo "  cd /opt/sns-ai-agent &&"
echo "  git fetch --tags &&"
echo "  git checkout $VERSION &&"
echo "  docker-compose pull &&"
echo "  docker-compose up -d --remove-orphans"

echo "Simulating staging deployment verification..."
echo "Would check: $STAGE_HEALTH_URL"
echo "Staging deployment simulation successful!"

echo "Deploying to production environment..."
echo "Simulating deployment to production environment (${PROD_HOST})..."
echo "SSH connection would execute:"
echo "  cd /opt/sns-ai-agent &&"
echo "  git fetch --tags &&"
echo "  git checkout $VERSION &&"
echo "  docker-compose pull &&"
echo "  docker-compose up -d --remove-orphans"

echo "Simulating production deployment verification..."
echo "Would check: $PROD_HEALTH_URL"
echo "Production deployment simulation successful!"

echo "Simulating Slack notification:"
echo ":rocket: $VERSION deployed to prod – JobLog fix complete"

echo "Deployment simulation of $VERSION completed successfully!"
