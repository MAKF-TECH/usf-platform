from __future__ import annotations

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from usf_ingest.config import get_settings
from usf_ingest.db import create_db_and_tables
from usf_ingest.routers import bootstrap, jobs, sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Configure loguru
    logger.remove()
    logger.add(sys.stderr, level=settings.LOG_LEVEL, serialize=True)
    logger.info("usf-ingest starting up", extra={"service": settings.SERVICE_NAME})

    await create_db_and_tables()
    yield
    logger.info("usf-ingest shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="USF Ingest Service",
        description="Structured + semi-structured ingestion paths for the USF platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(sources.router)
    app.include_router(jobs.router)
    app.include_router(bootstrap.router)

    @app.get("/health", tags=["ops"])
    async def health() -> dict:
        return {"status": "ok", "service": settings.SERVICE_NAME}

    return app


app = create_app()

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
    _configure_telemetry("usf-ingest")
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)
except ImportError:
    pass
