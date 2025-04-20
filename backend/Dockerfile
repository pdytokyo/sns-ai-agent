FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data uploads

# Make init_database.py executable
RUN chmod +x init_database.py

# Expose port for FastAPI
EXPOSE 8000

# Create entrypoint script
RUN echo '#!/bin/bash' > /app/entrypoint.sh && \
    echo 'echo "Running database initialization..."' >> /app/entrypoint.sh && \
    echo 'python init_database.py' >> /app/entrypoint.sh && \
    echo 'echo "Starting FastAPI application..."' >> /app/entrypoint.sh && \
    echo 'exec uvicorn app.main:app --host 0.0.0.0 --port 8000' >> /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Use entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
