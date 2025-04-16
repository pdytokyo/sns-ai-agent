FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements file first for better layer caching
COPY requirements-deploy.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-deploy.txt

# Copy only necessary files
COPY app/ ./app/
COPY *.py ./
COPY fly.toml ./
COPY Procfile ./

# Create necessary directories
RUN mkdir -p app/static/uploaded_videos app/static/output logs

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080
CMD cd app && uvicorn main:app --host 0.0.0.0 --port $PORT
