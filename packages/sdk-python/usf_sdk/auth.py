"""USF SDK — JWT token management."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class TokenStore:
    access_token: str = ""
    refresh_token: str = ""
    expires_at: float = 0.0

    def is_expired(self, buffer_seconds: int = 30) -> bool:
        return time.time() >= (self.expires_at - buffer_seconds)

    def store(self, access_token: str, expires_in: int, refresh_token: str = "") -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = time.time() + expires_in

    def auth_header(self) -> dict[str, str]:
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}
