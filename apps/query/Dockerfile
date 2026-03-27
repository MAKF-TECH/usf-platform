FROM python:3.12-slim

RUN groupadd -r usf && useradd -r -g usf usf

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages/core /app/packages/core
COPY packages/rdf /app/packages/rdf
COPY packages/sdl-schema /app/packages/sdl-schema
COPY apps/query /app/apps/query

WORKDIR /app/apps/query

RUN pip install --no-cache-dir \
    /app/packages/core \
    /app/packages/rdf \
    /app/packages/sdl-schema \
    -e .

USER usf
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "usf_query.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
