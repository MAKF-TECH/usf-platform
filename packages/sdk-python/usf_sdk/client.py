"""USF SDK — main client."""
from __future__ import annotations

import httpx
from loguru import logger
from typing import Any

from .auth import TokenStore
from .exceptions import (
    USFSDKError,
    AuthError,
    ContextAmbiguousError,
    NotFoundError,
    ValidationError,
    AccessDeniedError,
)
from .models import (
    TokenResponse,
    MetricSummary,
    MetricExplanation,
    QueryResult,
    QueryMeta,
    EntityResult,
    EntityDetail,
    ContextInfo,
)

_STATUS_ERRORS: dict[int, type[USFSDKError]] = {
    401: AuthError,
    403: AccessDeniedError,
    404: NotFoundError,
    409: ContextAmbiguousError,
    400: ValidationError,
    422: ValidationError,
}


def _raise_for_status(response: httpx.Response) -> None:
    """Raise a typed SDK error for non-2xx responses."""
    if response.is_success:
        return

    body: dict[str, Any] = {}
    try:
        body = response.json()
    except Exception:
        pass

    error_block: dict[str, Any] = body.get("error", {})
    message: str = error_block.get("message", response.text or f"HTTP {response.status_code}")
    detail: dict[str, Any] = error_block.get("detail", {})

    if response.status_code == 409:
        metric: str = detail.get("metric", "unknown")
        contexts: list[str] = [c["name"] for c in detail.get("contexts", [])]
        raise ContextAmbiguousError(metric=metric, available_contexts=contexts, message=message)

    exc_class = _STATUS_ERRORS.get(response.status_code, USFSDKError)
    raise exc_class(message, status_code=response.status_code, detail=detail)


class USFClient:
    """Universal Semantic Fabric Python SDK.

    Async-first. Use as an async context manager for automatic cleanup::

        async with USFClient("http://localhost:8000", context="finance") as client:
            await client.login("user@example.com", "pass")
            metrics = await client.list_metrics()
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        tenant: str | None = None,
        context: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.context = context
        self._tenant = tenant
        self._tokens = TokenStore()

        default_headers: dict[str, str] = {"User-Agent": "usf-sdk-python/0.1.0"}
        if api_key:
            default_headers["Authorization"] = f"Bearer {api_key}"
            self._tokens.access_token = api_key
        if tenant:
            default_headers["X-USF-Tenant-ID"] = tenant

        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            headers=default_headers,
            timeout=60.0,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _context_headers(self, context: str | None) -> dict[str, str]:
        ctx = context or self.context
        if ctx:
            return {"X-USF-Context": ctx}
        return {}

    def _auth_headers(self) -> dict[str, str]:
        return self._tokens.auth_header()

    async def _get(self, path: str, params: dict | None = None, context: str | None = None) -> Any:
        headers = {**self._auth_headers(), **self._context_headers(context)}
        logger.debug("GET {} params={}", path, params)
        r = await self._http.get(path, params=params, headers=headers)
        _raise_for_status(r)
        return r.json()

    async def _post(self, path: str, json: dict | None = None, context: str | None = None) -> Any:
        headers = {**self._auth_headers(), **self._context_headers(context)}
        logger.debug("POST {} body_keys={}", path, list((json or {}).keys()))
        r = await self._http.post(path, json=json, headers=headers)
        _raise_for_status(r)
        return r.json()

    # ── Auth ──────────────────────────────────────────────────────────────────

    async def login(self, email: str, password: str) -> "USFClient":
        """Authenticate and store JWT. Returns self for chaining."""
        body = await self._post("/auth/login", json={"email": email, "password": password})
        token = TokenResponse.model_validate(body)
        self._tokens.store(
            access_token=token.access_token,
            expires_in=token.expires_in,
            refresh_token=token.refresh_token or "",
        )
        logger.info("Authenticated as {}", email)
        return self

    # ── Contexts ──────────────────────────────────────────────────────────────

    async def list_contexts(self) -> list[str]:
        """List available semantic contexts for the current tenant."""
        body = await self._get("/contexts")
        items = body.get("data", [])
        return [ContextInfo.model_validate(c).name for c in items]

    # ── Metrics ───────────────────────────────────────────────────────────────

    async def list_metrics(
        self, context: str | None = None, search: str | None = None
    ) -> list[MetricSummary]:
        """List available business metrics."""
        params: dict[str, str] = {}
        ctx = context or self.context
        if ctx:
            params["context"] = ctx
        if search:
            params["search"] = search
        body = await self._get("/metrics", params=params or None, context=context)
        items = body.get("data", [])
        return [MetricSummary.model_validate(m) for m in items]

    async def explain(self, metric: str, context: str | None = None) -> MetricExplanation:
        """Get full metric definition, lineage, ontology class, and compiled SQL."""
        body = await self._get(f"/metrics/{metric}/explain", context=context)
        return MetricExplanation.model_validate(body.get("data", body))

    # ── Query ─────────────────────────────────────────────────────────────────

    async def query(
        self,
        metric: str,
        dimensions: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        time_range: dict[str, str] | None = None,
        context: str | None = None,
    ) -> QueryResult:
        """Execute a semantic metric query.

        Raises:
            ContextAmbiguousError: HTTP 409 — metric spans multiple contexts.
                Inspect ``e.available_contexts`` and retry with ``context=`` set.
        """
        payload: dict[str, Any] = {
            "type": "sql",
            "metric": metric,
            "options": {"include_provenance": True},
        }
        if dimensions:
            payload["dimensions"] = dimensions
        if filters:
            payload["filters"] = filters
        if time_range:
            payload["time_range"] = time_range

        ctx = context or self.context
        body = await self._post("/query", json=payload, context=ctx)
        data_block = body.get("data", {})
        meta_block = body.get("meta", {})

        columns: list[str] = data_block.get("columns", [])
        rows: list[dict] = data_block.get("rows", [])
        # Normalise rows → list[dict] keyed by column name
        if rows and isinstance(rows[0], list):
            rows = [dict(zip(columns, row)) for row in rows]

        return QueryResult(
            columns=columns,
            data=rows,
            row_count=data_block.get("row_count", len(rows)),
            meta=QueryMeta.model_validate(meta_block),
        )

    # ── Knowledge Graph ───────────────────────────────────────────────────────

    async def search_entities(
        self,
        query: str,
        entity_type: str | None = None,
        context: str | None = None,
        limit: int = 20,
    ) -> list[EntityResult]:
        """Semantic search over the knowledge graph."""
        params: dict[str, Any] = {"q": query, "limit": limit}
        if entity_type:
            params["entity_type"] = entity_type
        body = await self._get("/entities/search", params=params, context=context)
        return [EntityResult.model_validate(e) for e in body.get("data", [])]

    async def get_entity(self, iri: str, depth: int = 1) -> EntityDetail:
        """Get entity detail with PROV-O provenance."""
        import urllib.parse
        encoded = urllib.parse.quote(iri, safe="")
        body = await self._get(f"/entities/{encoded}", params={"depth": depth})
        return EntityDetail.model_validate(body.get("data", body))

    # ── SPARQL ────────────────────────────────────────────────────────────────

    async def sparql(self, query: str, context: str | None = None) -> list[dict[str, Any]]:
        """Execute a raw SPARQL SELECT against the ontology-grounded knowledge graph."""
        ctx = context or self.context
        payload = {"type": "sparql", "query": query}
        body = await self._post("/query", json=payload, context=ctx)
        return body.get("data", {}).get("rows", [])

    # ── Ingestion ─────────────────────────────────────────────────────────────

    async def ingest_csv(
        self,
        file_path: str,
        source_name: str,
        ontology_module: str = "fibo",
    ) -> str:
        """Upload a CSV file and start an ingestion job. Returns ``job_id``."""
        import httpx as _httpx

        headers = self._auth_headers()
        with open(file_path, "rb") as fh:
            r = await self._http.post(
                "/ingest/csv",
                files={"file": (file_path.split("/")[-1], fh, "text/csv")},
                data={"source_name": source_name, "ontology_module": ontology_module},
                headers=headers,
            )
        _raise_for_status(r)
        return r.json()["data"]["job_id"]

    async def job_status(self, job_id: str) -> dict[str, Any]:
        """Check ingestion job status and layer trace."""
        body = await self._get(f"/jobs/{job_id}")
        return body.get("data", body)

    # ── Context manager ───────────────────────────────────────────────────────

    async def __aenter__(self) -> "USFClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._http.aclose()
