# USF API Contracts — OpenAPI Specifications

**Version**: 1.0.0
**Status**: FROZEN
**Date**: 2026-03-27
**Author**: usf-architect

> These contracts are the source of truth for all inter-service communication.
> Every service must implement these interfaces exactly.
> Changes require an ADR and a version bump.

---

## Common Conventions

### Request Headers (all services)
```
X-USF-Tenant-ID: {uuid}
X-USF-Context: {context_name}
X-Request-ID: {uuid}
Authorization: Bearer {jwt}
```

### Response Envelope
```json
{
  "data": { "..." : "..." },
  "meta": {
    "request_id": "uuid",
    "tenant_id": "uuid",
    "context": "finance",
    "named_graph": "usf://tenant/context/finance/v1",
    "query_hash": "sha256hex",
    "prov_o_uri": "usf://tenant/provenance/2026-03-27/abc123",
    "cached": false,
    "execution_ms": 187
  }
}
```

### Error Envelope
```json
{
  "error": {
    "code": "CONTEXT_AMBIGUOUS",
    "message": "Human-readable description",
    "detail": {},
    "request_id": "uuid"
  }
}
```

### HTTP Status Codes
| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Validation error |
| 401 | Authentication required |
| 403 | Access denied (ABAC) |
| 404 | Not found |
| 409 | Context ambiguous — specify X-USF-Context |
| 422 | Semantic validation error |
| 429 | Rate limited |
| 500 | Internal error |
| 503 | Dependency unavailable |

---

## Service: usf-api (Port 8000)

### POST /auth/login
**Request**: `{"email": "...", "password": "..."}`
**Response 200**: `{"access_token": "eyJ...", "token_type": "bearer", "expires_in": 3600, "refresh_token": "..."}`

### POST /auth/refresh
**Request**: `{"refresh_token": "..."}` or via HttpOnly cookie
**Response 200**: Same shape as `/auth/login`

### GET /contexts
**Response 200**: `{"data": [{"name": "finance", "description": "...", "named_graph_uri": "usf://...", "metric_count": 14}]}`

### POST /query
**Request**:
```json
{"type": "sql|sparql|nl|ograg", "query": "...", "context": "finance", "options": {"explain": false, "include_provenance": true}}
```
**Response 200**: Standard envelope with `data.columns`, `data.rows`, `data.row_count`
**Response 409**: `{"error": {"code": "CONTEXT_AMBIGUOUS", "message": "...", "detail": {"metric": "balance", "contexts": [...]}}}`

### GET /metrics
**Query params**: `context`, `search`, `page`, `page_size`
**Response 200**: Paginated metric list with SDL metadata

### GET /entities/search
**Query params**: `q` (required), `entity_type`, `context`, `limit`
**Response 200**: `{"data": [{"iri": "...", "label": "Deutsche Bank AG", "ontology_class": "fibo:CommercialBank", "score": 0.94}]}`

### GET /health
**Response 200**: `{"status": "healthy", "version": "1.0.0", "dependencies": {"postgres": "healthy", "qlever": "healthy", "valkey": "healthy", "opa": "healthy"}}`

---

## Service: usf-query (Port 8001, internal)

### POST /compile
**Request**: `{"metric": "total_exposure_by_counterparty", "context": "finance", "dimensions": [...], "target_dialect": "postgres"}`
**Response 200**: `{"data": {"compiled_sql": "...", "compiled_sparql": "...", "execution_plan": "sql"}}`

### POST /execute/sql
**Request**: Same as `/compile`
**Response 200**: Standard envelope with query results

### POST /execute/sparql
**Request**: `{"sparql": "SELECT ...", "named_graph": "usf://...", "engine": "qlever|ontop", "timeout_ms": 30000}`
**Response 200**: SPARQL result bindings

### POST /execute/nl
**Request**: `{"question": "...", "context": "risk", "language_model": "gpt-4o", "max_iterations": 3}`
**Response 200**: `{"data": {"generated_sparql": "...", "validation_result": "valid", "iterations": 1, "rows": [...]}}`
**Response 422**: NL2SPARQL failed after max iterations

### POST /execute/ograg
**Request**: `{"question": "...", "entity_iris": [...], "context": "risk", "top_k_chunks": 5}`
**Response 200**: Answer with supporting_triples and supporting_chunks

### GET /explain/{metric}
**Response 200**: Metric definition, OWL class, compiled SQL, lineage

---

## Service: usf-kg (Port 8002, internal)

### POST /triples
**Request**: `{"named_graph": "usf://...", "triples": [...], "format": "json-triples", "validate": true, "quarantine_on_violation": true}`
**Response 201**: `{"data": {"inserted": 3407, "quarantined": 14, "quarantine_graph": "usf://..."}}`

### GET /graphs
**Query params**: `type` (ontology|context|instance|provenance|access|schema|quarantine)
**Response 200**: List of named graph metadata objects

### GET /graphs/{uri}
**Response 200**: Named graph metadata with triple_count, entity_count, ontology_classes

### GET /entities/{iri}
**Query params**: `depth` (default 1, max 3), `named_graph`
**Response 200**: Entity with properties, neighbors, prov_o

### POST /validate
**Request**: `{"triples": "...", "format": "turtle", "shapes_graph": "usf://..."}`
**Response 200**: `{"data": {"conforms": false, "violations": [...]}}`

### POST /ontology/load
**Request**: `{"module": "fibo", "version": "2024-Q4", "named_graph": "usf://..."}`
**Response 201**: `{"data": {"classes_loaded": 8147, "properties_loaded": 12384, "shapes_loaded": 342}}`

### GET /provenance/{iri}
**Response 200**: PROV-O JSON-LD chain for entity or query result

---

## Service: usf-sdl (Port 8003, internal)

### POST /validate
**Request**: `{"yaml_content": "entity:\n  name: BankAccount..."}`
**Response 200**: `{"data": {"valid": false, "errors": [{"path": "...", "message": "...", "severity": "error"}]}}`

### POST /compile
**Request**: `{"yaml_content": "...", "target_dialects": ["postgres", "snowflake"], "include_provenance_template": true}`
**Response 200**: `{"data": {"owl_turtle": "...", "sql": {"postgres": "..."}, "r2rml": "...", "shacl_shapes": "..."}}`

### GET /versions
**Response 200**: Paginated SDL version history

### POST /publish
**Request**: `{"yaml_content": "...", "version": "v2", "changelog": "..."}`
**Response 201**: `{"data": {"version_id": "uuid", "version": "v2", "named_graph": "usf://..."}}`

### GET /diff/{v1}/{v2}
**Response 200**: `{"data": {"added_entities": [], "removed_entities": [], "modified_entities": [...], "added_metrics": [...], "breaking_changes": false}}`

### GET /ontology/{module}
**Query params**: `search`, `parent_class`, `page`, `page_size`
**Response 200**: Ontology classes and properties for the module

---

## Service: usf-ingest (Port 8004, internal)

### POST /sources
**Request**: `{"name": "...", "type": "warehouse", "subtype": "postgres", "connection_config": {...}}`
**Response 201**: `{"data": {"id": "uuid", "name": "...", "status": "pending"}}`

### POST /jobs
**Request**: `{"source_id": "uuid", "mode": "full|incremental", "options": {"extraction_model": "gemini-1.5-pro", "ontology_version": "fibo-2024-Q4"}}`
**Response 202**: `{"data": {"job_id": "uuid", "status": "pending", "celery_task_id": "..."}}`

### GET /jobs/{id}
**Response 200**: Full job status with triples_added, triples_quarantined, extraction_model

### GET /jobs/{id}/trace
**Response 200**: Full Layer 1 trace with parser, chunks, extractions, confidence histogram, OpenLineage event

### POST /bootstrap/ontorag
**Request**: `{"source_ids": [...], "target_module": "fibo", "output_named_graph": "usf://..."}`
**Response 202**: `{"data": {"job_id": "uuid", "status": "pending"}}`

---

## Service: usf-audit (Port 8005, internal)

### GET /log
**Query params**: `start_date`, `end_date`, `user_id`, `context`, `action`, `status`, `page`, `page_size`
**Response 200**: Paginated audit log with user, action, context, abac_decision, query_hash

### GET /log/{query_hash}
**Response 200**: Full PROV-O JSON-LD for the query execution

### GET /lineage/{iri}
**Response 200**: Entity lineage chain from source → extraction → KG → query

### POST /export
**Request**: `{"start_date": "...", "end_date": "...", "format": "turtle|jsonld", "include_prov_o": true}`
**Response 202**: Export job created

### GET /stats
**Response 200**: Query counts, permit/deny rates, top metrics, top users

---

## Service: usf-mcp (Port 8006, SSE transport)

MCP tools implemented via `fastmcp`. All tools call usf-api internally.

### Tool: list_metrics
**Params**: `context?: string`
**Returns**: List of metrics with name, description, ontology_class, contexts, dimensions

### Tool: query_metric
**Params**: `metric: string`, `dimensions?: string[]`, `filters?: object`, `time_range?: object`, `context?: string`
**Returns**: Query result rows + provenance URI

### Tool: explain_metric
**Params**: `metric: string`, `context?: string`
**Returns**: Full metric definition, OWL class, compiled SQL, lineage

### Tool: list_contexts
**Params**: none
**Returns**: Available contexts for the authenticated tenant

### Tool: search_entities
**Params**: `query: string`, `entity_type?: string`, `context?: string`, `limit?: integer`
**Returns**: Entity list with IRI, label, ontology_class, relevance score

---

*End of API Contracts v1.0.0*
