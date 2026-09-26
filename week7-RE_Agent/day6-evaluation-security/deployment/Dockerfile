# Multi-Stage Production Dockerfile for RealEstate Hub AI Agent
# Stage 1: Build & Dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY day6-evaluation-security/requirements-day6.txt .
RUN pip install --user -r requirements-day6.txt

# Stage 2: Final Minimal Runtime Image
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/app/day6-evaluation-security:/app/day5-langgraph-agent:/app/realestate-hub/backend \
    APP_ENV=production \
    PORT=8000 \
    HOST=0.0.0.0

# Install minimal runtime dependencies & curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application source code
COPY day5-langgraph-agent /app/day5-langgraph-agent
COPY day6-evaluation-security /app/day6-evaluation-security
COPY realestate-hub /app/realestate-hub

# Create non-root system user for security
RUN useradd -u 8888 -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Container Healthcheck probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/liveness || exit 1

# Production Entrypoint
CMD ["python", "-m", "uvicorn", "deployment.prod_server:app", "--app-dir", "day6-evaluation-security", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
