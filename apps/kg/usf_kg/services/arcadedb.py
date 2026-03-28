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

    # ── Low-level Cypher execution ────────────────────────────────────────────

    async def execute_cypher(self, query: str, params: dict | None = None) -> list[dict[str, Any]]:
        """Execute a read-only Cypher query and return result records."""
        assert self._client, "ArcadeDBClient not started"
        payload: dict[str, Any] = {"language": "cypher", "command": query}
        if params:
            payload["params"] = params
        resp = await self._client.post(f"/query/{self._db}", json=payload)
        resp.raise_for_status()
        return resp.json().get("result", [])

    async def command(self, cypher: str, params: dict | None = None) -> list[dict[str, Any]]:
        """Execute a Cypher write command (CREATE, MERGE, SET, DELETE)."""
        assert self._client, "ArcadeDBClient not started"
        payload: dict[str, Any] = {"language": "cypher", "command": cypher}
        if params:
            payload["params"] = params
        resp = await self._client.post(f"/command/{self._db}", json=payload)
        resp.raise_for_status()
        return resp.json().get("result", [])

    # ── Node operations ───────────────────────────────────────────────────────

    async def upsert_node(self, label: str, iri: str, properties: dict[str, Any]) -> str:
        """Upsert a node by IRI; returns its IRI."""
        prop_str = ", ".join(f"n.`{k}` = ${k}" for k in properties)
        set_clause = f", {prop_str}" if prop_str else ""
        cypher = f"""
        MERGE (n:{label} {{iri: $iri}})
        ON CREATE SET n.iri = $iri{set_clause}
        ON MATCH  SET n.iri = $iri{set_clause}
        RETURN n.iri AS iri
        """
        result = await self.command(cypher, {"iri": iri, **properties})
        return result[0].get("iri", iri) if result else iri

    async def get_node(self, iri: str) -> dict[str, Any] | None:
        """Fetch a node by IRI. Returns None if not found."""
        result = await self.execute_cypher(
            "MATCH (n {iri: $iri}) RETURN n LIMIT 1", {"iri": iri}
        )
        if not result:
            return None
        node = result[0].get("n") or result[0]
        return node if isinstance(node, dict) else None

    # ── Edge operations ───────────────────────────────────────────────────────

    async def create_edge(
        self,
        src_iri: str,
        tgt_iri: str,
        rel_type: str,
        props: dict[str, Any] | None = None,
    ) -> bool:
        """Create or merge an edge between two nodes. Returns True on success."""
        params: dict[str, Any] = {"from_iri": src_iri, "to_iri": tgt_iri}
        if props:
            prop_str = ", ".join(f"r.`{k}` = ${k}" for k in props)
            cypher = f"""
            MATCH (a {{iri: $from_iri}}), (b {{iri: $to_iri}})
            MERGE (a)-[r:{rel_type}]->(b)
            ON CREATE SET {prop_str}
            ON MATCH  SET {prop_str}
            RETURN r
            """
            params.update(props)
        else:
            cypher = f"""
            MATCH (a {{iri: $from_iri}}), (b {{iri: $to_iri}})
            MERGE (a)-[r:{rel_type}]->(b)
            RETURN r
            """
        result = await self.command(cypher, params)
        return len(result) > 0

    # ── Legacy aliases (for backward compat) ─────────────────────────────────

    async def upsert_entity(
        self, iri: str, entity_type: str, properties: dict[str, Any]
    ) -> None:
        await self.upsert_node(entity_type, iri, properties)

    async def upsert_relationship(
        self,
        from_iri: str,
        rel_type: str,
        to_iri: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        await self.create_edge(from_iri, to_iri, rel_type, properties)

    # ── Graph traversal ───────────────────────────────────────────────────────

    async def traverse(
        self,
        start_iri: str,
        depth: int = 2,
        rel_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """BFS traversal from start_iri up to `depth` hops."""
        rel_filter = ":" + "|".join(rel_types) if rel_types else ""
        cypher = f"""
        MATCH path = (start {{iri: $start_iri}})-[{rel_filter}*1..{depth}]->(end)
        UNWIND relationships(path) AS r
        RETURN
            startNode(r).iri AS src,
            type(r)          AS rel,
            endNode(r).iri   AS tgt,
            length(path)     AS depth
        """
        return await self.execute_cypher(cypher, {"start_iri": start_iri})

    # ── Vector search ─────────────────────────────────────────────────────────

    async def vector_search(
        self,
        embedding: list[float],
        top_k: int = 10,
        label: str | None = None,
    ) -> list[dict[str, Any]]:
        """Vector similarity search on entity embeddings."""
        index_name = f"{label}_embedding" if label else "entity_embedding"
        cypher = f"""
        CALL db.index.vector.queryNodes('{index_name}', $top_k, $embedding)
        YIELD node, score
        RETURN node.iri AS iri, score
        """
        try:
            return await self.execute_cypher(cypher, {"top_k": top_k, "embedding": embedding})
        except httpx.HTTPStatusError as exc:
            logger.warning("Vector search failed (index may not exist)", index=index_name, error=str(exc))
            return []
