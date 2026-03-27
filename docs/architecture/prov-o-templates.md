# USF PROV-O JSON-LD Templates

**Version**: 1.0.0 | **Status**: FROZEN | **Date**: 2026-03-27

All templates use `{placeholder}` syntax. The PROV-O builder substitutes at runtime.
PROV-O graphs are stored in QLever under `usf://{tenant}/provenance/{date}`.

## Common Context

```json
{
  "@context": {
    "prov":    "http://www.w3.org/ns/prov#",
    "xsd":     "http://www.w3.org/2001/XMLSchema#",
    "rdfs":    "http://www.w3.org/2000/01/rdf-schema#",
    "usf":     "https://usf.makf.tech/ontology/",
    "dcterms": "http://purl.org/dc/terms/"
  }
}
```

## Template 1: Query Result Provenance

Emitted by usf-api. `meta.prov_o_uri` in every response points here.

Key nodes:
- `usf://{tenant}/provenance/{date}/query/{query_hash}` — prov:Entity (the result)
- `usf://{tenant}/provenance/{date}/activity/query-{query_hash}` — prov:Activity
- `usf://{tenant}/agent/user/{user_id}` — prov:Agent

Key predicates:
- `prov:wasGeneratedBy`, `prov:wasAttributedTo`, `prov:wasDerivedFrom`
- `usf:queryHash`, `usf:queryType`, `usf:context`, `usf:executionMs`, `usf:abacDecision`

## Template 2: Ingestion Batch Provenance

Emitted by usf-ingest on COMPLETE.

Key nodes:
- `usf://{tenant}/provenance/{date}/batch/{job_id}` — prov:Entity (the batch output)
- `usf://{tenant}/provenance/{date}/activity/ingest-{job_id}` — prov:Activity
- `usf://{tenant}/provenance/{date}/source/{source_id}` — prov:Entity (input source)

Key predicates:
- `prov:used` (source + ontology), `prov:generated` (instance named graph)
- `usf:ingestionType`, `usf:parserName`, `usf:extractionModel`, `usf:meanConfidence`

## Template 3: SDL Publish Provenance

Emitted by usf-sdl on publish.

Key nodes:
- `usf://{tenant}/schema/{version}` — prov:Entity (the new schema)
- Previous version linked via `prov:used`
- Publisher user as prov:Agent

## Python Builder Reference

```python
from usf_rdf.provenance import build_query_provenance, prov_graph_uri

# Build query provenance block
prov = build_query_provenance(
    tenant_slug="acme-bank",
    query_hash="abc12345",
    user_id="uuid",
    user_email="analyst@acme-bank.com",
    user_role="risk_analyst",
    query_type="sql",
    context_name="finance",
    named_graph_uri="usf://acme-bank/context/finance/v1",
    row_count=42,
    execution_ms=187,
    abac_decision="permit",
    compiled_query="SELECT ...",
    sdl_version="v2",
    ontology_version="fibo-2024-Q4",
    started_at=start_time,
    ended_at=end_time,
)

# Write to QLever
graph_uri = prov_graph_uri("acme-bank")  # "usf://acme-bank/provenance/2026-03-27"
```

*See packages/rdf/usf_rdf/provenance.py for full implementation.*
