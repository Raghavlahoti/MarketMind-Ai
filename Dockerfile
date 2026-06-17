# ============================================================================
# MARKETMIND AI - DOCKERFILE
# ============================================================================

# Use official lightweight Python image
FROM python:3.11-slim as base

# Set build-time environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# Install system dependencies (build-essential, libpq-dev for compiling optional modules if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root system user and group
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser

# Copy requirements file first to utilize Docker layer caching
COPY requirements.txt .

# Install dependencies under the root user
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the rest of the application files into the working directory
COPY . .

# Change ownership of the app directory to our non-root user
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Expose port for FastAPI API server
EXPOSE 8000
# Expose port for ARQ worker health server
EXPOSE 8010

# Default health check using standard urllib to verify main API or worker
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"

# Default command runs the FastAPI API server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
