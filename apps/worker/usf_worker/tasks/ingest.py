from __future__ import annotations

"""Structured and document ingestion tasks."""

import httpx
from celery import Task
from loguru import logger

from usf_worker.celery_app import app

INGEST_URL = "http://usf-ingest:8000"


@app.task(name="usf_worker.tasks.ingest.ingest_structured_source", bind=True, max_retries=3, default_retry_delay=30, acks_late=True)
def ingest_structured_source(self: Task, job_id: str, source_id: str, incremental: bool = True) -> dict:
    """Idempotent structured ingestion: fetch source config → run dlt pipeline → R2RML → Ontop."""
    logger.info("ingest_structured_source", extra={"job_id": job_id, "source_id": source_id})
    result = {"job_id": job_id, "source_id": source_id, "records_processed": 0, "status": "running"}

    try:
        source_r = httpx.get(f"{INGEST_URL}/sources/{source_id}", timeout=10)
        source_r.raise_for_status()
        source = source_r.json()
        config = source["connection_config"]
        source_type = source["source_type"]

        from usf_ingest.pipelines.structured.dlt_pipeline import (
            csv_parquet_source, postgres_source, rest_api_source, run_structured_pipeline
        )
        from usf_ingest.config import get_settings
        settings = get_settings()

        if source_type in ("csv", "parquet"):
            src = csv_parquet_source(
                file_path=config["file_path"],
                table_name=config.get("table_name", f"staging_{source_id[:8]}"),
                incremental_column=config.get("incremental_column") if incremental else None,
            )
        elif source_type == "postgres":
            src = postgres_source(
                connection_string=config["connection_string"],
                schema=config.get("schema", "public"),
                table_names=config.get("table_names"),
                incremental_column=config.get("incremental_column") if incremental else None,
            )
        elif source_type == "rest_api":
            src = rest_api_source(
                base_url=config["base_url"],
                endpoint=config["endpoint"],
                table_name=config.get("table_name", f"api_{source_id[:8]}"),
                headers=config.get("headers"),
                incremental_param=config.get("incremental_param") if incremental else None,
            )
        else:
            raise ValueError(f"Unsupported source_type: {source_type}")

        pipeline = run_structured_pipeline(src, f"usf_{source_id[:8]}", settings.DATABASE_URL)
        metrics = pipeline.last_trace.last_normalize_info
        records = getattr(metrics, "row_counts", {})
        result.update({"records_processed": sum(records.values()) if records else 0, "status": "success"})
        return result

    except Exception as exc:
        logger.error(f"ingest_structured_source failed: {exc}", exc_info=True)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc), **result}


@app.task(name="usf_worker.tasks.ingest.ingest_document", bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def ingest_document(self: Task, doc_id: str, tenant_id: str) -> dict:
    """Idempotent document ingestion for semi-structured formats."""
    logger.info("ingest_document", extra={"doc_id": doc_id, "tenant_id": tenant_id})
    result = {"doc_id": doc_id, "tenant_id": tenant_id, "status": "running"}

    try:
        r = httpx.get(f"{INGEST_URL}/documents/{doc_id}", timeout=10)
        r.raise_for_status()
        doc = r.json()
        named_graph = f"https://usf.platform/kg/{tenant_id}/doc/{doc_id}"
        fmt = doc.get("format", doc.get("content_type", ""))

        import asyncio
        if "fhir" in fmt:
            from usf_ingest.pipelines.semi_structured.fhir_parser import parse_fhir_bundle, insert_fhir_graph
            graph = parse_fhir_bundle(doc["content"])
            asyncio.run(insert_fhir_graph(graph, named_graph))
            result["triples"] = len(graph)
        elif "cim" in fmt:
            from usf_ingest.pipelines.semi_structured.cim_parser import parse_cim_from_bytes, insert_cim_graph
            graph = parse_cim_from_bytes(doc["content"].encode())
            asyncio.run(insert_cim_graph(graph, named_graph))
            result["triples"] = len(graph)
        elif "jsonld" in fmt or "json-ld" in fmt:
            from usf_ingest.pipelines.semi_structured.jsonld_parser import ingest_jsonld
            stats = asyncio.run(ingest_jsonld(doc["content"], named_graph, tenant_id))
            result.update(stats)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        result["status"] = "success"
        return result

    except Exception as exc:
        logger.error(f"ingest_document failed: {exc}", exc_info=True)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc), **result}
