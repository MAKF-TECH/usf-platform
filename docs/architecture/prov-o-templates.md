# USF PROV-O JSON-LD Templates

**Version**: 1.0.0  
**Status**: FROZEN  
**Date**: 2026-03-27  
**Author**: usf-architect

> PROV-O templates define the provenance structure for all USF activities.
> Every query result, ingestion batch, and SDL publish carries a PROV-O block.
> The PROV-O graph is stored in QLever under `usf://{tenant}/provenance/{date}`.
> Templates use `{placeholder}` syntax — the PROV-O builder substitutes at runtime.

---

## Namespace Prefixes (used in all templates)

```json
{
  "@context": {
    "prov":  "http://www.w3.org/ns/prov#",
    "xsd":   "http://www.w3.org/2001/XMLSchema#",
    "rdfs":  "http://www.w3.org/2000/01/rdf-schema#",
    "usf":   "https://usf.makf.tech/ontology/",
    "fibo":  "https://spec.edmcouncil.org/fibo/ontology/",
    "dcterms": "http://purl.org/dc/terms/"
  }
}
```

---

## Template 1: Query Result Provenance

Emitted by `usf-api` after every successful query. Stored in QLever provenance graph.
Referenced by the `meta.prov_o_uri` field in every response envelope.

```json
{
  "@context": {
    "prov":    "http://www.w3.org/ns/prov#",
    "xsd":     "http://www.w3.org/2001/XMLSchema#",
    "rdfs":    "http://www.w3.org/2000/01/rdf-schema#",
    "usf":     "https://usf.makf.tech/ontology/",
    "dcterms": "http://purl.org/dc/terms/"
  },
  "@graph": [
    {
      "@id": "usf://{tenant_slug}/provenance/{date}/query/{query_hash}",
      "@type": "prov:Entity",
      "rdfs:label": "Query result: {metric_or_entity}",
      "dcterms:created": {
        "@value": "{generated_at_time}",
        "@type": "xsd:dateTime"
      },
      "prov:wasGeneratedBy": {
        "@id": "usf://{tenant_slug}/provenance/{date}/activity/query-{query_hash}"
      },
      "prov:wasAttributedTo": {
        "@id": "usf://{tenant_slug}/agent/user/{user_id}"
      },
      "usf:queryHash": "{query_hash}",
      "usf:queryType": "{query_type}",
      "usf:context": "{context_name}",
      "usf:namedGraph": "{named_graph_uri}",
      "usf:rowCount": {
        "@value": "{row_count}",
        "@type": "xsd:integer"
      },
      "usf:executionMs": {
        "@value": "{execution_ms}",
        "@type": "xsd:integer"
      },
      "usf:abacDecision": "{abac_decision}",
      "prov:wasDerivedFrom": [
        {
          "@id": "{named_graph_uri}"
        }
      ]
    },
    {
      "@id": "usf://{tenant_slug}/provenance/{date}/activity/query-{query_hash}",
      "@type": "prov:Activity",
      "rdfs:label": "Query execution: {query_type}",
      "prov:startedAtTime": {
        "@value": "{query_started_at}",
        "@type": "xsd:dateTime"
      },
      "prov:endedAtTime": {
        "@value": "{query_ended_at}",
        "@type": "xsd:dateTime"
      },
      "prov:wasAssociatedWith": {
        "@id": "usf://{tenant_slug}/agent/user/{user_id}"
      },
      "prov:used": [
        {
          "@id": "{named_graph_uri}"
        },
        {
          "@id": "usf://{tenant_slug}/schema/{sdl_version}"
        }
      ],
      "usf:compiledQuery": "{compiled_query_escaped}",
      "usf:sdlVersion": "{sdl_version}",
      "usf:ontologyVersion": "{ontology_version}"
    },
    {
      "@id": "usf://{tenant_slug}/agent/user/{user_id}",
      "@type": "prov:Agent",
      "rdfs:label": "{user_email}",
      "usf:role": "{user_role}",
      "usf:department": "{user_department}"
    },
    {
      "@id": "usf://{tenant_slug}/agent/usf-api",
      "@type": ["prov:Agent", "prov:SoftwareAgent"],
      "rdfs:label": "USF API Service",
      "usf:version": "{usf_api_version}"
    }
  ]
}
```

### Placeholder Reference — Query Provenance

| Placeholder | Source | Example |
|-------------|--------|---------|
| `{tenant_slug}` | JWT claim | `acme-bank` |
| `{date}` | UTC today | `2026-03-27` |
| `{query_hash}` | SHA-256 of normalized query | `abc12345...` |
| `{metric_or_entity}` | Query target | `total_exposure_by_counterparty` |
| `{generated_at_time}` | Response timestamp | `2026-03-27T14:22:33.000Z` |
| `{user_id}` | JWT sub | UUID |
| `{user_email}` | JWT email | `analyst@acme-bank.com` |
| `{user_role}` | JWT roles[0] | `risk_analyst` |
| `{user_department}` | JWT dept | `Risk Management` |
| `{query_type}` | Request body type | `sql \| sparql \| nl \| ograg` |
| `{context_name}` | Resolved context | `finance` |
| `{named_graph_uri}` | Resolved named graph | `usf://acme-bank/context/finance/v1` |
| `{row_count}` | Execution result | `42` |
| `{execution_ms}` | Execution timer | `187` |
| `{abac_decision}` | OPA decision | `permit \| permit_with_filter` |
| `{query_started_at}` | Pre-execution timestamp | ISO 8601 |
| `{query_ended_at}` | Post-execution timestamp | ISO 8601 |
| `{sdl_version}` | Active SDL version | `v2` |
| `{ontology_version}` | Active ontology version | `fibo-2024-Q4` |
| `{compiled_query_escaped}` | SQL or SPARQL string | JSON-escaped |
| `{usf_api_version}` | Service version | `1.0.0` |

---

## Template 2: Ingestion Batch Provenance

Emitted by `usf-ingest` on COMPLETE. Written to QLever provenance graph.
Includes the full extraction chain: source → parser → LLM → triples.

```json
{
  "@context": {
    "prov":    "http://www.w3.org/ns/prov#",
    "xsd":     "http://www.w3.org/2001/XMLSchema#",
    "rdfs":    "http://www.w3.org/2000/01/rdf-schema#",
    "usf":     "https://usf.makf.tech/ontology/",
    "dcterms": "http://purl.org/dc/terms/"
  },
  "@graph": [
    {
      "@id": "usf://{tenant_slug}/provenance/{date}/batch/{job_id}",
      "@type": "prov:Entity",
      "rdfs:label": "Ingestion batch: {source_name}",
      "dcterms:created": {
        "@value": "{completed_at}",
        "@type": "xsd:dateTime"
      },
      "prov:wasGeneratedBy": {
        "@id": "usf://{tenant_slug}/provenance/{date}/activity/ingest-{job_id}"
      },
      "prov:wasAttributedTo": {
        "@id": "usf://{tenant_slug}/agent/usf-ingest"
      },
      "usf:outputGraph": "{named_graph_uri}",
      "usf:triplesInserted": {
        "@value": "{triples_added}",
        "@type": "xsd:integer"
      },
      "usf:triplesQuarantined": {
        "@value": "{triples_quarantined}",
        "@type": "xsd:integer"
      }
    },
    {
      "@id": "usf://{tenant_slug}/provenance/{date}/activity/ingest-{job_id}",
      "@type": "prov:Activity",
      "rdfs:label": "Ingestion activity: {ingestion_type}",
      "prov:startedAtTime": {
        "@value": "{started_at}",
        "@type": "xsd:dateTime"
      },
      "prov:endedAtTime": {
        "@value": "{completed_at}",
        "@type": "xsd:dateTime"
      },
      "prov:wasAssociatedWith": {
        "@id": "usf://{tenant_slug}/agent/usf-ingest"
      },
      "prov:used": [
        {
          "@id": "usf://{tenant_slug}/provenance/{date}/source/{source_id}"
        },
        {
          "@id": "usf://{tenant_slug}/ontology/{ontology_module}/{ontology_version}"
        }
      ],
      "usf:ingestionType": "{ingestion_type}",
      "usf:parserName": "{parser_name}",
      "usf:parserVersion": "{parser_version}",
      "usf:extractionModel": "{extraction_model}",
      "usf:openlineageRunId": "{openlineage_run_id}",
      "usf:meanConfidence": {
        "@value": "{mean_confidence}",
        "@type": "xsd:decimal"
      }
    },
    {
      "@id": "usf://{tenant_slug}/provenance/{date}/source/{source_id}",
      "@type": "prov:Entity",
      "rdfs:label": "{source_name}",
      "usf:sourceType": "{source_type}",
      "usf:sourceSubtype": "{source_subtype}",
      "usf:connectionRef": "{source_connection_ref}"
    },
    {
      "@id": "usf://{tenant_slug}/agent/usf-ingest",
      "@type": ["prov:Agent", "prov:SoftwareAgent"],
      "rdfs:label": "USF Ingest Service",
      "usf:version": "{usf_ingest_version}"
    }
  ]
}
```

### Placeholder Reference — Ingestion Provenance

| Placeholder | Source | Example |
|-------------|--------|---------|
| `{job_id}` | IngestionJob.id | UUID |
| `{source_name}` | DataSource.name | `Acme Bank Warehouse` |
| `{source_id}` | DataSource.id | UUID |
| `{source_type}` | DataSource.type | `warehouse \| file \| api` |
| `{source_subtype}` | DataSource.subtype | `postgres \| pdf \| fhir` |
| `{source_connection_ref}` | Host + db (no credentials) | `db.acme.internal/warehouse` |
| `{named_graph_uri}` | IngestionJob.named_graph_uri | `usf://acme-bank/instance/...` |
| `{triples_added}` | IngestionJob.triples_added | `3407` |
| `{triples_quarantined}` | IngestionJob.triples_quarantined | `14` |
| `{ingestion_type}` | Path type | `structured \| unstructured \| semi` |
| `{parser_name}` | Library used | `docling \| dlt \| cimpy \| fhir.resources` |
| `{parser_version}` | Library version | `2.1.0` |
| `{extraction_model}` | LLM if used, else `null` | `gemini-1.5-pro \| null` |
| `{ontology_module}` | Active module | `fibo` |
| `{ontology_version}` | Active version | `2024-Q4` |
| `{openlineage_run_id}` | OpenLineage run ID | UUID |
| `{mean_confidence}` | Extraction confidence avg | `0.963` |
| `{started_at}` | Job start | ISO 8601 |
| `{completed_at}` | Job end | ISO 8601 |

---

## Template 3: SDL Publish Provenance

Emitted by `usf-sdl /publish`. Written to QLever provenance graph.

```json
{
  "@context": {
    "prov":    "http://www.w3.org/ns/prov#",
    "xsd":     "http://www.w3.org/2001/XMLSchema#",
    "rdfs":    "http://www.w3.org/2000/01/rdf-schema#",
    "usf":     "https://usf.makf.tech/ontology/",
    "dcterms": "http://purl.org/dc/terms/"
  },
  "@graph": [
    {
      "@id": "usf://{tenant_slug}/schema/{version}",
      "@type": "prov:Entity",
      "rdfs:label": "SDL Schema {version}",
      "dcterms:created": {
        "@value": "{published_at}",
        "@type": "xsd:dateTime"
      },
      "prov:wasGeneratedBy": {
        "@id": "usf://{tenant_slug}/provenance/{date}/activity/sdl-publish-{version_id}"
      },
      "prov:wasAttributedTo": {
        "@id": "usf://{tenant_slug}/agent/user/{publisher_user_id}"
      },
      "usf:sdlVersion": "{version}",
      "usf:changelog": "{changelog}",
      "usf:entityCount": {
        "@value": "{entity_count}",
        "@type": "xsd:integer"
      },
      "usf:metricCount": {
        "@value": "{metric_count}",
        "@type": "xsd:integer"
      },
      "usf:breakingChange": {
        "@value": "{is_breaking_change}",
        "@type": "xsd:boolean"
      }
    },
    {
      "@id": "usf://{tenant_slug}/provenance/{date}/activity/sdl-publish-{version_id}",
      "@type": "prov:Activity",
      "rdfs:label": "SDL publish: {version}",
      "prov:startedAtTime": {
        "@value": "{published_at}",
        "@type": "xsd:dateTime"
      },
      "prov:endedAtTime": {
        "@value": "{published_at}",
        "@type": "xsd:dateTime"
      },
      "prov:wasAssociatedWith": {
        "@id": "usf://{tenant_slug}/agent/user/{publisher_user_id}"
      },
      "prov:used": [
        {
          "@id": "usf://{tenant_slug}/schema/{previous_version}"
        }
      ],
      "prov:generated": {
        "@id": "usf://{tenant_slug}/schema/{version}"
      }
    },
    {
      "@id": "usf://{tenant_slug}/agent/user/{publisher_user_id}",
      "@type": "prov:Agent",
      "rdfs:label": "{publisher_email}",
      "usf:role": "{publisher_role}"
    }
  ]
}
```

---

## PROV-O Python Builder (Reference Implementation)

The `packages/rdf` package provides a `ProvenanceBuilder` class that renders these templates:

```python
# packages/rdf/usf_rdf/provenance.py

from datetime import datetime, timezone
from typing import Any
import json
import hashlib

PROV_CONTEXT = {
    "prov":    "http://www.w3.org/ns/prov#",
    "xsd":     "http://www.w3.org/2001/XMLSchema#",
    "rdfs":    "http://www.w3.org/2000/01/rdf-schema#",
    "usf":     "https://usf.makf.tech/ontology/",
    "dcterms": "http://purl.org/dc/terms/",
}


def build_query_provenance(
    tenant_slug: str,
    query_hash: str,
    user_id: str,
    user_email: str,
    user_role: str,
    query_type: str,
    context_name: str | None,
    named_graph_uri: str | None,
    row_count: int,
    execution_ms: int,
    abac_decision: str,
    compiled_query: str,
    sdl_version: str,
    ontology_version: str,
    started_at: datetime,
    ended_at: datetime,
) -> dict[str, Any]:
    """Build PROV-O JSON-LD block for a query result."""
    date = ended_at.strftime("%Y-%m-%d")
    base = f"usf://{tenant_slug}/provenance/{date}"

    return {
        "@context": PROV_CONTEXT,
        "@graph": [
            {
                "@id": f"{base}/query/{query_hash}",
                "@type": "prov:Entity",
                "rdfs:label": f"Query result ({query_type})",
                "dcterms:created": {"@value": ended_at.isoformat(), "@type": "xsd:dateTime"},
                "prov:wasGeneratedBy": {"@id": f"{base}/activity/query-{query_hash}"},
                "prov:wasAttributedTo": {"@id": f"usf://{tenant_slug}/agent/user/{user_id}"},
                "usf:queryHash": query_hash,
                "usf:queryType": query_type,
                "usf:context": context_name,
                "usf:namedGraph": named_graph_uri,
                "usf:rowCount": {"@value": str(row_count), "@type": "xsd:integer"},
                "usf:executionMs": {"@value": str(execution_ms), "@type": "xsd:integer"},
                "usf:abacDecision": abac_decision,
                "prov:wasDerivedFrom": [{"@id": named_graph_uri}] if named_graph_uri else [],
            },
            {
                "@id": f"{base}/activity/query-{query_hash}",
                "@type": "prov:Activity",
                "prov:startedAtTime": {"@value": started_at.isoformat(), "@type": "xsd:dateTime"},
                "prov:endedAtTime": {"@value": ended_at.isoformat(), "@type": "xsd:dateTime"},
                "prov:wasAssociatedWith": {"@id": f"usf://{tenant_slug}/agent/user/{user_id}"},
                "prov:used": [
                    {"@id": named_graph_uri},
                    {"@id": f"usf://{tenant_slug}/schema/{sdl_version}"},
                ] if named_graph_uri else [],
                "usf:compiledQuery": compiled_query,
                "usf:sdlVersion": sdl_version,
                "usf:ontologyVersion": ontology_version,
            },
            {
                "@id": f"usf://{tenant_slug}/agent/user/{user_id}",
                "@type": "prov:Agent",
                "rdfs:label": user_email,
                "usf:role": user_role,
            },
        ],
    }


def prov_graph_uri(tenant_slug: str, date: datetime | None = None) -> str:
    """Return the named graph URI for today's provenance."""
    d = (date or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    return f"usf://{tenant_slug}/provenance/{d}"
```

---

## Storage in QLever

PROV-O triples are stored as a single daily named graph in QLever:

```sparql
-- Insert provenance triples via QLever UPDATE
INSERT DATA {
  GRAPH <usf://acme-bank/provenance/2026-03-27> {
    <usf://acme-bank/provenance/2026-03-27/query/abc12345>
        a prov:Entity ;
        rdfs:label "Query result (sql)" ;
        usf:queryHash "abc12345" ;
        prov:wasGeneratedBy <usf://acme-bank/provenance/2026-03-27/activity/query-abc12345> .
    
    <usf://acme-bank/provenance/2026-03-27/activity/query-abc12345>
        a prov:Activity ;
        prov:startedAtTime "2026-03-27T14:22:33Z"^^xsd:dateTime ;
        prov:endedAtTime   "2026-03-27T14:22:33.187Z"^^xsd:dateTime .
  }
}
```

---

*End of PROV-O Templates v1.0.0*
