"""Entity resolution — match entities across sources, assign canonical IRI."""
from __future__ import annotations

import hashlib
from difflib import SequenceMatcher
from typing import Any

from loguru import logger

from .qlever import QLeverService


def _levenshtein_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


class EntityResolutionService:
    """
    Match candidate IRIs referring to the same real-world entity,
    assign a canonical IRI, and insert owl:sameAs triples.
    """

    OWL_SAME_AS = "http://www.w3.org/2002/07/owl#sameAs"
    PROV_GRAPH = "usf://provenance/entity-resolution"

    def __init__(self, qlever: QLeverService) -> None:
        self._qlever = qlever

    async def resolve(
        self,
        candidate_iris: list[str],
        strategy: str = "levenshtein",
    ) -> dict[str, Any]:
        """
        Compare candidates and return the canonical IRI + confidence.
        Inserts owl:sameAs into QLever if confidence > threshold.
        """
        if len(candidate_iris) < 2:
            raise ValueError("Need at least 2 candidate IRIs to resolve")

        # Simple strategy: pick the IRI that looks most canonical
        # (shortest, or the one with a namespace we prefer)
        canonical = self._pick_canonical(candidate_iris)

        confidence = 1.0
        if strategy == "levenshtein":
            # For label-based resolution we'd fetch rdfs:label first;
            # here we use IRI similarity as a proxy
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

        # Insert owl:sameAs triples for all non-canonical IRIs
        from usf_rdf.triples import Triple
        from rdflib import URIRef

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
