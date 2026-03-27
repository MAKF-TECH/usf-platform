from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from usf_query.config import settings
from usf_query.routers import compile, execute, explain
from usf_query.services.query_router import backends_health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("usf-query starting", service=settings.service_name, debug=settings.debug)
    health = await backends_health()
    logger.info("Backend health at startup", **health)
    yield
    logger.info("usf-query shutting down")


app = FastAPI(
    title="USF Query Service",
    description="SQL, SPARQL, NL2SPARQL, and OG-RAG query execution",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(compile.router)
app.include_router(execute.router)
app.include_router(explain.router)


@app.get("/health")
async def health() -> dict:
    backends = await backends_health()
    return {
        "status": "ok",
        "service": settings.service_name,
        "backends": backends,
    }
