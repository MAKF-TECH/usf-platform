"""USF SDK — Python exceptions."""
from __future__ import annotations


class USFSDKError(Exception):
    """Base exception for all USF SDK errors."""

    def __init__(self, message: str, status_code: int | None = None, detail: dict | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail or {}


class AuthError(USFSDKError):
    """Raised on 401 — authentication required or token expired."""


class ContextAmbiguousError(USFSDKError):
    """Raised on 409 — metric is defined in multiple contexts; caller must specify one."""

    def __init__(self, metric: str, available_contexts: list[str], message: str = "") -> None:
        self.metric = metric
        self.available_contexts = available_contexts
        msg = message or (
            f"Metric '{metric}' is ambiguous. "
            f"Set context to one of: {', '.join(available_contexts)}"
        )
        super().__init__(msg, status_code=409)


class NotFoundError(USFSDKError):
    """Raised on 404."""


class ValidationError(USFSDKError):
    """Raised on 400 or 422 — request or semantic validation failed."""


class AccessDeniedError(USFSDKError):
    """Raised on 403 — ABAC policy denied the request."""
