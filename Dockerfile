FROM python:3.12-slim AS builder

WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-deploy.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-deploy.txt

COPY app/ ./app/
COPY *.py ./
COPY fly.toml ./
COPY Procfile ./

FROM python:3.12-slim

WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /build/app ./app
COPY --from=builder /build/*.py ./
COPY --from=builder /build/fly.toml ./
COPY --from=builder /build/Procfile ./
COPY --from=builder /build/requirements-deploy.txt ./

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-deploy.txt && \
    mkdir -p app/static/uploaded_videos app/static/output logs && \
    find /app -type d -name __pycache__ -exec rm -rf {} +

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080
CMD cd app && uvicorn main:app --host 0.0.0.0 --port $PORT
