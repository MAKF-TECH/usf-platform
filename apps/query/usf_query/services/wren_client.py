from __future__ import annotations
import hashlib, time
from typing import Any
import httpx
from loguru import logger
from usf_query.config import settings
from usf_query.models import QueryBackend, QueryResult


class WrenClient:
    def __init__(self) -> None:
        self._base_url = settings.wren_engine_url

    async def query(self, sql: str, manifest: dict[str, Any] | None = None) -> QueryResult:
        query_hash = hashlib.sha256(sql.encode()).hexdigest()[:16]
        start = time.perf_counter()
        payload: dict[str, Any] = {"sql": sql}
        if manifest:
            payload["manifest"] = manifest
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self._base_url}/v1/mdl/preview", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Wren Engine failed", error=str(exc))
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        rows: list[dict[str, Any]] = data.get("data", [])
        cols: list[str] = data.get("columns", [])
        logger.info("Wren executed", query_hash=query_hash, rows=len(rows), ms=round(elapsed_ms, 1))
        return QueryResult(rows=rows, columns=cols, total_rows=len(rows),
                           backend_used=QueryBackend.WREN, execution_time_ms=elapsed_ms,
                           query_hash=query_hash, sql_generated=sql)

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
