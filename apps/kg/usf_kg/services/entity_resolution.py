"""Entity resolution — match entities across sources, assign canonical IRI."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from loguru import logger
from rdflib import URIRef

from .qlever import QLeverService
from .arcadedb import ArcadeDBClient


def _levenshtein_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _canonical_iri(tenant_id: str, ontology_class: str, label: str) -> str:
    """Generate a canonical IRI for a new entity."""
    slug = hashlib.sha256(label.encode()).hexdigest()[:8]
    safe_class = ontology_class.split("/")[-1].split("#")[-1]
    return f"usf://{tenant_id}/entity/{safe_class}/{slug}"


@dataclass
class ResolvedEntity:
    canonical_iri: str
    is_new: bool
    confidence: float
    same_as_iri: str | None = None  # IRI of matched existing entity


class EntityResolutionService:
    """
    Resolve candidate entity labels/IRIs to canonical IRIs.

    Strategy:
    1. Check exact IRI match in ArcadeDB
    2. Vector similarity search for near-matches (threshold 0.85)
    3. If match: return canonical IRI + write owl:sameAs triple
    4. If new: generate canonical IRI = usf://{tenant}/entity/{class}/{sha256(label)[:8]}
    5. Write owl:sameAs to QLever provenance graph
    """

    OWL_SAME_AS = "http://www.w3.org/2002/07/owl#sameAs"
    PROV_GRAPH = "usf://provenance/entity-resolution"
    VECTOR_THRESHOLD = 0.85

    def __init__(self, qlever: QLeverService, arcadedb: ArcadeDBClient | None = None) -> None:
        self._qlever = qlever
        self._arcadedb = arcadedb

    async def resolve_entity(
        self,
        candidate_label: str,
        ontology_class: str,
        tenant_id: str,
        embedding: list[float] | None = None,
    ) -> ResolvedEntity:
        """
        Resolve a candidate entity label to a canonical IRI.

        1. Check for exact IRI match in ArcadeDB (iri == candidate_label)
        2. Vector similarity search if embedding provided (threshold 0.85)
        3. If match found: return canonical IRI + write owl:sameAs
        4. If new: generate canonical IRI, write to ArcadeDB
        5. Write owl:sameAs to QLever provenance graph
        """
        # Step 1: exact IRI lookup
        if self._arcadedb and (
            candidate_label.startswith("http") or candidate_label.startswith("usf://")
        ):
            existing = await self._arcadedb.get_node(candidate_label)
            if existing:
                canonical = existing.get("iri", candidate_label)
                logger.info(
                    "Entity resolved via exact IRI",
                    canonical=canonical,
                    candidate=candidate_label,
                )
                return ResolvedEntity(
                    canonical_iri=canonical,
                    is_new=False,
                    confidence=1.0,
                    same_as_iri=None,
                )

        # Step 2: vector similarity search
        if self._arcadedb and embedding:
            label_class = ontology_class.split("/")[-1].split("#")[-1]
            results = await self._arcadedb.vector_search(
                embedding=embedding,
                top_k=5,
                label=label_class,
            )
            for row in results:
                score = float(row.get("score", 0.0))
                if score >= self.VECTOR_THRESHOLD:
                    matched_iri = row.get("iri", "")
                    if not matched_iri:
                        continue
                    # Write owl:sameAs to QLever
                    candidate_iri = _canonical_iri(tenant_id, ontology_class, candidate_label)
                    await self._write_same_as(candidate_iri, matched_iri)
                    logger.info(
                        "Entity resolved via vector search",
                        canonical=matched_iri,
                        candidate=candidate_label,
                        score=score,
                    )
                    return ResolvedEntity(
                        canonical_iri=matched_iri,
                        is_new=False,
                        confidence=round(score, 4),
                        same_as_iri=candidate_iri,
                    )

        # Step 3: Generate new canonical IRI
        canonical_iri = _canonical_iri(tenant_id, ontology_class, candidate_label)

        # Persist in ArcadeDB for future lookups
        if self._arcadedb:
            label_class = ontology_class.split("/")[-1].split("#")[-1]
            await self._arcadedb.upsert_node(
                label=label_class,
                iri=canonical_iri,
                properties={"label": candidate_label, "ontologyClass": ontology_class},
            )

        logger.info(
            "New entity created",
            canonical=canonical_iri,
            candidate=candidate_label,
            class_=ontology_class,
        )
        return ResolvedEntity(
            canonical_iri=canonical_iri,
            is_new=True,
            confidence=1.0,
        )

    async def _write_same_as(self, from_iri: str, to_iri: str) -> None:
        """Write owl:sameAs triple to QLever provenance graph."""
        from usf_rdf.triples import Triple
        triples = [
            Triple(
                subject=URIRef(from_iri),
                predicate=URIRef(self.OWL_SAME_AS),
                obj=URIRef(to_iri),
            )
        ]
        try:
            await self._qlever.insert_triples(self.PROV_GRAPH, triples)
        except Exception as exc:
            logger.warning("Failed to write owl:sameAs to QLever", error=str(exc))

    # ── Legacy method: resolve multiple IRIs ─────────────────────────────────

    async def resolve(
        self,
        candidate_iris: list[str],
        strategy: str = "levenshtein",
    ) -> dict[str, Any]:
        """
        Compare multiple candidate IRIs and return the canonical IRI + confidence.
        Inserts owl:sameAs into QLever if confidence > threshold.
        """
        if len(candidate_iris) < 2:
            raise ValueError("Need at least 2 candidate IRIs to resolve")

        canonical = self._pick_canonical(candidate_iris)

        confidence = 1.0
        if strategy == "levenshtein":
            scores = [
                _levenshtein_ratio(canonical, iri)
                for iri in candidate_iris
                if iri != canonical
            ]
            confidence = sum(scores) / len(scores) if scores else 1.0

        logger.info(
            "Entity resolution",
            canonical=canonical,
            candidates=candidate_iris,
            confidence=confidence,
        )

        from usf_rdf.triples import Triple
        triples = [
            Triple(
                subject=URIRef(iri),
                predicate=URIRef(self.OWL_SAME_AS),
                obj=URIRef(canonical),
            )
            for iri in candidate_iris
            if iri != canonical
        ]
        if triples:
            await self._qlever.insert_triples(self.PROV_GRAPH, triples)

        return {
            "canonical_iri": canonical,
            "merged_iris": candidate_iris,
            "confidence": round(confidence, 4),
        }

    def _pick_canonical(self, iris: list[str]) -> str:
        """Pick the most canonical IRI: prefer usf:// namespace, then shortest."""
        usf_iris = [i for i in iris if i.startswith("https://usf.makf.tech/")]
        if usf_iris:
            return min(usf_iris, key=len)
        return min(iris, key=len)
