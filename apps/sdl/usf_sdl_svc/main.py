"""usf-sdl — FastAPI application entrypoint."""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from .config import settings
from .routers import validate, compile, versions, diff, ontology

logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DDTHH:mm:ss.SSSZ} | {level} | {name}:{function}:{line} | {message} | {extra}",
    serialize=True,
    level=settings.log_level,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("usf-sdl started")
    yield
    logger.info("usf-sdl stopped")


app = FastAPI(
    title="usf-sdl",
    description="USF SDL compiler service — YAML→OWL+SQL+R2RML",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": settings.service_name}


app.include_router(validate.router)
app.include_router(compile.router)
app.include_router(versions.router)
app.include_router(diff.router)
app.include_router(ontology.router)

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
    _configure_telemetry("usf-sdl")
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)
except ImportError:
    pass
