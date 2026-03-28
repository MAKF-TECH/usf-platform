from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from usf_api.middleware.abac import TokenClaims


# ── Pydantic models for prov metadata ────────────────────────────────────────

class QueryMeta(BaseModel):
    """Metadata captured during query execution for provenance."""
    started_at: datetime
    ended_at: datetime
    query_hash: str
    backend: Any  # QueryBackend enum or string
    policy_version: str = "unknown"
    ontology_version: str = "latest"
    data_sources: list[str] = []


class SemanticQueryRef(BaseModel):
    """Minimal reference to the query for provenance (avoids circular imports)."""
    context: str
    ontology_version: str = "latest"
    query_hash: str | None = None


# ── PROV-O builders ───────────────────────────────────────────────────────────

def build_prov_block(
    query: SemanticQueryRef,
    result_meta: QueryMeta,
    user: TokenClaims,
) -> dict[str, Any]:
    """
    Build a W3C PROV-O JSON-LD provenance block.

    Represents:
      - prov:Entity  — the result dataset
      - prov:Activity — the query execution
      - prov:Agent    — the user who ran the query
    """
    backend_val = (
        result_meta.backend.value
        if hasattr(result_meta.backend, "value")
        else str(result_meta.backend)
    )

    return {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "usf": "https://usf.io/vocab/",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        },
        "@type": "prov:Entity",
        "prov:wasGeneratedBy": {
            "@type": "prov:Activity",
            "prov:startedAtTime": {
                "@value": result_meta.started_at.isoformat(),
                "@type": "xsd:dateTime",
            },
            "prov:endedAtTime": {
                "@value": result_meta.ended_at.isoformat(),
                "@type": "xsd:dateTime",
            },
            "usf:semanticModelVersion": query.context + "/latest",
            "usf:ontologyVersion": result_meta.ontology_version,
            "usf:contextApplied": query.context,
            "usf:abacPolicy": result_meta.policy_version,
            "usf:queryHash": result_meta.query_hash,
            "usf:backend": backend_val,
        },
        "prov:wasAttributedTo": {
            "@id": f"usf://user/{user.user_id}",
        },
        "prov:wasDerivedFrom": result_meta.data_sources,
    }


# ── Typed models for spec build_prov_block ────────────────────────────────────

class QueryMeta(BaseModel):
    """Execution metadata captured during query for provenance."""
    started_at: datetime
    ended_at: datetime
    query_hash: str
    backend: Any  # QueryBackend enum or str
    policy_version: str = "unknown"
    ontology_version: str = "latest"
    data_sources: list[str] = []


class SemanticQueryRef(BaseModel):
    """Minimal query reference for provenance (avoids circular imports)."""
    context: str
    ontology_version: str = "latest"


def build_prov_block(
    query: SemanticQueryRef,
    result_meta: QueryMeta,
    user: Any,  # TokenClaims or str user_id
) -> dict[str, Any]:
    """
    Build a W3C PROV-O JSON-LD provenance block per spec.

    Returns a prov:Entity JSON-LD dict with embedded Activity and attribution.
    """
    backend_val = (
        result_meta.backend.value
        if hasattr(result_meta.backend, "value")
        else str(result_meta.backend)
    )
    user_id = user.user_id if hasattr(user, "user_id") else str(user)

    return {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "usf": "https://usf.io/vocab/",
        },
        "@type": "prov:Entity",
        "prov:wasGeneratedBy": {
            "@type": "prov:Activity",
            "prov:startedAtTime": result_meta.started_at.isoformat(),
            "prov:endedAtTime": result_meta.ended_at.isoformat(),
            "usf:semanticModelVersion": query.context + "/latest",
            "usf:ontologyVersion": result_meta.ontology_version,
            "usf:contextApplied": query.context,
            "usf:abacPolicy": result_meta.policy_version,
            "usf:queryHash": result_meta.query_hash,
            "usf:backend": backend_val,
        },
        "prov:wasAttributedTo": {
            "@id": f"usf://user/{user_id}",
        },
        "prov:wasDerivedFrom": result_meta.data_sources,
    }


def build_prov_o(
    query_id: str,
    user_id: str,
    tenant_id: str,
    context: str | None,
    query_hash: str | None,
    abac_decision: str,
    backend: str | None = None,
) -> dict[str, Any]:
    """
    Legacy compatibility builder — same interface as original build_prov_o.
    Returns a PROV-O JSON-LD @graph structure.
    """
    now = datetime.now(tz=timezone.utc).isoformat()
    activity_id = f"urn:usf:activity:{query_id}"
    agent_id = f"urn:usf:agent:{user_id}"
    entity_id = f"urn:usf:entity:result:{query_id}"

    return {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "usf": "urn:usf:",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        },
        "@graph": [
            {
                "@id": activity_id,
                "@type": "prov:Activity",
                "prov:startedAtTime": {"@value": now, "@type": "xsd:dateTime"},
                "prov:wasAssociatedWith": {"@id": agent_id},
                "usf:queryHash": query_hash,
                "usf:context": context,
                "usf:tenantId": tenant_id,
                "usf:backendUsed": backend,
                "usf:abacDecision": abac_decision,
            },
            {
                "@id": agent_id,
                "@type": "prov:Agent",
                "usf:userId": user_id,
                "usf:tenantId": tenant_id,
            },
            {
                "@id": entity_id,
                "@type": "prov:Entity",
                "prov:wasGeneratedBy": {"@id": activity_id},
                "prov:generatedAtTime": {"@value": now, "@type": "xsd:dateTime"},
            },
        ],
    }
