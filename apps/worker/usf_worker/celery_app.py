from __future__ import annotations

import os
import sys

from celery import Celery
from loguru import logger

# ── Broker / Backend ──────────────────────────────────────────────────────────
BROKER_URL = os.getenv("VALKEY_URL", "redis://valkey:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://usf:usf@postgres:5432/usf")
# Celery result backend uses psycopg2 (sync) URL format
RESULT_BACKEND = f"db+{DATABASE_URL.replace('postgresql+psycopg', 'postgresql').replace('psycopg://', '/')}"

app = Celery(
    "usf_worker",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        "usf_worker.tasks.ingest",
        "usf_worker.tasks.sdl",
        "usf_worker.tasks.cache",
        "usf_worker.tasks.ontology",
        "usf_worker.tasks.audit",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,           # Ack only after task completes (idempotency)
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # One task at a time per worker thread
    task_track_started=True,
)

# Configure loguru
logger.remove()
logger.add(sys.stderr, level=os.getenv("LOG_LEVEL", "INFO"), serialize=True)
