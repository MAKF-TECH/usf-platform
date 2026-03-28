"""Tests for usf-worker Celery app and tasks — no Docker/broker required."""
from __future__ import annotations


def test_celery_app_configured():
    """Celery app has acks_late and prefetch=1 for reliability."""
    from usf_worker.celery_app import app

    assert app.conf.task_acks_late is True
    assert app.conf.worker_prefetch_multiplier == 1


def test_celery_app_includes_task_modules():
    """Celery include lists all task modules."""
    from usf_worker.celery_app import app

    includes = app.conf.include or []
    assert "usf_worker.tasks.ingest" in includes
    assert "usf_worker.tasks.cache" in includes
    assert "usf_worker.tasks.sdl" in includes
    assert "usf_worker.tasks.ontology" in includes
    assert "usf_worker.tasks.audit" in includes


def test_celery_app_serializer():
    """Task serializer is JSON for interop."""
    from usf_worker.celery_app import app

    assert app.conf.task_serializer == "json"


def test_ingest_task_is_registered():
    """ingest_structured_source task is registered by name."""
    # Import the tasks module to trigger registration
    import usf_worker.tasks.ingest  # noqa: F401
    from usf_worker.celery_app import app

    assert "usf_worker.tasks.ingest.ingest_structured_source" in app.tasks


def test_cache_warm_task_is_registered():
    """warm_cache task is registered."""
    import usf_worker.tasks.cache  # noqa: F401
    from usf_worker.celery_app import app

    assert "usf_worker.tasks.cache.warm_cache" in app.tasks


def test_cache_module_has_warm_cache():
    """Cache module exposes warm_cache function."""
    from usf_worker.tasks import cache

    assert hasattr(cache, "warm_cache")


def test_beat_schedule_has_expected_tasks():
    """Beat schedule contains drift/schema and cache tasks."""
    # Import beat to register schedule
    import usf_worker.beat  # noqa: F401
    from usf_worker.celery_app import app

    schedule = app.conf.beat_schedule
    assert schedule, "beat_schedule should not be empty"
    task_names = [v.get("task", "") for v in schedule.values()]
    assert any("drift" in t or "schema" in t for t in task_names)
    assert any("cache" in t or "warm" in t for t in task_names)
