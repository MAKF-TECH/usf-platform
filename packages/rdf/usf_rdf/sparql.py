"""Async SPARQL client wrapper for QLever."""
from __future__ import annotations

import json
from typing import Any

import httpx
from loguru import logger


class SPARQLClient:
    """Async SPARQL client for QLever (or any SPARQL 1.1 endpoint)."""

    def __init__(self, endpoint: str, update_endpoint: str | None = None) -> None:
        self._endpoint = endpoint
        self._update_endpoint = update_endpoint or endpoint
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(timeout=60.0)

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()

    async def query(
        self,
        sparql: str,
        accept: str = "application/sparql-results+json",
    ) -> dict[str, Any]:
        """Execute a SPARQL SELECT/ASK/CONSTRUCT query."""
        assert self._client, "SPARQLClient not started"
        logger.debug("SPARQL query", query=sparql[:200])
        resp = await self._client.post(
            self._endpoint,
            data={"query": sparql},
            headers={"Accept": accept, "Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()

    async def update(self, sparql: str) -> None:
        """Execute a SPARQL UPDATE (INSERT/DELETE/LOAD)."""
        assert self._client, "SPARQLClient not started"
        logger.debug("SPARQL update", update=sparql[:200])
        resp = await self._client.post(
            self._update_endpoint,
            data={"update": sparql},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()

    async def ask(self, sparql: str) -> bool:
        """Execute a SPARQL ASK query."""
        result = await self.query(sparql, accept="application/sparql-results+json")
        return result.get("boolean", False)

    def bindings(self, result: dict[str, Any]) -> list[dict[str, str]]:
        """Extract bindings from a SPARQL JSON result."""
        rows = result.get("results", {}).get("bindings", [])
        return [
            {k: v.get("value", "") for k, v in row.items()}
            for row in rows
        ]
