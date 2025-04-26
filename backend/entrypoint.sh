set -e

cd /app

mkdir -p data

echo "Running Alembic migrations..."
alembic upgrade head || echo "Alembic migration failed, continuing anyway"

echo "Running database initialization..."
python init_database.py || echo "Database initialization failed, continuing anyway"

echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
