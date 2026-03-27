"""
USF GitHub App token generation helper.

Used by services that need to interact with GitHub:
- usf-sdl: Read/write SDL YAML versions to a GitHub repo
- usf-architect agent: Create branches, PRs, commit contracts

Generates short-lived installation access tokens using the GitHub App
JWT flow (RS256 signing with the app's private key).

Reference: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app
"""

from __future__ import annotations

import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from usf_core.errors import USFError


class GitHubAppError(USFError):
    code = "GITHUB_APP_ERROR"
    http_status = 500


def _make_app_jwt(app_id: str, private_key_pem: str) -> str:
    """
    Create a GitHub App JWT (valid 10 minutes).

    Uses PyJWT (not python-jose) because GitHub requires specific JWT format.
    """
    try:
        import jwt as pyjwt
    except ImportError as e:
        raise GitHubAppError(
            "PyJWT is required for GitHub App auth. Install: pip install PyJWT"
        ) from e

    now = int(time.time())
    payload = {
        "iat": now - 60,    # Allow 60s clock skew
        "exp": now + 600,   # 10 minute expiry (GitHub max)
        "iss": app_id,
    }
    return pyjwt.encode(payload, private_key_pem, algorithm="RS256")


def get_installation_token(
    app_id: str,
    installation_id: str,
    private_key_path: str,
    *,
    timeout: float = 10.0,
) -> str:
    """
    Generate a GitHub App installation access token.

    The token is valid for 1 hour. Callers should cache it and refresh
    before expiry. Use get_installation_token_cached() for automatic caching.

    Args:
        app_id: GitHub App ID (integer as string).
        installation_id: Installation ID (integer as string).
        private_key_path: Path to the RSA private key PEM file.
        timeout: HTTP request timeout in seconds.

    Returns:
        Installation access token string (starts with 'ghs_').

    Raises:
        GitHubAppError: If the token request fails.
    """
    key_path = Path(private_key_path)
    if not key_path.exists():
        raise GitHubAppError(
            f"GitHub App private key not found: {private_key_path}",
            detail={"path": private_key_path},
        )

    private_key = key_path.read_text()
    app_jwt = _make_app_jwt(app_id, private_key)

    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "usf-platform/1.0",
    }

    try:
        response = httpx.post(url, headers=headers, timeout=timeout)
    except httpx.RequestError as e:
        raise GitHubAppError(
            f"GitHub API request failed: {e}",
            detail={"url": url},
        ) from e

    if response.status_code != 201:
        raise GitHubAppError(
            f"GitHub API returned {response.status_code}",
            detail={"url": url, "response": response.text[:500]},
        )

    data: dict[str, Any] = response.json()
    token = data.get("token")
    if not token:
        raise GitHubAppError(
            "GitHub API response missing 'token' field",
            detail={"response_keys": list(data.keys())},
        )

    return token


class _TokenCache:
    """Simple in-process token cache with expiry."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0

    def get(self) -> str | None:
        if self._token and time.time() < self._expires_at - 60:  # 60s buffer
            return self._token
        return None

    def set(self, token: str, expires_in_seconds: int = 3600) -> None:
        self._token = token
        self._expires_at = time.time() + expires_in_seconds


_token_cache = _TokenCache()


def get_installation_token_cached(
    app_id: str,
    installation_id: str,
    private_key_path: str,
) -> str:
    """
    Get an installation token, using a simple in-process cache.

    Re-generates the token when it's within 60 seconds of expiry.
    Safe for single-process use. For multi-process, use Valkey cache instead.
    """
    cached = _token_cache.get()
    if cached:
        return cached

    token = get_installation_token(app_id, installation_id, private_key_path)
    _token_cache.set(token, expires_in_seconds=3540)  # 59 min (GitHub tokens last 60 min)
    return token


def github_clone_url(repo: str, token: str) -> str:
    """
    Build an authenticated GitHub HTTPS clone URL.

    Args:
        repo: GitHub repo in 'owner/repo' format.
        token: Installation access token.

    Returns:
        HTTPS URL with embedded token credentials.
    """
    return f"https://x-access-token:{token}@github.com/{repo}.git"
