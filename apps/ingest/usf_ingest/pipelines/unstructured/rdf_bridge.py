"""RDF bridge — convert ArcadeDB nodes/edges to RDF triples and POST to usf-kg.

Maps Cypher node vertex types to OWL classes using the FIBO/FHIR bridge.
Generates prov:wasGeneratedBy triples with extraction provenance metadata.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from loguru import logger


# Namespace prefixes
_NS = {
    "fibo-be": "https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LegalPersons/",
    "fibo-fbc": "https://spec.edmcouncil.org/fibo/ontology/FBC/",
    "fibo-fnd": "https://spec.edmcouncil.org/fibo/ontology/FND/",
    "fhir": "http://hl7.org/fhir/",
    "cim": "http://iec.ch/TC57/CIM100#",
    "prov": "http://www.w3.org/ns/prov#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "usf": "https://usf.io/ontology/",
    "prov-act": "https://usf.io/provenance/activity/",
    "prov-agent": "https://usf.io/provenance/agent/",
}

# Map short ontology class names → full OWL class IRIs
_CLASS_IRI_MAP: dict[str, str] = {
    # FIBO
    "fibo:LegalEntity": "https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LegalPersons/LegalEntity",
    "fibo:Account": "https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/Account",
    "fibo:CommercialBank": "https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/FinancialInstitutions/CommercialBank",
    "fibo:Transaction": "https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/FinancialInstrument",
    "fibo:Counterparty": "https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/BusinessCentersAndExchanges/Counterparty",
    "fibo:MonetaryAmount": "https://spec.edmcouncil.org/fibo/ontology/FND/Accounting/CurrencyAmount/MonetaryAmount",
    # FHIR
    "fhir:Patient": "http://hl7.org/fhir/Patient",
    "fhir:Observation": "http://hl7.org/fhir/Observation",
    "fhir:Medication": "http://hl7.org/fhir/Medication",
    # USF generic fallback
    "Entity": "https://usf.io/ontology/Entity",
}

# Vertex type → FIBO class mapping
_VERTEX_CLASS_MAP: dict[str, str] = {
    "LegalEntity": "fibo:LegalEntity",
    "FinancialAccount": "fibo:Account",
    "FinancialTransaction": "fibo:Transaction",
    "Counterparty": "fibo:Counterparty",
    "MonetaryAmount": "fibo:MonetaryAmount",
    "Patient": "fhir:Patient",
    "ClinicalObservation": "fhir:Observation",
    "Medication": "fhir:Medication",
}


def _resolve_class_iri(ontology_class: str) -> str:
    """Resolve a short ontology class name to its full OWL IRI."""
    if ontology_class in _CLASS_IRI_MAP:
        return _CLASS_IRI_MAP[ontology_class]
    # Try stripping to last segment
    short = ontology_class.split(":")[-1].split("/")[-1]
    for k, v in _CLASS_IRI_MAP.items():
        if k.split(":")[-1] == short:
            return v
    # Return as-is if already an IRI
    if ontology_class.startswith("http"):
        return ontology_class
    return f"https://usf.io/ontology/{short}"


@dataclass
class TripleSet:
    """A set of RDF triples ready for insertion into usf-kg."""

    entity_triples: list[tuple[str, str, str]] = field(default_factory=list)
    prov_triples: list[tuple[str, str, str]] = field(default_factory=list)
    named_graph: str = "usf://graph/default"

    def all_triples(self) -> list[tuple[str, str, str]]:
        return self.entity_triples + self.prov_triples


class RDFBridge:
    """Convert ArcadeDB node IRIs + ExtractionResults to RDF and POST to usf-kg.

    Uses rdflib to build the graph in memory, then serialises to Turtle
    and POSTs to the usf-kg /triples endpoint.
    """

    def __init__(self, usf_kg_url: str, tenant_id: str = "default") -> None:
        self._usf_kg_url = usf_kg_url.rstrip("/")
        self._tenant_id = tenant_id

    async def convert_and_post(
        self,
        extraction_results: list[Any],   # list[ExtractionResult]
        inserted_iris: list[str],
        job_id: str,
        source_uri: str,
        model_id: str,
        named_graph: str | None = None,
    ) -> TripleSet:
        """Convert extractions to RDF and POST to usf-kg.

        Args:
            extraction_results: Filtered ExtractionResult list.
            inserted_iris: Canonical IRIs from ArcadeDBBuilder.
            job_id: Ingestion job ID for PROV-O.
            source_uri: Source document URI.
            model_id: LLM used for extraction.
            named_graph: Target named graph in usf-kg.

        Returns:
            TripleSet of generated triples.
        """
        import asyncio

        triples = await asyncio.get_event_loop().run_in_executor(
            None,
            self._build_triples,
            extraction_results,
            inserted_iris,
            job_id,
            source_uri,
            model_id,
            named_graph,
        )
        await self._post_triples(triples)
        return triples

    def _build_triples(
        self,
        extractions: list[Any],
        iris: list[str],
        job_id: str,
        source_uri: str,
        model_id: str,
        named_graph: str | None,
    ) -> TripleSet:
        try:
            from rdflib import Graph, URIRef, Literal, Namespace
            from rdflib.namespace import RDF, RDFS, OWL, XSD
        except ImportError as exc:
            raise RuntimeError("rdflib is not installed.") from exc

        PROV = Namespace(_NS["prov"])
        USF = Namespace(_NS["usf"])
        PROV_ACT = Namespace(_NS["prov-act"])
        PROV_AGENT = Namespace(_NS["prov-agent"])

        g = Graph()
        for prefix, uri in _NS.items():
            g.bind(prefix.replace("-", "_"), uri)

        # PROV-O activity node
        now_iso = datetime.now(timezone.utc).isoformat()
        activity_iri = URIRef(f"{_NS['prov-act']}{job_id}")
        agent_iri = URIRef(f"{_NS['prov-agent']}langextract/{model_id}")

        g.add((activity_iri, RDF.type, PROV.Activity))
        g.add((activity_iri, PROV.startedAtTime, Literal(now_iso, datatype=XSD.dateTime)))
        g.add((activity_iri, URIRef(_NS["usf"] + "jobId"), Literal(job_id)))
        g.add((activity_iri, URIRef(_NS["usf"] + "modelId"), Literal(model_id)))
        g.add((activity_iri, URIRef(_NS["usf"] + "sourceUri"), URIRef(source_uri)))
        g.add((agent_iri, RDF.type, PROV.SoftwareAgent))
        g.add((agent_iri, RDFS.label, Literal(f"LangExtract/{model_id}")))
        g.add((activity_iri, PROV.wasAssociatedWith, agent_iri))

        entity_triples: list[tuple[str, str, str]] = []
        prov_triples: list[tuple[str, str, str]] = []

        for ext in extractions:
            if ext.char_interval is None:
                continue

            iri_str = next(
                (i for i in iris if ext.text_span.strip().lower().replace(" ", "-") in i),
                None,
            )
            if not iri_str:
                continue

            entity_ref = URIRef(iri_str)
            class_iri = URIRef(_resolve_class_iri(ext.ontology_class))

            # rdf:type triple
            g.add((entity_ref, RDF.type, class_iri))
            g.add((entity_ref, RDF.type, OWL.NamedIndividual))
            g.add((entity_ref, RDFS.label, Literal(ext.text_span)))

            # Attributes as data properties
            for attr_key, attr_val in ext.attributes.items():
                if attr_val is None:
                    continue
                prop_iri = URIRef(f"{_NS['usf']}{attr_key}")
                g.add((entity_ref, prop_iri, Literal(str(attr_val))))

            # PROV-O: entity was generated by the extraction activity
            g.add((entity_ref, PROV.wasGeneratedBy, activity_iri))
            g.add((entity_ref, PROV.wasDerivedFrom, URIRef(source_uri)))

            # char_interval as USF-specific annotation
            g.add((
                entity_ref,
                URIRef(_NS["usf"] + "charStart"),
                Literal(ext.char_interval[0], datatype=XSD.integer),
            ))
            g.add((
                entity_ref,
                URIRef(_NS["usf"] + "charEnd"),
                Literal(ext.char_interval[1], datatype=XSD.integer),
            ))
            g.add((
                entity_ref,
                URIRef(_NS["usf"] + "confidenceScore"),
                Literal(ext.confidence_score, datatype=XSD.decimal),
            ))

            entity_triples.append((iri_str, str(RDF.type), str(class_iri)))

        # Serialise graph to turtle for logging
        turtle_bytes = g.serialize(format="turtle").encode()
        logger.debug(
            "RDF bridge triples built",
            entity_count=len(entity_triples),
            turtle_bytes=len(turtle_bytes),
        )

        ng = named_graph or f"usf://graph/ingest/{self._tenant_id}/{job_id}"

        ts = TripleSet(
            entity_triples=entity_triples,
            prov_triples=prov_triples,
            named_graph=ng,
        )
        ts._turtle = turtle_bytes.decode()  # type: ignore[attr-defined]
        return ts

    async def _post_triples(self, triples: TripleSet) -> None:
        """POST Turtle triples to usf-kg /triples endpoint."""
        import asyncio

        turtle_content = getattr(triples, "_turtle", "")
        if not turtle_content:
            logger.warning("No RDF triples to post")
            return

        await asyncio.get_event_loop().run_in_executor(
            None,
            self._post_sync,
            turtle_content,
            triples.named_graph,
        )

    def _post_sync(self, turtle: str, named_graph: str) -> None:
        import httpx

        url = f"{self._usf_kg_url}/triples"
        payload = {
            "turtle": turtle,
            "named_graph": named_graph,
        }
        try:
            resp = httpx.post(url, json=payload, timeout=30.0)
            resp.raise_for_status()
            logger.info(
                "RDF triples posted to usf-kg",
                named_graph=named_graph,
                status=resp.status_code,
            )
        except Exception as e:
            logger.error("Failed to post RDF triples to usf-kg", error=str(e), url=url)
            raise
