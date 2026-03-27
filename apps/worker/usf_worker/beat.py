from __future__ import annotations

"""Celery Beat schedule — periodic background tasks."""

from datetime import timedelta

from celery.schedules import crontab

from usf_worker.celery_app import app

app.conf.beat_schedule = {
    # Schema drift check: daily at 02:00 UTC
    "schema-drift-check": {
        "task": "usf_worker.tasks.ingest.check_schema_drift",
        "schedule": crontab(hour=2, minute=0),
    },
    # Cache warming: every 6 hours — warms all tenants
    "cache-warming": {
        "task": "usf_worker.tasks.cache.warm_all_tenants",
        "schedule": timedelta(hours=6),
    },
    # Ontology sync: weekly on Sunday at 03:00 UTC — all industry modules
    "ontology-sync": {
        "task": "usf_worker.tasks.ontology.sync_industry_modules",
        "schedule": crontab(day_of_week="sunday", hour=3, minute=0),
    },
}
