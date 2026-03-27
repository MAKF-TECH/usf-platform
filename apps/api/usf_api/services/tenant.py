from __future__ import annotations
import uuid
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from usf_api.models import Tenant, User


async def get_tenant_by_id(tid: uuid.UUID, db: AsyncSession) -> Tenant | None:
    r = await db.exec(select(Tenant).where(Tenant.id == tid))
    return r.first()


async def get_user_by_id(uid: uuid.UUID, db: AsyncSession) -> User | None:
    r = await db.exec(select(User).where(User.id == uid))
    return r.first()


async def get_user_by_email(email: str, db: AsyncSession) -> User | None:
    r = await db.exec(select(User).where(User.email == email))
    return r.first()
