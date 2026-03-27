from __future__ import annotations

import uuid
from typing import Any

from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from usf_api.models import Tenant, User


async def get_tenant_by_id(tenant_id: uuid.UUID, db: AsyncSession) -> Tenant | None:
    """Lookup tenant by ID."""
    from sqlmodel import select
    result = await db.exec(select(Tenant).where(Tenant.id == tenant_id))
    return result.first()


async def get_user_by_id(user_id: uuid.UUID, db: AsyncSession) -> User | None:
    from sqlmodel import select
    result = await db.exec(select(User).where(User.id == user_id))
    return result.first()


async def get_user_by_email(email: str, db: AsyncSession) -> User | None:
    from sqlmodel import select
    result = await db.exec(select(User).where(User.email == email))
    return result.first()
