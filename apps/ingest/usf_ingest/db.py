from __future__ import annotations
<<<<<<< HEAD

from typing import AsyncGenerator

=======
from typing import AsyncGenerator
>>>>>>> c21bc52 (feat(data-eng): implement usf-ingest, usf-worker, usf-audit services + IBM AML pilot)
from loguru import logger
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
<<<<<<< HEAD

=======
>>>>>>> c21bc52 (feat(data-eng): implement usf-ingest, usf-worker, usf-audit services + IBM AML pilot)
from usf_ingest.config import get_settings

_engine: AsyncEngine | None = None

<<<<<<< HEAD

def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = sessionmaker(
        get_engine(), class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
=======
def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().DATABASE_URL, echo=False, pool_pre_ping=True, pool_size=10, max_overflow=20)
    return _engine

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    sf = sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    async with sf() as session:
>>>>>>> c21bc52 (feat(data-eng): implement usf-ingest, usf-worker, usf-audit services + IBM AML pilot)
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

<<<<<<< HEAD

async def create_db_and_tables() -> None:
    async with get_engine().begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("Database tables created/verified")
=======
async def create_db_and_tables() -> None:
    async with get_engine().begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("DB tables created/verified")
>>>>>>> c21bc52 (feat(data-eng): implement usf-ingest, usf-worker, usf-audit services + IBM AML pilot)
