FROM python:3.10-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install build dependencies and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from root or backend directory
COPY requirements.txt* backend/requirements.txt* /tmp/reqs/
RUN if [ -f "/tmp/reqs/backend/requirements.txt" ]; then \
        cp /tmp/reqs/backend/requirements.txt /app/requirements.txt; \
    else \
        cp /tmp/reqs/requirements.txt /app/requirements.txt; \
    fi && \
    rm -rf /tmp/reqs && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Download spaCy model during build step (en_core_web_sm)
RUN python -m spacy download en_core_web_sm

# Copy application source code into /app cleanly whether context is root or backend
COPY . /tmp/repo/
RUN if [ -d "/tmp/repo/backend" ]; then \
        cp -r /tmp/repo/backend/. /app/; \
    else \
        cp -r /tmp/repo/. /app/; \
    fi && \
    rm -rf /tmp/repo

# Expose container port
EXPOSE 8000

# Start Uvicorn bound to 0.0.0.0 and dynamic $PORT provided by Render environment
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
