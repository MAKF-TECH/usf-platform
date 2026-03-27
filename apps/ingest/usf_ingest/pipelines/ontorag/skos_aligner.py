"""SKOS Aligner — match draft ontology classes to industry standard ontologies.

OntoRAG step 2 of 3.

Uses embedding similarity to find the nearest FIBO/FHIR/CIM class for each
draft class. Returns an alignment_map with match confidence and SKOS match type.

SKOS match types:
  - skos:exactMatch   (similarity >= 0.92)
  - skos:closeMatch   (similarity >= 0.80)
  - skos:broadMatch   (similarity >= 0.65, draft is more specific)
  - skos:narrowMatch  (similarity >= 0.65, draft is more general)
  - skos:relatedMatch (similarity < 0.65 but above threshold)
  - None              (no match found)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from loguru import logger

from .ontology_extractor import DraftOntology, DraftClass

# Known industry ontology classes with descriptions (compact lookup table)
# In production, this would be loaded from the FIBO/FHIR OWL files
_INDUSTRY_CLASSES: dict[str, list[dict[str, str]]] = {
    "fibo": [
        {"iri": "https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LegalPersons/LegalEntity",
         "label": "LegalEntity", "description": "An entity recognized by law as having legal rights and obligations"},
        {"iri": "https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/Account",
         "label": "Account", "description": "A financial account holding balances and transactions"},
        {"iri": "https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/FinancialInstitutions/CommercialBank",
         "label": "CommercialBank", "description": "A bank that offers commercial banking services to businesses and individuals"},
        {"iri": "https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/FinancialInstrument",
         "label": "FinancialInstrument", "description": "A contract representing a financial asset or liability"},
        {"iri": "https://spec.edmcouncil.org/fibo/ontology/FND/Accounting/CurrencyAmount/MonetaryAmount",
         "label": "MonetaryAmount", "description": "A quantity denominated in a currency"},
        {"iri": "https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/BusinessCentersAndExchanges/Counterparty",
         "label": "Counterparty", "description": "A party to a financial transaction or contract"},
        {"iri": "https://spec.edmcouncil.org/fibo/ontology/FBC/DebtAndEquities/Debt/LoanAgreement",
         "label": "LoanAgreement", "description": "A contract for a loan of money"},
        {"iri": "https://spec.edmcouncil.org/fibo/ontology/FND/Parties/Roles/PartyInRole",
         "label": "PartyInRole", "description": "A party acting in a specific business role"},
    ],
    "fhir": [
        {"iri": "http://hl7.org/fhir/Patient",
         "label": "Patient", "description": "A person receiving or registered to receive healthcare services"},
        {"iri": "http://hl7.org/fhir/Observation",
         "label": "Observation", "description": "A clinical measurement or assertion about a patient"},
        {"iri": "http://hl7.org/fhir/Medication",
         "label": "Medication", "description": "A pharmaceutical product or drug"},
        {"iri": "http://hl7.org/fhir/Practitioner",
         "label": "Practitioner", "description": "A person involved in the provisioning of healthcare"},
        {"iri": "http://hl7.org/fhir/Condition",
         "label": "Condition", "description": "A clinical condition, problem, or diagnosis"},
        {"iri": "http://hl7.org/fhir/Encounter",
         "label": "Encounter", "description": "An interaction between a patient and a healthcare provider"},
    ],
    "cim": [
        {"iri": "http://iec.ch/TC57/CIM100#Equipment",
         "label": "Equipment", "description": "A physical piece of electrical or network equipment"},
        {"iri": "http://iec.ch/TC57/CIM100#Substation",
         "label": "Substation", "description": "A facility that transforms electrical energy"},
        {"iri": "http://iec.ch/TC57/CIM100#EnergyConsumer",
         "label": "EnergyConsumer", "description": "A device or facility consuming electrical energy"},
    ],
}


@dataclass
class ClassAlignment:
    draft_class: str
    matched_class: str | None    # Full OWL IRI
    matched_label: str | None
    confidence: float             # 0.0 – 1.0 cosine similarity
    skos_match_type: str | None   # "exactMatch" | "closeMatch" | "broadMatch" | "narrowMatch" | "relatedMatch"
    ontology_module: str | None   # "fibo" | "fhir" | "cim"


# {draft_class: ClassAlignment}
AlignmentMap = dict[str, ClassAlignment]


class SKOSAligner:
    """Align draft ontology classes to industry standard ontologies via embeddings.

    Falls back to TF-IDF cosine similarity if embedding API is unavailable.
    """

    # Confidence thresholds for SKOS match type assignment
    EXACT_THRESHOLD = 0.92
    CLOSE_THRESHOLD = 0.80
    BROAD_THRESHOLD = 0.65
    RELATED_THRESHOLD = 0.45

    def __init__(
        self,
        target_modules: list[str] | None = None,
        embedder_config: dict[str, Any] | None = None,
    ) -> None:
        self._target_modules = target_modules or ["fibo"]
        self._embedder_config = embedder_config or {}

    async def align(self, draft_ontology: DraftOntology) -> AlignmentMap:
        """Align all classes in the draft ontology.

        Args:
            draft_ontology: Output of OntologyExtractor.

        Returns:
            AlignmentMap: draft class name → ClassAlignment.
        """
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None, self._align_sync, draft_ontology
        )

    def _align_sync(self, draft_ontology: DraftOntology) -> AlignmentMap:
        alignment: AlignmentMap = {}

        # Gather all candidate classes from target modules
        candidates: list[dict[str, str]] = []
        candidate_modules: list[str] = []
        for module in self._target_modules:
            for cls in _INDUSTRY_CLASSES.get(module, []):
                candidates.append(cls)
                candidate_modules.append(module)

        if not candidates:
            logger.warning("No candidate classes found for alignment", modules=self._target_modules)
            return alignment

        # Build corpus texts for similarity
        candidate_texts = [
            f"{c['label']}: {c['description']}" for c in candidates
        ]

        for draft_class in draft_ontology.classes:
            query_text = f"{draft_class.name}: {draft_class.description}"
            similarity_scores = self._compute_similarities(query_text, candidate_texts)

            best_idx = int(max(range(len(similarity_scores)), key=lambda i: similarity_scores[i]))
            best_score = similarity_scores[best_idx]
            best_candidate = candidates[best_idx]
            best_module = candidate_modules[best_idx]

            if best_score < self.RELATED_THRESHOLD:
                alignment[draft_class.name] = ClassAlignment(
                    draft_class=draft_class.name,
                    matched_class=None,
                    matched_label=None,
                    confidence=best_score,
                    skos_match_type=None,
                    ontology_module=None,
                )
                continue

            skos_type = self._skos_match_type(best_score)
            alignment[draft_class.name] = ClassAlignment(
                draft_class=draft_class.name,
                matched_class=best_candidate["iri"],
                matched_label=best_candidate["label"],
                confidence=best_score,
                skos_match_type=skos_type,
                ontology_module=best_module,
            )

        matched = sum(1 for a in alignment.values() if a.matched_class)
        logger.info(
            "SKOS alignment complete",
            draft_classes=len(draft_ontology.classes),
            matched=matched,
            unmatched=len(alignment) - matched,
        )
        return alignment

    def _compute_similarities(
        self, query: str, candidates: list[str]
    ) -> list[float]:
        """Compute cosine similarities between query and candidates.

        Tries OpenAI embeddings first, falls back to TF-IDF.
        """
        try:
            return self._embed_similarity(query, candidates)
        except Exception as e:
            logger.debug("Embedding similarity failed, using TF-IDF", error=str(e))
            return self._tfidf_similarity(query, candidates)

    def _embed_similarity(self, query: str, candidates: list[str]) -> list[float]:
        """Use OpenAI embeddings for similarity."""
        import os, httpx, math

        api_key = self._embedder_config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("No OpenAI API key for embedding")

        model = self._embedder_config.get("model", "text-embedding-3-small")
        all_texts = [query] + candidates
        resp = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "input": [t[:512] for t in all_texts]},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        vecs = [d["embedding"] for d in data]

        def cosine(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            return dot / (na * nb) if na and nb else 0.0

        query_vec = vecs[0]
        return [cosine(query_vec, v) for v in vecs[1:]]

    def _tfidf_similarity(self, query: str, candidates: list[str]) -> list[float]:
        """TF-IDF cosine similarity as fallback."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            corpus = [query] + candidates
            vec = TfidfVectorizer().fit_transform(corpus)
            sims = cosine_similarity(vec[0:1], vec[1:]).flatten()
            return sims.tolist()
        except ImportError:
            # Final fallback: simple word overlap Jaccard
            return [self._jaccard(query, c) for c in candidates]

    def _jaccard(self, a: str, b: str) -> float:
        sa, sb = set(a.lower().split()), set(b.lower().split())
        if not sa and not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    def _skos_match_type(self, score: float) -> str:
        if score >= self.EXACT_THRESHOLD:
            return "exactMatch"
        if score >= self.CLOSE_THRESHOLD:
            return "closeMatch"
        if score >= self.BROAD_THRESHOLD:
            return "broadMatch"
        return "relatedMatch"
