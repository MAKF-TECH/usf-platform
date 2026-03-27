FROM python:3.12-slim
RUN groupadd -r usf && useradd -r -g usf usf
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY packages/core /app/packages/core
COPY apps/mcp /app/apps/mcp
WORKDIR /app/apps/mcp
RUN pip install --no-cache-dir /app/packages/core -e .
USER usf
EXPOSE 9000
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1
CMD ["python", "-m", "usf_mcp.main"]
