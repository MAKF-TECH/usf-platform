from __future__ import annotations

import httpx
from loguru import logger

from usf_mcp.config import settings


class USFAPIClient:
    """HTTP client calling usf-api for all MCP tool implementations."""

    def __init__(self) -> None:
        self._base_url = settings.usf_api_url
        self._token: str | None = settings.service_token or None

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def get(self, path: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self._base_url}{path}",
                params=params,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def post(self, path: str, body: dict) -> dict:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}{path}",
                json=body,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def list_metrics(self, context: str | None = None) -> dict:
        params = {}
        if context:
            params["context"] = context
        return await self.get("/metrics/", params=params or None)

    async def query_metric(
        self,
        metric: str,
        dimensions: list[str],
        filters: dict,
        time_range: dict | None,
        context: str | None,
    ) -> dict:
        body = {
            "metric": metric,
            "dimensions": dimensions,
            "filters": filters,
            "mode": "auto",
        }
        if time_range:
            body["time_range"] = time_range
        headers_extra = {}
        if context:
            headers_extra["X-USF-Context"] = context
        # Pass context in body as well (usf-api reads from header, but also accepts body)
        body["context"] = context
        return await self.post("/query/", body)

    async def explain_metric(self, metric: str, context: str | None = None) -> dict:
        params = {}
        if context:
            params["context"] = context
        return await self.get(f"/metrics/{metric}", params=params or None)

    async def search_entities(
        self, query: str, entity_type: str | None, context: str | None
    ) -> dict:
        params: dict = {"q": query}
        if entity_type:
            params["entity_type"] = entity_type
        if context:
            params["context"] = context
        return await self.get("/entities/search", params=params)

    async def get_entity(self, iri: str) -> dict:
        import urllib.parse
        encoded = urllib.parse.quote(iri, safe="")
        return await self.get(f"/entities/{encoded}")

    async def list_contexts(self) -> dict:
        return await self.get("/contexts/")


# Singleton
_client: USFAPIClient | None = None


def get_client() -> USFAPIClient:
    global _client
    if _client is None:
        _client = USFAPIClient()
    return _client
