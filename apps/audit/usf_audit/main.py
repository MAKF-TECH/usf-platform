from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from usf_audit.config import get_settings
from usf_audit.db import create_db_and_tables
from usf_audit.routers import export, lineage, log, stats
from usf_audit.services.kafka_consumer import start_kafka_consumer


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.remove()
    logger.add(sys.stderr, level=settings.LOG_LEVEL, serialize=True)
    logger.info("usf-audit starting up", extra={"service": settings.SERVICE_NAME})

    await create_db_and_tables()

    # Start Kafka consumer in background
    consumer_task = asyncio.create_task(start_kafka_consumer())
    app.state.consumer_task = consumer_task

    yield

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    logger.info("usf-audit shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="USF Audit Service",
        description="Append-only audit log, lineage tracing, and PROV-O export",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(log.router)
    app.include_router(lineage.router)
    app.include_router(export.router)
    app.include_router(stats.router)

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
    _configure_telemetry("usf-audit")
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)
except ImportError:
    pass
