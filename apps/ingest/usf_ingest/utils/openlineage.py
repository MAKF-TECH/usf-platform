from __future__ import annotations

"""OpenLineage utilities — emit USF custom facets via RunEvents."""

import uuid
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from openlineage.client import OpenLineageClient
from openlineage.client.facet import BaseFacet
from openlineage.client.run import Job, Run, RunEvent, RunState

from usf_ingest.config import get_settings


class USFExtractionFacet(BaseFacet):
    """Emitted after LLM-driven unstructured extraction."""
    extraction_model: str
    ontology_version: str
    confidence_mean: float
    confidence_min: float
    named_graph_uri: str


class USFIngestionFacet(BaseFacet):
    """Emitted after any ingestion pipeline run."""
    source_type: str
    record_count: int
    triples_added: int
    triples_quarantined: int
    shacl_violations: int


class USFLineageEmitter:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = OpenLineageClient(url=settings.OPENLINEAGE_URL)
        self._namespace = "usf-platform"

    def emit_start(self, job_name: str, run_id: str, inputs: list, outputs: list) -> None:
        self._emit(RunEvent(
            eventType=RunState.START,
            eventTime=datetime.now(timezone.utc).isoformat(),
            run=Run(runId=run_id),
            job=Job(namespace=self._namespace, name=job_name),
            inputs=inputs,
            outputs=outputs,
        ))

    def emit_complete(
        self,
        job_name: str,
        run_id: str,
        inputs: list,
        outputs: list,
        ingestion_facet: USFIngestionFacet | None = None,
        extraction_facet: USFExtractionFacet | None = None,
    ) -> None:
        run_facets: dict[str, Any] = {}
        if ingestion_facet:
            run_facets["usf_ingestion"] = ingestion_facet
        if extraction_facet:
            run_facets["usf_extraction"] = extraction_facet
        self._emit(RunEvent(
            eventType=RunState.COMPLETE,
            eventTime=datetime.now(timezone.utc).isoformat(),
            run=Run(runId=run_id, facets=run_facets),
            job=Job(namespace=self._namespace, name=job_name),
            inputs=inputs,
            outputs=outputs,
        ))

    def emit_fail(self, job_name: str, run_id: str, error: str) -> None:
        self._emit(RunEvent(
            eventType=RunState.FAIL,
            eventTime=datetime.now(timezone.utc).isoformat(),
            run=Run(runId=run_id),
            job=Job(namespace=self._namespace, name=job_name),
            inputs=[], outputs=[],
        ))

    def _emit(self, event: RunEvent) -> None:
        try:
            self._client.emit(event)
        except Exception as exc:
            logger.warning("OpenLineage emit failed (non-fatal)", extra={"error": str(exc)})
