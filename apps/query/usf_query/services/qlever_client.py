from __future__ import annotations
import hashlib, time
from typing import Any
import httpx
from loguru import logger
from usf_query.config import settings
from usf_query.models import QueryBackend, QueryResult


class QLeverClient:
    def __init__(self) -> None:
        self._base_url = settings.qlever_url

    async def query(self, sparql: str, named_graph: str | None = None) -> QueryResult:
        params: dict[str, Any] = {"query": sparql, "format": "json"}
        if named_graph:
            params["default-graph-uri"] = named_graph
        query_hash = hashlib.sha256(sparql.encode()).hexdigest()[:16]
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{self._base_url}/", params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("QLever query failed", error=str(exc))
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        bindings = data.get("results", {}).get("bindings", [])
        cols = [v["value"] for v in data.get("head", {}).get("vars", [])]
        rows = [{col: binding.get(col, {}).get("value") for col in cols} for binding in bindings]
        logger.info("QLever executed", query_hash=query_hash, rows=len(rows), ms=round(elapsed_ms, 1))
        return QueryResult(rows=rows, columns=cols, total_rows=len(rows),
                           backend_used=QueryBackend.QLEVER, execution_time_ms=elapsed_ms,
                           query_hash=query_hash, sparql_generated=sparql)

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/ping")
                return resp.status_code < 500
        except Exception:
            return False
