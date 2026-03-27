"""Named graph manager for QLever."""
from __future__ import annotations

from loguru import logger

from .sparql import SPARQLClient


class NamedGraphManager:
    """Create, list, and delete named graphs in QLever."""

    def __init__(self, client: SPARQLClient) -> None:
        self._client = client

    async def list_graphs(self) -> list[str]:
        """Return all named graph URIs."""
        result = await self._client.query(
            "SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } }"
        )
        return [row["g"] for row in self._client.bindings(result)]

    async def graph_exists(self, graph_uri: str) -> bool:
        return await self._client.ask(
            f"ASK {{ GRAPH <{graph_uri}> {{ ?s ?p ?o }} }}"
        )

    async def create_or_clear(self, graph_uri: str) -> None:
        """Create an empty named graph (clear if already exists)."""
        await self._client.update(f"CLEAR GRAPH <{graph_uri}>")
        logger.info("Named graph cleared/created", graph=graph_uri)

    async def delete(self, graph_uri: str) -> None:
        """Drop a named graph entirely."""
        await self._client.update(f"DROP GRAPH <{graph_uri}>")
        logger.info("Named graph dropped", graph=graph_uri)

    async def triple_count(self, graph_uri: str) -> int:
        result = await self._client.query(
            f"SELECT (COUNT(*) AS ?n) WHERE {{ GRAPH <{graph_uri}> {{ ?s ?p ?o }} }}"
        )
        bindings = self._client.bindings(result)
        return int(bindings[0]["n"]) if bindings else 0
