"""PROV-O builder — produce JSON-LD provenance blocks."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProvOBuilder:
    """Build PROV-O JSON-LD blocks for USF queries and ingestion runs."""

    CONTEXT = {
        "prov": "http://www.w3.org/ns/prov#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "usf": "https://usf.makf.tech/ontology/",
    }

    def query_activity(
        self,
        *,
        query_hash: str,
        sparql_text: str | None = None,
        context: str | None = None,
        user_iri: str | None = None,
        used_graphs: list[str] | None = None,
        generated_result_iri: str | None = None,
        started_at: str | None = None,
        ended_at: str | None = None,
    ) -> dict[str, Any]:
        """Build a PROV-O Activity block for a SPARQL/SQL query execution."""
        activity_iri = f"https://usf.makf.tech/prov/query/{query_hash}"
        doc: dict[str, Any] = {
            "@context": self.CONTEXT,
            "@id": activity_iri,
            "@type": "prov:Activity",
            "prov:startedAtTime": {
                "@value": started_at or _now_iso(),
                "@type": "xsd:dateTime",
            },
            "prov:endedAtTime": {
                "@value": ended_at or _now_iso(),
                "@type": "xsd:dateTime",
            },
            "usf:queryHash": query_hash,
        }
        if context:
            doc["usf:context"] = context
        if sparql_text:
            doc["usf:sparqlText"] = sparql_text
        if user_iri:
            doc["prov:wasAssociatedWith"] = {"@id": user_iri}
        if used_graphs:
            doc["prov:used"] = [{"@id": g} for g in used_graphs]
        if generated_result_iri:
            doc["prov:generated"] = {"@id": generated_result_iri}
        return doc

    def ingestion_activity(
        self,
        *,
        job_id: str,
        source_iri: str,
        tenant_iri: str,
        triples_added: int,
        ontology_version: str | None = None,
        extraction_model: str | None = None,
        named_graph_iri: str | None = None,
        started_at: str | None = None,
        ended_at: str | None = None,
    ) -> dict[str, Any]:
        """Build a PROV-O Activity block for a data ingestion run."""
        activity_iri = f"https://usf.makf.tech/prov/ingest/{job_id}"
        doc: dict[str, Any] = {
            "@context": self.CONTEXT,
            "@id": activity_iri,
            "@type": "prov:Activity",
            "prov:startedAtTime": {
                "@value": started_at or _now_iso(),
                "@type": "xsd:dateTime",
            },
            "prov:endedAtTime": {
                "@value": ended_at or _now_iso(),
                "@type": "xsd:dateTime",
            },
            "prov:used": {"@id": source_iri},
            "prov:wasAssociatedWith": {"@id": tenant_iri},
            "usf:triplesAdded": triples_added,
        }
        if ontology_version:
            doc["usf:ontologyVersion"] = ontology_version
        if extraction_model:
            doc["usf:extractionModel"] = extraction_model
        if named_graph_iri:
            doc["prov:generated"] = {"@id": named_graph_iri}
        return doc

    def entity_derivation(
        self,
        *,
        entity_iri: str,
        derived_from_iris: list[str],
        activity_iri: str | None = None,
    ) -> dict[str, Any]:
        """Build a prov:wasDerivedFrom chain for an entity."""
        doc: dict[str, Any] = {
            "@context": self.CONTEXT,
            "@id": entity_iri,
            "@type": "prov:Entity",
            "prov:wasDerivedFrom": [{"@id": iri} for iri in derived_from_iris],
        }
        if activity_iri:
            doc["prov:wasGeneratedBy"] = {"@id": activity_iri}
        return doc
