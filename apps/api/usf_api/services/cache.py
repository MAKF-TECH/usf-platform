from __future__ import annotations
import json
from typing import Any
from loguru import logger
from usf_api.config import settings


async def get_cached(key: str, redis_client: Any) -> Any | None:
    try:
        raw = await redis_client.get(key)
        if raw:
            logger.debug("Cache HIT", key=key)
            return json.loads(raw)
    except Exception as exc:
        logger.warning("Cache GET error", key=key, error=str(exc))
    return None


async def set_cached(key: str, value: Any, redis_client: Any, ttl: int | None = None) -> None:
    try:
        await redis_client.set(key, json.dumps(value, default=str), ex=ttl or settings.cache_ttl_seconds)
    except Exception as exc:
        logger.warning("Cache SET error", key=key, error=str(exc))


async def invalidate_pattern(pattern: str, redis_client: Any) -> int:
    try:
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)
            return len(keys)
    except Exception as exc:
        logger.warning("Cache invalidate error", pattern=pattern, error=str(exc))
    return 0


def make_query_cache_key(tenant_id: str, context: str, query_hash: str) -> str:
    return f"usf:query:{tenant_id}:{context}:{query_hash}"

def make_metrics_cache_key(tenant_id: str, context: str) -> str:
    return f"usf:metrics:{tenant_id}:{context}"
