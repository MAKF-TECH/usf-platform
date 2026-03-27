from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from usf_api.models import LoginRequest, RefreshRequest, Session, TokenPair, User, UserResponse
from usf_api.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_password,
)
from usf_api.services.tenant import get_user_by_email, get_user_by_id

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer()


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


async def get_db(request: Request) -> AsyncSession:
    async with request.app.state.db() as session:
        yield session


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    request: Request,
) -> dict[str, Any]:
    """Dependency: decode JWT and return user claims."""
    token = creds.credentials
    try:
        claims = decode_token(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if claims.get("type") != "access":
        raise HTTPException(status_code=401, detail="Expected access token")
    return claims


@router.post("/login", response_model=TokenPair, status_code=201)
async def login(req: LoginRequest, request: Request) -> TokenPair:
    """Authenticate user and return JWT pair."""
    async with request.app.state.db() as db:
        user = await get_user_by_email(req.email, db)

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    access = create_access_token(
        sub=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
    )
    refresh = create_refresh_token(sub=str(user.id), tenant_id=str(user.tenant_id))

    # Store refresh token hash in DB
    async with request.app.state.db() as db:
        session_obj = Session(
            user_id=user.id,
            refresh_token_hash=hash_token(refresh),
            expires_at=_utcnow() + timedelta(days=30),
        )
        db.add(session_obj)
        await db.commit()

    logger.info("User logged in", user_id=str(user.id), role=user.role)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair)
async def refresh(req: RefreshRequest, request: Request) -> TokenPair:
    """Exchange refresh token for a new access token."""
    try:
        claims = decode_token(req.refresh_token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid refresh token: {exc}")

    if claims.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Expected refresh token")

    token_hash = hash_token(req.refresh_token)

    async with request.app.state.db() as db:
        from sqlmodel import select
        result = await db.exec(
            select(Session).where(
                Session.refresh_token_hash == token_hash,
                Session.revoked == False,  # noqa: E712
            )
        )
        session_obj = result.first()

    if not session_obj or session_obj.expires_at < _utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    user_id = uuid.UUID(claims["sub"])
    async with request.app.state.db() as db:
        user = await get_user_by_id(user_id, db)

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or disabled")

    new_access = create_access_token(
        sub=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
    )
    new_refresh = create_refresh_token(sub=str(user.id), tenant_id=str(user.tenant_id))

    # Revoke old session, create new
    async with request.app.state.db() as db:
        session_obj.revoked = True
        db.add(session_obj)
        new_session = Session(
            user_id=user.id,
            refresh_token_hash=hash_token(new_refresh),
            expires_at=_utcnow() + timedelta(days=30),
        )
        db.add(new_session)
        await db.commit()

    return TokenPair(access_token=new_access, refresh_token=new_refresh)


@router.get("/me", response_model=UserResponse)
async def get_me(claims: Annotated[dict, Depends(get_current_user)]) -> UserResponse:
    """Return current user info from JWT claims."""
    return UserResponse(
        id=uuid.UUID(claims["sub"]),
        email=claims.get("email", ""),
        role=claims["role"],
        department=claims.get("department"),
        tenant_id=uuid.UUID(claims["tenant_id"]),
    )
