"""USF Worker — Celery background task service.

This module exposes a minimal FastAPI health endpoint
alongside the Celery worker process.
"""
from fastapi import FastAPI
from loguru import logger
import sys

# Configure loguru
logger.remove()
logger.add(sys.stdout, format="{time:ISO8601} | {level} | {name} | {message}", serialize=True)

app = FastAPI(title="usf-worker", version="0.1.0")

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "usf-worker"}

# ── OpenTelemetry instrumentation ─────────────────────────────────────────────
import os as _os

def _configure_telemetry(service_name: str):
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    provider = TracerProvider()
    otlp_endpoint = _os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)

try:
    _configure_telemetry("usf-worker")
except ImportError:
    pass
