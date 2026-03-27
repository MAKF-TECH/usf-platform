from __future__ import annotations

"""Celery Beat schedule — periodic background tasks."""

from celery.schedules import crontab

from usf_worker.celery_app import app

app.conf.beat_schedule = {
    # Schema drift check: daily at 02:00 UTC
    "schema-drift-check": {
        "task": "usf_worker.tasks.sdl.validate_all_triples",
        "schedule": crontab(hour=2, minute=0),
        "kwargs": {"named_graph_uri": "https://usf.platform/kg/default"},
    },
    # Cache warming: every 6 hours
    "cache-warming-default": {
        "task": "usf_worker.tasks.cache.warm_cache",
        "schedule": crontab(minute=0, hour="*/6"),
        "kwargs": {"tenant_id": "default", "context": "global"},
    },
    # Ontology sync: weekly on Sunday at 03:00 UTC
    "ontology-sync-weekly": {
        "task": "usf_worker.tasks.ontology.sync_ontology_module",
        "schedule": crontab(day_of_week="sunday", hour=3, minute=0),
        "kwargs": {"module_id": "fibo", "force_reload": False},
    },
}
