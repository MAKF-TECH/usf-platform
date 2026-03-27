from __future__ import annotations
<<<<<<< HEAD

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

=======
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger
>>>>>>> c21bc52 (feat(data-eng): implement usf-ingest, usf-worker, usf-audit services + IBM AML pilot)
from usf_ingest.config import get_settings
from usf_ingest.db import create_db_and_tables
from usf_ingest.routers import bootstrap, jobs, sources

<<<<<<< HEAD

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
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
=======
@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    logger.remove()
    logger.add(sys.stderr, level=s.LOG_LEVEL, serialize=True)
    logger.info("usf-ingest starting", extra={"service": s.SERVICE_NAME})
    await create_db_and_tables()
    yield
    logger.info("usf-ingest shutdown")

def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="USF Ingest Service", version="0.1.0", lifespan=lifespan)
>>>>>>> c21bc52 (feat(data-eng): implement usf-ingest, usf-worker, usf-audit services + IBM AML pilot)
    app.include_router(sources.router)
    app.include_router(jobs.router)
    app.include_router(bootstrap.router)

    @app.get("/health", tags=["ops"])
    async def health() -> dict:
<<<<<<< HEAD
        return {"status": "ok", "service": settings.SERVICE_NAME}

    return app


=======
        return {"status": "ok", "service": s.SERVICE_NAME}

    return app

>>>>>>> c21bc52 (feat(data-eng): implement usf-ingest, usf-worker, usf-audit services + IBM AML pilot)
app = create_app()
