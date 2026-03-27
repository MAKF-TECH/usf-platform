from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from loguru import logger
from passlib.context import CryptContext

from usf_api.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _signing_key() -> str:
    """Return private key for signing (RS256) or secret (HS256 fallback)."""
    if settings.jwt_algorithm == "RS256" and settings.jwt_private_key:
        return settings.jwt_private_key
    # Fallback to HS256 in dev
    return settings.jwt_secret


def _verifying_key() -> str:
    """Return public key for verification (RS256) or secret (HS256)."""
    if settings.jwt_algorithm == "RS256" and settings.jwt_public_key:
        return settings.jwt_public_key
    return settings.jwt_secret


def _effective_algorithm() -> str:
    if settings.jwt_algorithm == "RS256" and settings.jwt_private_key:
        return "RS256"
    return "HS256"


def create_access_token(sub: str, tenant_id: str, role: str, extra: dict[str, Any] | None = None) -> str:
    now = _utcnow()
    claims: dict[str, Any] = {
        "sub": sub,
        "tenant_id": tenant_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_expire_minutes),
        "type": "access",
    }
    if extra:
        claims.update(extra)
    return jwt.encode(claims, _signing_key(), algorithm=_effective_algorithm())


def create_refresh_token(sub: str, tenant_id: str) -> str:
    now = _utcnow()
    claims = {
        "sub": sub,
        "tenant_id": tenant_id,
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_expire_days),
        "type": "refresh",
    }
    return jwt.encode(claims, _signing_key(), algorithm=_effective_algorithm())


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT. Raises JWTError on failure."""
    return jwt.decode(
        token,
        _verifying_key(),
        algorithms=[_effective_algorithm()],
    )


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
