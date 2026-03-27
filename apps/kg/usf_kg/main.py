"""usf-kg — FastAPI application entrypoint."""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from .config import settings
from .routers import triples, graphs, entities, validate, ontology, provenance
from .services.qlever import QLeverService
from .services.arcadedb import ArcadeDBClient
from .services.entity_resolution import EntityResolutionService
from .services.shacl_service import SHACLService

# ── Logging setup (must happen before anything else) ─────────────────────────
logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DDTHH:mm:ss.SSSZ} | {level} | {name}:{function}:{line} | {message} | {extra}",
    serialize=True,
    level=settings.log_level,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    qlever = QLeverService(settings.qlever_url, settings.qlever_update_url)
    await qlever.start()
    app.state.qlever = qlever

    arcadedb = ArcadeDBClient(
        settings.arcadedb_url,
        settings.arcadedb_user,
        settings.arcadedb_pass,
        settings.arcadedb_database,
    )
    await arcadedb.start()
    app.state.arcadedb = arcadedb

    app.state.entity_resolver = EntityResolutionService(qlever)
    app.state.shacl_service = SHACLService(qlever)

    logger.info("usf-kg started", qlever=settings.qlever_url, arcadedb=settings.arcadedb_url)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    await qlever.stop()
    await arcadedb.stop()
    logger.info("usf-kg stopped")


app = FastAPI(
    title="usf-kg",
    description="USF Knowledge Graph service — QLever + ArcadeDB + SHACL",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": settings.service_name}


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(triples.router)
app.include_router(graphs.router)
app.include_router(entities.router)
app.include_router(validate.router)
app.include_router(ontology.router)
app.include_router(provenance.router)
