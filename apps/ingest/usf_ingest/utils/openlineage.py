from __future__ import annotations

"""OpenLineage utilities — emit USF custom facets via RunEvents."""

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger
from openlineage.client import OpenLineageClient
from openlineage.client.facet import BaseFacet
from openlineage.client.run import Job, Run, RunEvent, RunState
from pydantic import Field

from usf_ingest.config import get_settings


# ── Custom Facets ─────────────────────────────────────────────────────────────

class USFExtractionFacet(BaseFacet):
    """Facet emitted after LLM-driven unstructured extraction."""
    extraction_model: str       # e.g. "gemini-2.5-flash" or "gpt-4o"
    ontology_version: str       # e.g. "fibo-2024-Q4"
    confidence_mean: float
    confidence_min: float
    named_graph_uri: str        # where triples were written


class USFIngestionFacet(BaseFacet):
    """Facet emitted after any ingestion pipeline run."""
    source_type: str            # "structured" | "unstructured" | "semi_structured"
    record_count: int
    triples_added: int
    triples_quarantined: int
    shacl_violations: int


# ── Emitter ───────────────────────────────────────────────────────────────────

class USFLineageEmitter:
    """Thin wrapper around OpenLineageClient for USF pipelines."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = OpenLineageClient(url=settings.OPENLINEAGE_URL)
        self._namespace = "usf-platform"

    def _run_id(self) -> str:
        return str(uuid.uuid4())

    def emit_start(self, job_name: str, run_id: str, inputs: list[Any], outputs: list[Any]) -> None:
        event = RunEvent(
            eventType=RunState.START,
            eventTime=datetime.now(timezone.utc).isoformat(),
            run=Run(runId=run_id),
            job=Job(namespace=self._namespace, name=job_name),
            inputs=inputs,
            outputs=outputs,
        )
        self._emit(event)

    def emit_complete(
        self,
        job_name: str,
        run_id: str,
        inputs: list[Any],
        outputs: list[Any],
        ingestion_facet: USFIngestionFacet | None = None,
        extraction_facet: USFExtractionFacet | None = None,
    ) -> None:
        run_facets: dict[str, Any] = {}
        if ingestion_facet:
            run_facets["usf_ingestion"] = ingestion_facet
        if extraction_facet:
            run_facets["usf_extraction"] = extraction_facet

        event = RunEvent(
            eventType=RunState.COMPLETE,
            eventTime=datetime.now(timezone.utc).isoformat(),
            run=Run(runId=run_id, facets=run_facets),
            job=Job(namespace=self._namespace, name=job_name),
            inputs=inputs,
            outputs=outputs,
        )
        self._emit(event)

    def emit_fail(self, job_name: str, run_id: str, error: str) -> None:
        event = RunEvent(
            eventType=RunState.FAIL,
            eventTime=datetime.now(timezone.utc).isoformat(),
            run=Run(runId=run_id),
            job=Job(namespace=self._namespace, name=job_name),
            inputs=[],
            outputs=[],
        )
        self._emit(event)

    def _emit(self, event: RunEvent) -> None:
        try:
            self._client.emit(event)
        except Exception as exc:
            logger.warning("OpenLineage emit failed (non-fatal)", extra={"error": str(exc)})
