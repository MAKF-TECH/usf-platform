from __future__ import annotations
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
from jose import jwt
from passlib.context import CryptContext
from usf_api.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(p: str) -> str: return _pwd.hash(p)
def verify_password(plain: str, hashed: str) -> bool: return _pwd.verify(plain, hashed)
def _utcnow() -> datetime: return datetime.now(tz=timezone.utc)
def _alg() -> str: return "RS256" if settings.jwt_algorithm == "RS256" and settings.jwt_private_key else "HS256"
def _sign_key() -> str: return settings.jwt_private_key if _alg() == "RS256" else settings.jwt_secret
def _verify_key() -> str: return settings.jwt_public_key if _alg() == "RS256" else settings.jwt_secret


def create_access_token(sub: str, tenant_id: str, role: str) -> str:
    now = _utcnow()
    return jwt.encode({"sub": sub, "tenant_id": tenant_id, "role": role,
                       "iat": now, "exp": now + timedelta(minutes=settings.jwt_access_expire_minutes), "type": "access"},
                      _sign_key(), algorithm=_alg())


def create_refresh_token(sub: str, tenant_id: str) -> str:
    now = _utcnow()
    return jwt.encode({"sub": sub, "tenant_id": tenant_id,
                       "iat": now, "exp": now + timedelta(days=settings.jwt_refresh_expire_days), "type": "refresh"},
                      _sign_key(), algorithm=_alg())


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _verify_key(), algorithms=[_alg()])


def hash_token(t: str) -> str: return hashlib.sha256(t.encode()).hexdigest()
