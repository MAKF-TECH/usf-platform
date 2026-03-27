from __future__ import annotations

import hashlib
import time
from typing import Any

import httpx
from loguru import logger

from usf_query.config import settings
from usf_query.models import QueryBackend, QueryResult


class ArcadeDBClient:
    """HTTP client for ArcadeDB — Cypher queries and vector similarity search."""

    def __init__(self) -> None:
        self._base_url = settings.arcadedb_url
        self._db = settings.arcadedb_database
        self._auth = (settings.arcadedb_username, settings.arcadedb_password)

    @property
    def _cypher_url(self) -> str:
        return f"{self._base_url}/api/v1/query/{self._db}"

    async def cypher(self, query: str, params: dict[str, Any] | None = None) -> QueryResult:
        """Execute a Cypher query."""
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        start = time.perf_counter()
        payload = {
            "language": "cypher",
            "command": query,
            "params": params or {},
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self._cypher_url,
                    json=payload,
                    auth=self._auth,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("ArcadeDB Cypher query failed", error=str(exc), query_hash=query_hash)
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        result_list: list[dict[str, Any]] = data.get("result", [])
        cols = list(result_list[0].keys()) if result_list else []

        logger.info(
            "ArcadeDB Cypher executed",
            query_hash=query_hash,
            rows=len(result_list),
            elapsed_ms=round(elapsed_ms, 2),
        )

        return QueryResult(
            rows=result_list,
            columns=cols,
            total_rows=len(result_list),
            backend_used=QueryBackend.ARCADEDB,
            execution_time_ms=elapsed_ms,
            query_hash=query_hash,
        )

    async def vector_search(
        self,
        index_name: str,
        vector: list[float],
        k: int = 5,
    ) -> list[dict[str, Any]]:
        """Vector similarity search via ArcadeDB vector index."""
        query = (
            f"SELECT @rid, @type, @out, vectorDistance(embedding, $vector) AS score "
            f"FROM vectorIndex('{index_name}', $vector, {k}) "
            f"ORDER BY score LIMIT {k}"
        )
        result = await self.cypher(query, params={"vector": vector})
        return result.rows

    async def get_subgraph(
        self,
        entity_iri: str,
        depth: int = 2,
    ) -> list[dict[str, Any]]:
        """Retrieve entity subgraph via Cypher traversal."""
        query = (
            "MATCH path = (start {iri: $iri})-[*1.."
            + str(depth)
            + "]->(neighbor) "
            "RETURN start, relationships(path) AS rels, collect(neighbor) AS neighbors"
        )
        result = await self.cypher(query, params={"iri": entity_iri})
        return result.rows

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self._base_url}/api/v1/ready",
                    auth=self._auth,
                )
                return resp.status_code == 204
        except Exception:
            return False
