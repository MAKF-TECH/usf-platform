FROM python:3.12-slim

RUN groupadd -r usf && useradd -r -g usf usf

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages/core /app/packages/core
COPY packages/sdl-schema /app/packages/sdl-schema
COPY apps/sdl /app/apps/sdl

WORKDIR /app/apps/sdl

RUN pip install --no-cache-dir \
    /app/packages/core \
    /app/packages/sdl-schema \
    -e . 2>/dev/null || pip install --no-cache-dir fastapi uvicorn httpx

USER usf
EXPOSE 8004

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

CMD ["uvicorn", "usf_sdl.main:app", "--host", "0.0.0.0", "--port", "8004"]
