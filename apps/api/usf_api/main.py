from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from usf_api.config import settings
from usf_api.routers import auth, contexts, health, metrics, query, search


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("usf-api starting", service=settings.service_name)

    # PostgreSQL async pool
    engine = create_async_engine(settings.database_url, pool_size=10, max_overflow=20)
    app.state.db = async_sessionmaker(engine, expire_on_commit=False)
    logger.info("Database pool initialized")

    # Valkey/Redis client
    app.state.cache = aioredis.from_url(
        settings.valkey_url,
        encoding="utf-8",
        decode_responses=True,
    )
    logger.info("Valkey cache client initialized")

    yield

    await engine.dispose()
    await app.state.cache.aclose()
    logger.info("usf-api shutdown complete")


app = FastAPI(
    title="USF API Gateway",
    description="Authentication, ABAC, context routing, and query gateway",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(query.router)
app.include_router(metrics.router)
app.include_router(contexts.router)
app.include_router(search.router)
