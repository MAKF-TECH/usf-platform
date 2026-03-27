from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


def build_prov_o(query_id: str, user_id: str, tenant_id: str, context: str | None,
                  query_hash: str | None, abac_decision: str, backend: str | None = None) -> dict[str, Any]:
    now = datetime.now(tz=timezone.utc).isoformat()
    return {
        "@context": {"prov": "http://www.w3.org/ns/prov#", "usf": "urn:usf:", "xsd": "http://www.w3.org/2001/XMLSchema#"},
        "@graph": [
            {"@id": f"urn:usf:activity:{query_id}", "@type": "prov:Activity",
             "prov:startedAtTime": {"@value": now, "@type": "xsd:dateTime"},
             "prov:wasAssociatedWith": {"@id": f"urn:usf:agent:{user_id}"},
             "usf:queryHash": query_hash, "usf:context": context, "usf:tenantId": tenant_id,
             "usf:backendUsed": backend, "usf:abacDecision": abac_decision},
            {"@id": f"urn:usf:agent:{user_id}", "@type": "prov:Agent", "usf:tenantId": tenant_id},
            {"@id": f"urn:usf:entity:result:{query_id}", "@type": "prov:Entity",
             "prov:wasGeneratedBy": {"@id": f"urn:usf:activity:{query_id}"},
             "prov:generatedAtTime": {"@value": now, "@type": "xsd:dateTime"}},
        ],
    }
