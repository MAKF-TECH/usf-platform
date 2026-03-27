"""ArcadeDB client for usf-kg (property graph + vector index via HTTP API)."""
from __future__ import annotations

from typing import Any

import httpx
from loguru import logger


class ArcadeDBClient:
    """ArcadeDB HTTP API client using Cypher queries."""

    def __init__(self, url: str, user: str, password: str, database: str) -> None:
        self._base = f"{url}/api/v1"
        self._db = database
        self._auth = (user, password)
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self._base,
            auth=self._auth,
            timeout=30.0,
        )
        logger.info("ArcadeDBClient started", database=self._db)

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()

    async def query(self, cypher: str, params: dict | None = None) -> list[dict[str, Any]]:
        """Execute a Cypher query and return result records."""
        assert self._client, "ArcadeDBClient not started"
        payload: dict[str, Any] = {"language": "cypher", "command": cypher}
        if params:
            payload["params"] = params

        resp = await self._client.post(f"/query/{self._db}", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", [])

    async def command(self, cypher: str, params: dict | None = None) -> list[dict[str, Any]]:
        """Execute a Cypher write command (CREATE, MERGE, SET, DELETE)."""
        assert self._client, "ArcadeDBClient not started"
        payload: dict[str, Any] = {"language": "cypher", "command": cypher}
        if params:
            payload["params"] = params

        resp = await self._client.post(f"/command/{self._db}", json=payload)
        resp.raise_for_status()
        return resp.json().get("result", [])

    async def upsert_entity(
        self,
        iri: str,
        entity_type: str,
        properties: dict[str, Any],
    ) -> None:
        """Upsert an entity node by IRI."""
        prop_str = ", ".join(f"n.`{k}` = ${k}" for k in properties)
        cypher = f"""
        MERGE (n:{entity_type} {{iri: $iri}})
        ON CREATE SET n.iri = $iri, {prop_str}
        ON MATCH  SET {prop_str}
        """
        await self.command(cypher, {"iri": iri, **properties})

    async def upsert_relationship(
        self,
        from_iri: str,
        rel_type: str,
        to_iri: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Upsert a relationship between two entities."""
        cypher = f"""
        MATCH (a {{iri: $from_iri}}), (b {{iri: $to_iri}})
        MERGE (a)-[r:{rel_type}]->(b)
        """
        if properties:
            prop_str = ", ".join(f"r.`{k}` = ${k}" for k in properties)
            cypher += f" ON CREATE SET {prop_str} ON MATCH SET {prop_str}"
        await self.command(cypher, {"from_iri": from_iri, "to_iri": to_iri, **(properties or {})})

    async def vector_search(
        self,
        entity_type: str,
        embedding: list[float],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Vector similarity search on entity embeddings."""
        # ArcadeDB vector index query via Cypher
        cypher = f"""
        CALL db.index.vector.queryNodes('{entity_type}_embedding', $top_k, $embedding)
        YIELD node, score
        RETURN node.iri AS iri, score
        """
        return await self.query(cypher, {"top_k": top_k, "embedding": embedding})
