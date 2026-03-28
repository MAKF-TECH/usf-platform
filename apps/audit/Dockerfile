# ── Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY packages/core /build/packages/core
COPY packages/rdf /build/packages/rdf
COPY packages/sdl-schema /build/packages/sdl-schema
COPY apps/audit /build/app
RUN pip install --no-cache-dir -e ./packages/core -e ./packages/rdf -e ./packages/sdl-schema -e ./app

# ── Runtime ───────────────────────────────────────────────────────
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl libpq5 && rm -rf /var/lib/apt/lists/*
RUN groupadd -r -g 1000 usf && useradd -r -u 1000 -g usf usf
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /build /build
WORKDIR /build/app
USER usf
EXPOSE 8006

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1
CMD ["uvicorn", "usf_audit.main:app", "--host", "0.0.0.0", "--port", "8006", "--workers", "2"]
