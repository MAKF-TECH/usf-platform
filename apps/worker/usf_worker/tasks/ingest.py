from __future__ import annotations

"""Ingest tasks — structured and document ingestion pipelines."""

import uuid
from datetime import datetime

import httpx
from celery import Task
from loguru import logger

from usf_worker.celery_app import app

INGEST_SERVICE_URL = "http://usf-ingest:8000"


def _get_source(source_id: str) -> dict:
    """Fetch DataSource from usf-ingest API."""
    response = httpx.get(f"{INGEST_SERVICE_URL}/sources/{source_id}", timeout=10)
    response.raise_for_status()
    return response.json()


def _update_job(job_id: str, payload: dict) -> None:
    """PATCH job status back to usf-ingest (internal endpoint)."""
    # Best-effort; silently ignore failures
    try:
        httpx.patch(f"{INGEST_SERVICE_URL}/internal/jobs/{job_id}", json=payload, timeout=10)
    except Exception as exc:
        logger.warning(f"Could not update job {job_id}: {exc}")


@app.task(
    name="usf_worker.tasks.ingest.ingest_structured_source",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def ingest_structured_source(
    self: Task,
    job_id: str,
    source_id: str,
    incremental: bool = True,
) -> dict:
    """
    Idempotent structured ingestion task.

    1. Fetch source config from usf-ingest.
    2. Run the appropriate dlt pipeline.
    3. Introspect schema, generate R2RML, upload to Ontop.
    4. Emit OpenLineage events.
    """
    logger.info("Starting ingest_structured_source", extra={"job_id": job_id, "source_id": source_id})
    result = {
        "job_id": job_id,
        "source_id": source_id,
        "records_processed": 0,
        "triples_added": 0,
        "status": "running",
    }

    try:
        source = _get_source(source_id)
        source_type = source["source_type"]
        config = source["connection_config"]

        # Import pipeline modules (lazy to avoid circular imports)
        from usf_ingest.pipelines.structured.dlt_pipeline import (
            csv_parquet_source,
            postgres_source,
            rest_api_source,
            run_structured_pipeline,
        )
        from usf_ingest.config import get_settings

        settings = get_settings()

        if source_type in ("csv", "parquet"):
            source_dlt = csv_parquet_source(
                file_path=config["file_path"],
                table_name=config.get("table_name", f"staging_{source_id[:8]}"),
                incremental_column=config.get("incremental_column") if incremental else None,
            )
        elif source_type == "postgres":
            source_dlt = postgres_source(
                connection_string=config["connection_string"],
                schema=config.get("schema", "public"),
                table_names=config.get("table_names"),
                incremental_column=config.get("incremental_column") if incremental else None,
            )
        elif source_type == "rest_api":
            source_dlt = rest_api_source(
                base_url=config["base_url"],
                endpoint=config["endpoint"],
                table_name=config.get("table_name", f"api_{source_id[:8]}"),
                headers=config.get("headers"),
                incremental_param=config.get("incremental_param") if incremental else None,
            )
        else:
            raise ValueError(f"Unsupported source_type: {source_type}")

        pipeline = run_structured_pipeline(
            source=source_dlt,
            pipeline_name=f"usf_{source_id[:8]}",
            destination_url=settings.DATABASE_URL,
        )

        # Extract load metrics from dlt pipeline state
        metrics = pipeline.last_trace.last_normalize_info
        records = getattr(metrics, "row_counts", {})
        total_records = sum(records.values()) if records else 0

        result.update({
            "records_processed": total_records,
            "status": "success",
        })
        logger.info("ingest_structured_source complete", extra=result)
        return result

    except Exception as exc:
        logger.error(f"ingest_structured_source failed: {exc}", exc_info=True)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            result["status"] = "failed"
            result["error"] = str(exc)
            return result


@app.task(
    name="usf_worker.tasks.ingest.ingest_document",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def ingest_document(
    self: Task,
    doc_id: str,
    tenant_id: str,
) -> dict:
    """
    Idempotent document ingestion (semi-structured path).

    Triggers the appropriate parser based on document content type.
    """
    logger.info("Starting ingest_document", extra={"doc_id": doc_id, "tenant_id": tenant_id})
    result = {"doc_id": doc_id, "tenant_id": tenant_id, "status": "running"}

    try:
        # Fetch document metadata from usf-ingest
        response = httpx.get(f"{INGEST_SERVICE_URL}/documents/{doc_id}", timeout=10)
        response.raise_for_status()
        doc = response.json()

        named_graph = f"https://usf.platform/kg/{tenant_id}/doc/{doc_id}"
        content_type = doc.get("content_type", "")

        # Dispatch to correct parser (sync wrappers around async parsers)
        import asyncio

        if "fhir" in content_type or doc.get("format") == "fhir":
            from usf_ingest.pipelines.semi_structured.fhir_parser import (
                insert_fhir_graph,
                parse_fhir_bundle,
            )
            graph = parse_fhir_bundle(doc["content"])
            asyncio.run(insert_fhir_graph(graph, named_graph))
            result["triples"] = len(graph)
        elif "cim" in content_type or doc.get("format") == "cim":
            from usf_ingest.pipelines.semi_structured.cim_parser import (
                insert_cim_graph,
                parse_cim_from_bytes,
            )
            graph = parse_cim_from_bytes(doc["content"].encode())
            asyncio.run(insert_cim_graph(graph, named_graph))
            result["triples"] = len(graph)
        elif "json-ld" in content_type or doc.get("format") == "jsonld":
            from usf_ingest.pipelines.semi_structured.jsonld_parser import ingest_jsonld
            stats = asyncio.run(ingest_jsonld(doc["content"], named_graph, tenant_id))
            result.update(stats)
        else:
            raise ValueError(f"Unsupported document format: {content_type}")

        result["status"] = "success"
        return result

    except Exception as exc:
        logger.error(f"ingest_document failed: {exc}", exc_info=True)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            result["status"] = "failed"
            result["error"] = str(exc)
            return result
