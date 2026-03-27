FROM python:3.12-slim

# Build args
ARG APP_DIR=/app

# Install OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd -r usf && useradd -r -g usf -d /app -s /sbin/nologin usf

WORKDIR ${APP_DIR}

# Copy package dependencies first (better layer caching)
COPY packages/rdf /packages/rdf
COPY packages/core /packages/core

# Copy service source
COPY apps/kg/pyproject.toml apps/kg/pyproject.toml
COPY apps/kg/usf_kg apps/kg/usf_kg

# Install dependencies
RUN pip install --no-cache-dir \
    "usf-rdf @ /packages/rdf" \
    "usf-core @ /packages/core" \
    -e /app/apps/kg

# Chown
RUN chown -R usf:usf ${APP_DIR}
USER usf

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "usf_kg.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
