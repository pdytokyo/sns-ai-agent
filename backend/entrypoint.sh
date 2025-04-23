set -e

echo "Running Alembic migrations..."
alembic upgrade head

echo "Running database initialization..."
python init_database.py

echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
