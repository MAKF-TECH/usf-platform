from __future__ import annotations

import hashlib
import time
from typing import Any

import httpx
from loguru import logger

from usf_query.config import settings
from usf_query.models import QueryBackend, QueryResult


class WrenClient:
    """HTTP client for Wren Engine semantic SQL sidecar."""

    def __init__(self) -> None:
        self._base_url = settings.wren_engine_url

    async def query(self, sql: str, manifest: dict[str, Any] | None = None) -> QueryResult:
        """Execute semantic SQL via Wren Engine."""
        query_hash = hashlib.sha256(sql.encode()).hexdigest()[:16]
        start = time.perf_counter()

        payload: dict[str, Any] = {"sql": sql}
        if manifest:
            payload["manifest"] = manifest

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/mdl/preview",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Wren Engine query failed", error=str(exc), query_hash=query_hash)
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        rows: list[dict[str, Any]] = data.get("data", [])
        cols: list[str] = data.get("columns", [])

        logger.info(
            "Wren Engine query executed",
            query_hash=query_hash,
            rows=len(rows),
            elapsed_ms=round(elapsed_ms, 2),
        )

        return QueryResult(
            rows=rows,
            columns=cols,
            total_rows=len(rows),
            backend_used=QueryBackend.WREN,
            execution_time_ms=elapsed_ms,
            query_hash=query_hash,
            sql_generated=sql,
        )

    async def validate(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """Validate a Wren manifest (MDL)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self._base_url}/v1/mdl/validate",
                json={"manifest": manifest},
            )
            resp.raise_for_status()
            return resp.json()

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
