"""USF GitHub App token generation helper."""
from __future__ import annotations
import time
from pathlib import Path
from typing import Any
import httpx
from usf_core.errors import USFError


class GitHubAppError(USFError):
    code = "GITHUB_APP_ERROR"
    http_status = 500


def _make_app_jwt(app_id: str, private_key_pem: str) -> str:
    try:
        import jwt as pyjwt
    except ImportError as e:
        raise GitHubAppError("PyJWT is required. pip install PyJWT") from e
    now = int(time.time())
    return pyjwt.encode({"iat": now-60, "exp": now+600, "iss": app_id}, private_key_pem, algorithm="RS256")


def get_installation_token(app_id: str, installation_id: str, private_key_path: str, *, timeout: float = 10.0) -> str:
    """Generate a GitHub App installation access token (valid 1 hour)."""
    key_path = Path(private_key_path)
    if not key_path.exists():
        raise GitHubAppError(f"GitHub App private key not found: {private_key_path}")
    private_key = key_path.read_text()
    app_jwt = _make_app_jwt(app_id, private_key)
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {"Authorization": f"Bearer {app_jwt}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "usf-platform/1.0"}
    try:
        response = httpx.post(url, headers=headers, timeout=timeout)
    except httpx.RequestError as e:
        raise GitHubAppError(f"GitHub API request failed: {e}") from e
    if response.status_code != 201:
        raise GitHubAppError(f"GitHub API returned {response.status_code}", detail={"response": response.text[:500]})
    data: dict[str, Any] = response.json()
    token = data.get("token")
    if not token:
        raise GitHubAppError("GitHub API response missing token field")
    return token


class _TokenCache:
    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0
    def get(self) -> str | None:
        if self._token and time.time() < self._expires_at - 60:
            return self._token
        return None
    def set(self, token: str, expires_in_seconds: int = 3600) -> None:
        self._token = token
        self._expires_at = time.time() + expires_in_seconds

_token_cache = _TokenCache()

def get_installation_token_cached(app_id: str, installation_id: str, private_key_path: str) -> str:
    """Get an installation token with in-process caching."""
    cached = _token_cache.get()
    if cached:
        return cached
    token = get_installation_token(app_id, installation_id, private_key_path)
    _token_cache.set(token, expires_in_seconds=3540)
    return token

def github_clone_url(repo: str, token: str) -> str:
    return f"https://x-access-token:{token}@github.com/{repo}.git"
