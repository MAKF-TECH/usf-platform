"""ArcadeDB Knowledge Graph builder.

Adapted from the neo4j-graphrag-python pattern, re-implemented for ArcadeDB's
Cypher-over-HTTP API.

Pipeline:
1. Accept typed entities + relationships from LangExtract output
2. UPSERT each entity as an ArcadeDB vertex (merge on canonical IRI)
3. Create edges for relationships
4. Generate and store vector embeddings for entity name + description
5. Return list of canonical IRIs for all inserted nodes
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any
from loguru import logger


def _make_iri(ontology_class: str, text_span: str) -> str:
    """Generate a deterministic IRI from class + text span."""
    slug = text_span.strip().lower().replace(" ", "-")
    h = hashlib.sha256(f"{ontology_class}:{text_span}".encode()).hexdigest()[:8]
    safe_class = ontology_class.split(":")[-1].split("/")[-1]
    return f"usf://entity/{safe_class}/{slug}-{h}"


@dataclass
class ArcadeNode:
    iri: str
    vertex_type: str      # ArcadeDB vertex class name
    ontology_class: str   # Full FIBO/FHIR IRI
    label: str            # Human-readable label (text_span)
    attributes: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None


@dataclass
class ArcadeEdge:
    edge_type: str        # ArcadeDB edge class name
    from_iri: str
    to_iri: str
    attributes: dict[str, Any] = field(default_factory=dict)


class ArcadeDBClient:
    """Thin async-compatible HTTP client for ArcadeDB Cypher API."""

    def __init__(self, base_url: str, database: str, username: str, password: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._database = database
        self._auth = (username, password)

    async def execute_cypher(self, query: str, params: dict | None = None) -> Any:
        """POST a Cypher query to ArcadeDB and return the response JSON."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self._execute_sync, query, params or {}
        )

    def _execute_sync(self, query: str, params: dict) -> Any:
        import httpx

        url = f"{self._base_url}/api/v1/command/{self._database}"
        payload = {
            "language": "cypher",
            "command": query,
            "params": params,
        }
        resp = httpx.post(url, json=payload, auth=self._auth, timeout=30.0)
        resp.raise_for_status()
        return resp.json()

    async def check_health(self) -> bool:
        """Check ArcadeDB is reachable."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(None, self._health_sync)

    def _health_sync(self) -> bool:
        import httpx
        try:
            resp = httpx.get(f"{self._base_url}/api/v1/ready", timeout=5.0)
            return resp.status_code == 204
        except Exception:
            return False


class Embedder:
    """LLM-agnostic text embedder. Supports OpenAI and local sentence-transformers."""

    def __init__(self, provider: str = "openai", model: str = "text-embedding-3-small") -> None:
        self._provider = provider
        self._model = model

    async def embed(self, text: str) -> list[float]:
        """Return embedding vector for a text string."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(None, self._embed_sync, text)

    def _embed_sync(self, text: str) -> list[float]:
        if self._provider == "openai":
            return self._embed_openai(text)
        if self._provider == "local":
            return self._embed_local(text)
        logger.warning("Unknown embedder provider, skipping embedding", provider=self._provider)
        return []

    def _embed_openai(self, text: str) -> list[float]:
        import os
        import httpx

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set, skipping embedding")
            return []
        resp = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": self._model, "input": text[:8192]},
            timeout=20.0,
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]

    def _embed_local(self, text: str) -> list[float]:
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(self._model)
            return model.encode(text).tolist()
        except ImportError:
            logger.warning("sentence_transformers not installed, skipping embedding")
            return []


class ArcadeDBBuilder:
    """Build knowledge graph in ArcadeDB from typed extraction results.

    Adapted from neo4j-graphrag-python's SimpleKGPipeline pattern.
    """

    # Map ontology class short names → ArcadeDB vertex class names
    # These must be pre-created as vertex types in the database schema.
    _DEFAULT_VERTEX_TYPE_MAP: dict[str, str] = {
        "fibo:LegalEntity": "LegalEntity",
        "fibo:Account": "FinancialAccount",
        "fibo:Transaction": "FinancialTransaction",
        "fibo:Counterparty": "Counterparty",
        "fibo:MonetaryAmount": "MonetaryAmount",
        "fhir:Patient": "Patient",
        "fhir:Observation": "ClinicalObservation",
        "fhir:Medication": "Medication",
    }

    def __init__(
        self,
        client: ArcadeDBClient,
        embedder: Embedder | None = None,
        vertex_type_map: dict[str, str] | None = None,
    ) -> None:
        self._client = client
        self._embedder = embedder or Embedder()
        self._vertex_type_map = vertex_type_map or self._DEFAULT_VERTEX_TYPE_MAP

    def _resolve_vertex_type(self, ontology_class: str) -> str:
        """Map ontology class to ArcadeDB vertex type name."""
        # Direct match
        if ontology_class in self._vertex_type_map:
            return self._vertex_type_map[ontology_class]
        # Short name match (last segment of IRI or prefix:LocalName)
        short = ontology_class.split(":")[-1].split("/")[-1]
        for k, v in self._vertex_type_map.items():
            if k.split(":")[-1] == short or k.split("/")[-1] == short:
                return v
        # Default: use cleaned short name as vertex type
        return short or "Entity"

    async def build_knowledge_graph(
        self,
        entities: list[Any],  # list[ExtractionResult] after confidence filter
        relationship_types: list[str] | None = None,
        job_id: str | None = None,
    ) -> list[str]:
        """Insert entities into ArcadeDB and return their canonical IRIs.

        Args:
            entities: Passed ExtractionResult objects from ConfidenceFilter.
            relationship_types: Edge types to create (inferred from entity attrs).
            job_id: Optional job ID for provenance.

        Returns:
            List of canonical IRI strings for all created/updated nodes.
        """
        inserted_iris: list[str] = []

        for ext in entities:
            iri = _make_iri(ext.ontology_class, ext.text_span)
            vertex_type = self._resolve_vertex_type(ext.ontology_class)

            # Build embedding
            embedding: list[float] = []
            if self._embedder:
                try:
                    embedding = await self._embedder.embed(
                        f"{ext.ontology_class}: {ext.text_span}"
                    )
                except Exception as e:
                    logger.warning("Embedding failed", iri=iri, error=str(e))

            node = ArcadeNode(
                iri=iri,
                vertex_type=vertex_type,
                ontology_class=ext.ontology_class,
                label=ext.text_span,
                attributes={
                    **ext.attributes,
                    "model_id": ext.model_id,
                    "confidence_score": ext.confidence_score,
                    "char_start": ext.char_interval[0] if ext.char_interval else None,
                    "char_end": ext.char_interval[1] if ext.char_interval else None,
                    "job_id": job_id,
                },
                embedding=embedding or None,
            )

            try:
                await self._upsert_vertex(node)
                inserted_iris.append(iri)
            except Exception as e:
                logger.error(
                    "Failed to upsert vertex",
                    iri=iri,
                    vertex_type=vertex_type,
                    error=str(e),
                )

        logger.info(
            "ArcadeDB KG build complete",
            total_entities=len(entities),
            inserted=len(inserted_iris),
            job_id=job_id,
        )
        return inserted_iris

    async def _upsert_vertex(self, node: ArcadeNode) -> None:
        """UPSERT a vertex into ArcadeDB (merge on iri property)."""
        # ArcadeDB Cypher: MERGE on iri, set all properties
        props = {
            "iri": node.iri,
            "ontology_class": node.ontology_class,
            "label": node.label,
            **node.attributes,
        }
        # Filter out None values — Cypher SET won't accept None
        props = {k: v for k, v in props.items() if v is not None}

        # Store embedding as a separate property if present
        if node.embedding:
            props["embedding"] = node.embedding

        # Build SET clause
        set_parts = [f"n.{k} = ${k}" for k in props if k != "iri"]
        set_clause = ", ".join(set_parts) if set_parts else "n.iri = $iri"

        cypher = (
            f"MERGE (n:{node.vertex_type} {{iri: $iri}}) "
            f"SET {set_clause} "
            f"RETURN n.iri"
        )

        await self._client.execute_cypher(cypher, props)

    async def create_edge(self, edge: ArcadeEdge) -> None:
        """Create a directed edge between two existing vertices."""
        cypher = (
            f"MATCH (a {{iri: $from_iri}}), (b {{iri: $to_iri}}) "
            f"MERGE (a)-[r:{edge.edge_type}]->(b) "
            f"SET r += $attrs "
            f"RETURN r"
        )
        params = {
            "from_iri": edge.from_iri,
            "to_iri": edge.to_iri,
            "attrs": edge.attributes,
        }
        await self._client.execute_cypher(cypher, params)
