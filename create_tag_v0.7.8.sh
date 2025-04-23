set -e

git checkout main
git pull origin main

git tag -a v0.7.8 -m "Release v0.7.8: Add alembic migrations directory"
git push origin v0.7.8

echo "Tag v0.7.8 created and pushed successfully"
