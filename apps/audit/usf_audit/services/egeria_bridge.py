"""
Egeria Open Metadata integration for USF.

Syncs USF lineage events and SDL definitions to Egeria,
enabling cross-tool metadata exchange with DataHub, Collibra, etc.
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger


class EgeriaBridge:
    """Client for Egeria Open Metadata and Governance platform."""

    def __init__(
        self,
        egeria_url: str,
        server_name: str = "simple-metadata-store",
        user_id: str = "garygeeke",
    ):
        self.base = (
            f"{egeria_url}/servers/{server_name}/open-metadata/access-services"
        )
        self.user_id = user_id

    async def register_data_asset(self, asset: dict[str, Any]) -> str:
        """Register a USF named graph as a DataAsset in Egeria.

        Returns Egeria GUID.
        """
        url = (
            f"{self.base}/asset-owner/users/{self.user_id}"
            "/assets/data-stores/databases"
        )
        payload = {
            "class": "NewDataStoreRequestBody",
            "displayName": asset.get("name", "USF Named Graph"),
            "description": asset.get("description", ""),
            "qualifiedName": f"usf::{asset.get('iri', asset.get('name', ''))}",
            "additionalProperties": {
                "source": "usf-platform",
                "tenant_id": asset.get("tenant_id", ""),
                "graph_iri": asset.get("iri", ""),
            },
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            guid = resp.json().get("guid", "")
            logger.info("Registered data asset in Egeria: {}", guid)
            return guid

    async def publish_lineage_event(self, event: dict[str, Any]) -> bool:
        """Forward an OpenLineage event to Egeria's lineage store."""
        url = (
            f"{self.base}/asset-manager/users/{self.user_id}"
            "/governance-actions/open-lineage-events"
        )
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(url, json=event)
                resp.raise_for_status()
                logger.info("Published lineage event to Egeria")
                return True
            except httpx.HTTPError as exc:
                logger.error("Failed to publish lineage event to Egeria: {}", exc)
                return False

    async def sync_sdl_metric(
        self, metric_name: str, sdl_def: dict[str, Any]
    ) -> str:
        """Publish a USF SDL metric definition as a GlossaryTerm in Egeria."""
        url = (
            f"{self.base}/subject-area/users/{self.user_id}"
            "/glossaries/terms"
        )
        payload = {
            "class": "GlossaryTermProperties",
            "qualifiedName": f"usf::metric::{metric_name}",
            "displayName": metric_name,
            "description": sdl_def.get("description", ""),
            "summary": f"USF SDL metric: type={sdl_def.get('type', 'unknown')}",
            "additionalProperties": {
                "sdl_type": sdl_def.get("type", ""),
                "dimensions": ",".join(sdl_def.get("dimensions", [])),
                "source": "usf-sdl",
            },
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            guid = resp.json().get("guid", "")
            logger.info("Synced SDL metric '{}' to Egeria: {}", metric_name, guid)
            return guid

    async def get_data_assets(self, tenant_id: str) -> list[dict[str, Any]]:
        """List all data assets registered for a tenant."""
        url = (
            f"{self.base}/asset-consumer/users/{self.user_id}"
            "/assets/by-search-string"
        )
        params = {"searchString": f"usf::{tenant_id}", "startFrom": 0, "pageSize": 100}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, params=params, json={})
            resp.raise_for_status()
            return resp.json().get("assets", [])

    async def health(self) -> bool:
        """Check Egeria connectivity."""
        # Use the platform origin URL (strip access-services path)
        platform_url = self.base.split("/open-metadata")[0].rsplit("/servers", 1)[0]
        url = f"{platform_url}/open-metadata/platform-services/users/{self.user_id}/server-platform/origin"
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(url)
                return resp.status_code == 200
            except httpx.HTTPError:
                return False
