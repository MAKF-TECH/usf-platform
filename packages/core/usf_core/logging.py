"""USF structured logging setup using loguru."""
from __future__ import annotations
import logging
import sys
from typing import Any
from loguru import logger


class _InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging(service_name: str, level: str = "INFO", json: bool = True, extra: dict[str, Any] | None = None) -> None:
    """Configure loguru for a USF service. Call once at startup."""
    logger.remove()
    _extra = {"service": service_name, **(extra or {})}
    if json:
        logger.add(sys.stdout, level=level, format="{message}", serialize=True, enqueue=True, backtrace=False, diagnose=False)
    else:
        fmt = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>"
        logger.add(sys.stdout, level=level, format=fmt, colorize=True, enqueue=True, backtrace=True, diagnose=True)
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).handlers = [_InterceptHandler()]
        logging.getLogger(name).propagate = False
    logger.configure(extra=_extra)
    logger.info("Logging configured", service=service_name, level=level, json_mode=json)


def get_logger(name: str | None = None) -> Any:
    if name:
        return logger.bind(module=name)
    return logger
