"""SKOS aligner — map SDL terms to FIBO/FHIR IRIs via skos:exactMatch."""
from __future__ import annotations

from rdflib import Graph, URIRef, Namespace
from rdflib.namespace import SKOS

USF = Namespace("https://usf.makf.tech/ontology/")

# Static alignment table — SDL name → FIBO/FHIR IRI
_KNOWN_ALIGNMENTS: dict[str, str] = {
    "Account": "https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/Account",
    "Bank": "https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/FinancialInstitutions/CommercialBank",
    "LegalEntity": "https://spec.edmcouncil.org/fibo/ontology/BE/LegalEntities/LegalPersons/LegalEntity",
    "Transaction": "https://usf.makf.tech/ontology/FinancialTransaction",
    # FHIR alignments
    "Patient": "http://hl7.org/fhir/Patient",
    "Observation": "http://hl7.org/fhir/Observation",
    "Encounter": "http://hl7.org/fhir/Encounter",
}


class SKOSAligner:
    """Align SDL entity names to canonical ontology IRIs using SKOS exactMatch."""

    def align(self, entity_name: str, namespace: str | None = None) -> str | None:
        """Return the best-known canonical IRI for an SDL entity name."""
        # Direct match
        if entity_name in _KNOWN_ALIGNMENTS:
            return _KNOWN_ALIGNMENTS[entity_name]
        # Suffix match
        for key, iri in _KNOWN_ALIGNMENTS.items():
            if entity_name.lower() == key.lower():
                return iri
        return None

    def generate_skos_mappings(self, sdl: dict) -> str:
        """
        Generate a Turtle document of skos:exactMatch triples for all SDL entities.
        Returns Turtle string.
        """
        g = Graph()
        g.bind("skos", SKOS)
        g.bind("usf", USF)

        ns = Namespace(sdl.get("namespace", str(USF)))
        g.bind("ns", ns)

        for entity in sdl.get("entities", []):
            entity_name = entity["name"]
            local_iri = URIRef(ns + entity_name)
            fibo_class = entity.get("fibo_class")

            if fibo_class:
                g.add((local_iri, SKOS.exactMatch, URIRef(fibo_class)))
            else:
                canonical = self.align(entity_name)
                if canonical:
                    g.add((local_iri, SKOS.exactMatch, URIRef(canonical)))

        return g.serialize(format="turtle")
