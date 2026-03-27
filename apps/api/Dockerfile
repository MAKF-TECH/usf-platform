FROM python:3.12-slim

# Create non-root user with uid=1000
RUN groupadd -r -g 1000 usf && useradd -r -u 1000 -g usf usf

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared packages first (layer caching)
COPY packages/core /app/packages/core

# Copy application
COPY apps/api /app/apps/api

WORKDIR /app/apps/api

RUN pip install --no-cache-dir /app/packages/core -e .

# Switch to non-root user
USER usf

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "usf_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
