from __future__ import annotations

import hashlib
import time
from typing import Any
from urllib.parse import urljoin

import httpx
from loguru import logger

from usf_query.config import settings
from usf_query.models import QueryBackend, QueryResult


class OntopClient:
    """HTTP client for Ontop SPARQL-SQL sidecar.

    Ontop exposes a standard SPARQL 1.1 endpoint at /sparql.
    It translates SPARQL queries over virtual RDF graphs to SQL
    against the underlying relational database.
    """

    def __init__(self) -> None:
        self._base_url = settings.ontop_url
        self._sparql_endpoint = urljoin(self._base_url + "/", "sparql")

    async def query(self, sparql: str) -> QueryResult:
        """Execute SPARQL via Ontop (SPARQL → SQL → DB)."""
        query_hash = hashlib.sha256(sparql.encode()).hexdigest()[:16]
        start = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    self._sparql_endpoint,
                    data={"query": sparql},
                    headers={
                        "Accept": "application/sparql-results+json",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Ontop query failed", error=str(exc), query_hash=query_hash)
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        bindings = data.get("results", {}).get("bindings", [])
        cols: list[str] = data.get("head", {}).get("vars", [])

        rows = []
        for binding in bindings:
            row = {}
            for col in cols:
                val = binding.get(col, {})
                row[col] = val.get("value")
            rows.append(row)

        logger.info(
            "Ontop query executed",
            query_hash=query_hash,
            rows=len(rows),
            elapsed_ms=round(elapsed_ms, 2),
        )

        return QueryResult(
            rows=rows,
            columns=cols,
            total_rows=len(rows),
            backend_used=QueryBackend.ONTOP,
            execution_time_ms=elapsed_ms,
            query_hash=query_hash,
            sparql_generated=sparql,
        )

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/")
                return resp.status_code < 500
        except Exception:
            return False
