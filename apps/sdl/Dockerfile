FROM python:3.12-slim

ARG APP_DIR=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r usf && useradd -r -g usf -d /app -s /sbin/nologin usf

WORKDIR ${APP_DIR}

COPY packages/rdf /packages/rdf
COPY packages/core /packages/core

COPY apps/sdl/pyproject.toml apps/sdl/pyproject.toml
COPY apps/sdl/usf_sdl_svc apps/sdl/usf_sdl_svc

RUN pip install --no-cache-dir \
    "usf-rdf @ /packages/rdf" \
    "usf-core @ /packages/core" \
    -e /app/apps/sdl

RUN chown -R usf:usf ${APP_DIR}
USER usf

EXPOSE 8001

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "usf_sdl_svc.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
