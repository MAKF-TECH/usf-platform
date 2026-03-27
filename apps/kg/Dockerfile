FROM python:3.12-slim

RUN groupadd -r usf && useradd -r -g usf usf

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages/core /app/packages/core
COPY packages/rdf /app/packages/rdf
COPY packages/ontologies /app/packages/ontologies
COPY apps/kg /app/apps/kg

WORKDIR /app/apps/kg

RUN pip install --no-cache-dir \
    /app/packages/core \
    /app/packages/rdf \
    /app/packages/ontologies \
    -e .

USER usf
EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["uvicorn", "usf_kg.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "2"]
