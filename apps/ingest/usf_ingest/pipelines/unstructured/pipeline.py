"""Main unstructured pipeline orchestrator.

Orchestrates: parse → chunk → extract → filter → build_kg → rdf_bridge → emit_openlineage

All steps are async-compatible for Celery task integration.
Job status updates are written to PostgreSQL via psycopg[async].
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from loguru import logger

from .docling_parser import DoclingParser, DocumentResult
from .chunker import SemanticChunker, Chunk
from .langextract_runner import LangExtractRunner, ExtractionResult
from .confidence_filter import ConfidenceFilter, QuarantineRecord
from .arcadedb_builder import ArcadeDBBuilder, ArcadeDBClient, Embedder
from .rdf_bridge import RDFBridge


@dataclass
class PipelineConfig:
    """Runtime configuration for one unstructured pipeline run."""

    # LLM config
    llm_provider: str = "gemini"                 # "gemini" | "openai" | "ollama"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # Ontology module
    ontology_module: str = "fibo"

    # Chunking
    max_chunk_size: int = 512
    chunk_overlap: int = 50

    # Extraction
    extraction_passes: int = 3
    confidence_threshold: float = 0.5

    # ArcadeDB
    arcadedb_url: str = "http://arcadedb:2480"
    arcadedb_database: str = "usf"
    arcadedb_username: str = "root"
    arcadedb_password: str = "usf"

    # Embedder
    embedder_provider: str = "openai"
    embedder_model: str = "text-embedding-3-small"

    # usf-kg
    usf_kg_url: str = "http://usf-kg:8000"

    # OpenLineage
    openlineage_url: str = "http://marquez:5000"

    # Tenant
    tenant_id: str = "default"

    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Summary of a completed unstructured pipeline run."""

    job_id: str
    source_path: str
    ontology_module: str
    document: DocumentResult | None = None
    chunks_count: int = 0
    extractions_count: int = 0
    passed_count: int = 0
    quarantined_count: int = 0
    inserted_iris: list[str] = field(default_factory=list)
    named_graph: str = ""
    duration_seconds: float = 0.0
    error: str | None = None
    success: bool = True


class UnstructuredPipeline:
    """End-to-end unstructured document ingestion pipeline.

    Steps:
        1. parse     — Docling: PDF/DOCX/HTML → DocumentResult
        2. chunk     — chonkie: text → list[Chunk]
        3. extract   — LangExtract: chunks → list[ExtractionResult]
        4. filter    — ConfidenceFilter: split into passed / quarantined
        5. build_kg  — ArcadeDBBuilder: UPSERT entities → list[IRI]
        6. rdf       — RDFBridge: IRIs + extractions → RDF triples → usf-kg
        7. lineage   — OpenLineage RunEvent → Redpanda/Marquez

    Usage:
        pipeline = UnstructuredPipeline(config)
        result = await pipeline.run("path/to/document.pdf", job_id="job-123")
    """

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config

        self._parser = DoclingParser()
        self._chunker = SemanticChunker(
            max_chunk_size=config.max_chunk_size,
            chunk_overlap=config.chunk_overlap,
        )
        self._extractor = LangExtractRunner(
            config={
                "llm_provider": config.llm_provider,
                "gemini_api_key": config.gemini_api_key,
                "openai_api_key": config.openai_api_key,
                "ollama_base_url": config.ollama_base_url,
                "ollama_model": config.ollama_model,
            },
            extraction_passes=config.extraction_passes,
        )
        self._filter = ConfidenceFilter(confidence_threshold=config.confidence_threshold)

        arcade_client = ArcadeDBClient(
            base_url=config.arcadedb_url,
            database=config.arcadedb_database,
            username=config.arcadedb_username,
            password=config.arcadedb_password,
        )
        embedder = Embedder(
            provider=config.embedder_provider,
            model=config.embedder_model,
        )
        self._kg_builder = ArcadeDBBuilder(client=arcade_client, embedder=embedder)
        self._rdf_bridge = RDFBridge(
            usf_kg_url=config.usf_kg_url,
            tenant_id=config.tenant_id,
        )

    async def run(
        self,
        source: str,
        job_id: str | None = None,
        named_graph: str | None = None,
    ) -> PipelineResult:
        """Run the full unstructured pipeline for one document.

        Args:
            source: File path or URL of the document.
            job_id: Optional job ID; generated if not provided.
            named_graph: Target named graph override.

        Returns:
            PipelineResult summary.
        """
        import time

        job_id = job_id or str(uuid.uuid4())
        t_start = time.monotonic()

        logger.info(
            "Unstructured pipeline starting",
            job_id=job_id,
            source=source,
            module=self._config.ontology_module,
        )

        result = PipelineResult(
            job_id=job_id,
            source_path=source,
            ontology_module=self._config.ontology_module,
        )

        try:
            # 1. Parse
            logger.info("Step 1/7: Parsing document", job_id=job_id)
            document = await self._parser.parse(source)
            result.document = document

            # 2. Chunk
            logger.info("Step 2/7: Chunking document", job_id=job_id, words=document.word_count)
            chunks: list[Chunk] = await self._chunker.chunk(document.text)
            result.chunks_count = len(chunks)

            # 3. Extract — run per chunk, aggregate
            logger.info("Step 3/7: Extracting entities", job_id=job_id, chunks=len(chunks))
            all_extractions: list[ExtractionResult] = []
            for chunk in chunks:
                chunk_results = await self._extractor.extract(
                    text=chunk.text,
                    ontology_module=self._config.ontology_module,
                    chunk_index=chunk.chunk_index,
                )
                # Adjust char offsets to be relative to full document
                for r in chunk_results:
                    if r.char_interval is not None:
                        r.char_interval = (
                            chunk.char_start + r.char_interval[0],
                            chunk.char_start + r.char_interval[1],
                        )
                all_extractions.extend(chunk_results)

            result.extractions_count = len(all_extractions)

            # 4. Filter
            logger.info(
                "Step 4/7: Filtering extractions",
                job_id=job_id,
                total=len(all_extractions),
            )
            passed, quarantined = self._filter.filter(all_extractions, job_id=job_id)
            result.passed_count = len(passed)
            result.quarantined_count = len(quarantined)

            # Log quarantined to audit store (fire-and-forget)
            if quarantined:
                await self._log_quarantine(quarantined, job_id)

            # 5. Build KG in ArcadeDB
            logger.info(
                "Step 5/7: Building KG in ArcadeDB",
                job_id=job_id,
                entities=len(passed),
            )
            inserted_iris = await self._kg_builder.build_knowledge_graph(
                entities=passed, job_id=job_id
            )
            result.inserted_iris = inserted_iris

            # 6. RDF Bridge → usf-kg
            logger.info("Step 6/7: RDF bridge → usf-kg", job_id=job_id)
            from .langextract_runner import _select_model_id
            model_id = _select_model_id(self._extractor._config)
            triples = await self._rdf_bridge.convert_and_post(
                extraction_results=passed,
                inserted_iris=inserted_iris,
                job_id=job_id,
                source_uri=source if source.startswith("http") else f"file://{source}",
                model_id=model_id,
                named_graph=named_graph,
            )
            result.named_graph = triples.named_graph

            # 7. OpenLineage
            logger.info("Step 7/7: Emitting OpenLineage event", job_id=job_id)
            await self._emit_openlineage(job_id, source, result)

            result.duration_seconds = time.monotonic() - t_start
            result.success = True

            logger.info(
                "Unstructured pipeline complete",
                job_id=job_id,
                passed=result.passed_count,
                quarantined=result.quarantined_count,
                inserted_iris=len(inserted_iris),
                duration=f"{result.duration_seconds:.2f}s",
            )

        except Exception as e:
            result.success = False
            result.error = str(e)
            result.duration_seconds = time.monotonic() - t_start
            logger.error(
                "Unstructured pipeline failed",
                job_id=job_id,
                error=str(e),
                exc_info=True,
            )
            raise

        return result

    async def _log_quarantine(
        self, quarantined: list[QuarantineRecord], job_id: str
    ) -> None:
        """Persist quarantine records. Best-effort — does not fail the pipeline."""
        try:
            logger.info(
                "Quarantine records",
                count=len(quarantined),
                job_id=job_id,
                reasons=[q.reason for q in quarantined[:5]],
            )
            # In production, write to quarantine table via psycopg[async]
            # or push to a quarantine named graph in usf-kg
        except Exception as e:
            logger.warning("Failed to log quarantine records", error=str(e))

    async def _emit_openlineage(
        self, job_id: str, source: str, result: PipelineResult
    ) -> None:
        """Emit OpenLineage RunEvent to Marquez."""
        import asyncio

        try:
            import httpx

            event = {
                "eventType": "COMPLETE",
                "eventTime": datetime.now(timezone.utc).isoformat(),
                "run": {
                    "runId": job_id,
                    "facets": {
                        "unstructuredIngestion": {
                            "_producer": "https://usf.io/producers/usf-ingest",
                            "_schemaURL": "https://usf.io/schemas/unstructuredIngestion/v1",
                            "source": source,
                            "ontologyModule": result.ontology_module,
                            "chunksCount": result.chunks_count,
                            "extractionsCount": result.extractions_count,
                            "passedCount": result.passed_count,
                            "quarantinedCount": result.quarantined_count,
                            "insertedIrisCount": len(result.inserted_iris),
                        }
                    },
                },
                "job": {
                    "namespace": "usf-ingest",
                    "name": f"unstructured.{result.ontology_module}",
                },
                "inputs": [{"namespace": "documents", "name": source}],
                "outputs": [{"namespace": "usf-kg", "name": result.named_graph}],
            }

            async def post() -> None:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{self._config.openlineage_url}/api/v1/lineage",
                        json=event,
                        timeout=5.0,
                    )

            await asyncio.wait_for(post(), timeout=5.0)

        except Exception as e:
            # Non-critical: lineage emission failure should not fail the pipeline
            logger.warning("OpenLineage emit failed (non-critical)", error=str(e))
