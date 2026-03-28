"""USF Worker — Celery background task service.

This module exposes a minimal FastAPI health endpoint
alongside the Celery worker process.
"""
from fastapi import FastAPI
from loguru import logger
import sys

# Configure loguru
logger.remove()
logger.add(sys.stdout, format="{time:ISO8601} | {level} | {name} | {message}", serialize=True)

app = FastAPI(title="usf-worker", version="0.1.0")

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "usf-worker"}
