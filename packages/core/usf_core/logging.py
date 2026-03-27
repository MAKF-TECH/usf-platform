"""
USF structured logging setup using loguru.

Rules:
- Remove loguru's default handler on import
- Add JSON-structured stdout handler (for log aggregation)
- Intercept standard library logging into loguru
- Provide get_logger() for all services

Usage in a FastAPI app:
    from usf_core.logging import configure_logging
    configure_logging(service_name="usf-api", level="INFO", json=True)
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from loguru import logger


# ─────────────────────────────────────────────────────────────────
# Standard library → loguru bridge
# ─────────────────────────────────────────────────────────────────


class _InterceptHandler(logging.Handler):
    """Redirect all standard library log records into loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        # Translate stdlib level to loguru level name
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find the correct caller frame
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


# ─────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────


def configure_logging(
    service_name: str,
    level: str = "INFO",
    json: bool = True,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Configure loguru for a USF service.

    Call once at application startup (in FastAPI lifespan or __main__).

    Args:
        service_name: Used as the 'service' field in every log record.
        level: Minimum log level (DEBUG / INFO / WARNING / ERROR / CRITICAL).
        json: If True, emit JSON (for log aggregation). If False, human-readable.
        extra: Additional static fields to include in every record.
    """
    # Remove all existing handlers (including loguru default)
    logger.remove()

    _extra = {"service": service_name, **(extra or {})}

    if json:
        # JSON output: one JSON object per line. Used in production / staging.
        fmt = "{message}"
        logger.add(
            sys.stdout,
            level=level,
            format=fmt,
            serialize=True,  # loguru JSON serialization
            enqueue=True,    # async-safe (thread + multiprocess)
            backtrace=False,
            diagnose=False,
        )
    else:
        # Human-readable output for local development.
        fmt = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        logger.add(
            sys.stdout,
            level=level,
            format=fmt,
            colorize=True,
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )

    # Patch all standard library loggers to route through loguru
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).handlers = [_InterceptHandler()]
        logging.getLogger(name).propagate = False

    # Bind static context to every subsequent log call
    logger.configure(extra=_extra)

    logger.info(
        "Logging configured",
        service=service_name,
        level=level,
        json_mode=json,
    )


def get_logger(name: str | None = None) -> Any:
    """
    Return a loguru logger optionally bound to a module name.

    Usage:
        from usf_core.logging import get_logger
        log = get_logger(__name__)
        log.info("Processing query", query_hash="abc123", tenant="acme-bank")
    """
    if name:
        return logger.bind(module=name)
    return logger
