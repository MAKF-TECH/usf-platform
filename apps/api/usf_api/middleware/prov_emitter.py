from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


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
    Build a PROV-O JSON-LD provenance block.
    
    Based on W3C PROV-O: https://www.w3.org/TR/prov-o/
    Activity = the query execution
    Agent = the user
    Entity = the result dataset
    """
    now = utcnow().isoformat()
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
