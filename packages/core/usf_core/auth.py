"""USF JWT authentication — RS256 verify and sign."""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from usf_core.errors import AuthenticationError


@dataclass(frozen=True)
class TokenClaims:
    sub: str
    email: str
    tenant_id: str
    tenant_slug: str
    roles: list[str] = field(default_factory=list)
    department: str | None = None
    clearance: str = "internal"
    jti: str = field(default_factory=lambda: str(uuid.uuid4()))
    exp: int = 0
    iat: int = 0

    def has_role(self, *roles: str) -> bool:
        return bool(set(self.roles) & set(roles))

    def is_admin(self) -> bool:
        return "admin" in self.roles

    def is_expired(self) -> bool:
        return self.exp > 0 and time.time() > self.exp


@lru_cache(maxsize=1)
def _load_public_key(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise RuntimeError(f"JWT public key not found at {path}")
    return p.read_text()


@lru_cache(maxsize=1)
def _load_private_key(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise RuntimeError(f"JWT private key not found at {path}")
    return p.read_text()


def verify_token(token: str, public_key_path: str, algorithm: str = "RS256") -> TokenClaims:
    """Decode and verify a JWT access token. Raises AuthenticationError on failure."""
    public_key = _load_public_key(public_key_path)
    try:
        payload: dict[str, Any] = jwt.decode(token, public_key, algorithms=[algorithm], options={"verify_exp": True})
    except ExpiredSignatureError as e:
        raise AuthenticationError("Token has expired") from e
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {e}") from e

    sub, email, tenant_id, tenant_slug = payload.get("sub"), payload.get("email"), payload.get("tenant_id"), payload.get("tenant_slug")
    if not all([sub, email, tenant_id, tenant_slug]):
        raise AuthenticationError("Token missing required claims: sub, email, tenant_id, tenant_slug")

    return TokenClaims(sub=str(sub), email=str(email), tenant_id=str(tenant_id), tenant_slug=str(tenant_slug),
        roles=payload.get("roles", []), department=payload.get("department"),
        clearance=payload.get("clearance", "internal"), jti=payload.get("jti", ""),
        exp=payload.get("exp", 0), iat=payload.get("iat", 0))


def sign_access_token(claims: dict[str, Any], private_key_path: str, expires_in_seconds: int = 3600, algorithm: str = "RS256") -> str:
    """Sign a JWT access token (usf-api only)."""
    private_key = _load_private_key(private_key_path)
    now = int(time.time())
    payload = {**claims, "iat": now, "exp": now + expires_in_seconds, "jti": str(uuid.uuid4())}
    return jwt.encode(payload, private_key, algorithm=algorithm)


def extract_bearer_token(authorization_header: str | None) -> str:
    if not authorization_header:
        raise AuthenticationError("Authorization header is required")
    parts = authorization_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Authorization header must be: Bearer <token>")
    return parts[1].strip()
