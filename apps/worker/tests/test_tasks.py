"""Tests for usf-worker Celery app and tasks."""
from __future__ import annotations


def test_celery_app_configured():
    from usf_worker.celery_app import app

    assert app.conf.task_acks_late is True
    assert app.conf.worker_prefetch_multiplier == 1


def test_celery_includes():
    from usf_worker.celery_app import app

    includes = app.conf.include or []
    assert "usf_worker.tasks.ingest" in includes
    assert "usf_worker.tasks.cache" in includes


def test_serializer_json():
    from usf_worker.celery_app import app

    assert app.conf.task_serializer == "json"


def test_ingest_task_registered():
    import usf_worker.tasks.ingest  # noqa: F401
    from usf_worker.celery_app import app

    assert "usf_worker.tasks.ingest.ingest_structured_source" in app.tasks


def test_cache_warm_registered():
    import usf_worker.tasks.cache  # noqa: F401
    from usf_worker.celery_app import app

    assert "usf_worker.tasks.cache.warm_cache" in app.tasks


def test_cache_module_has_warm_cache():
    from usf_worker.tasks import cache

    assert hasattr(cache, "warm_cache")


def test_beat_schedule():
    import usf_worker.beat  # noqa: F401
    from usf_worker.celery_app import app

    schedule = app.conf.beat_schedule
    assert schedule
    task_names = [v.get("task", "") for v in schedule.values()]
    assert any("drift" in t or "schema" in t for t in task_names)
    assert any("cache" in t or "warm" in t for t in task_names)
