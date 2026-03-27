# USF API Contracts — OpenAPI Specifications

**Version**: 1.0.0 | **Status**: FROZEN | **Date**: 2026-03-27 | **Author**: usf-architect

> Source of truth for all inter-service communication. Every service must implement these interfaces exactly.

## Quick Reference

| Service | Port | Key Endpoints |
|---------|------|--------------|
| usf-api | 8000 | /auth/login, /auth/refresh, /contexts, /query, /metrics, /entities/search, /health |
| usf-query | 8001 | /compile, /execute/sql, /execute/sparql, /execute/nl, /execute/ograg, /explain/{metric} |
| usf-kg | 8002 | /triples, /graphs, /graphs/{uri}, /entities/{iri}, /validate, /ontology/load, /provenance/{iri} |
| usf-sdl | 8003 | /validate, /compile, /versions, /publish, /diff/{v1}/{v2}, /ontology/{module} |
| usf-ingest | 8004 | /sources, /jobs, /jobs/{id}, /jobs/{id}/trace, /bootstrap/ontorag |
| usf-audit | 8005 | /log, /log/{query_hash}, /lineage/{iri}, /export, /stats |
| usf-mcp | 8006 | MCP tools: list_metrics, query_metric, explain_metric, list_contexts, search_entities |

## Common Conventions

### Request Headers
```
X-USF-Tenant-ID: {uuid}
X-USF-Context: {context_name}
X-Request-ID: {uuid}
Authorization: Bearer {jwt}
```

### Response Envelope
```json
{
  "data": {},
  "meta": {
    "request_id": "uuid", "tenant_id": "uuid", "context": "finance",
    "named_graph": "usf://tenant/context/finance/v1", "query_hash": "sha256hex",
    "prov_o_uri": "usf://tenant/provenance/2026-03-27/abc123",
    "cached": false, "execution_ms": 187
  }
}
```

### Error Envelope
```json
{"error": {"code": "CONTEXT_AMBIGUOUS", "message": "...", "detail": {}, "request_id": "uuid"}}
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
| 503 | Dependency unavailable |

---

## usf-api (Port 8000)

### POST /auth/login
Request: `{"email": "...", "password": "..."}`
Response: `{"access_token": "eyJ...", "token_type": "bearer", "expires_in": 3600, "refresh_token": "..."}`

### POST /auth/refresh
Request: `{"refresh_token": "..."}` or HttpOnly cookie
Response: Same shape as /auth/login

### GET /contexts
Response: `{"data": [{"name": "finance", "description": "...", "named_graph_uri": "usf://...", "metric_count": 14}]}`

### POST /query
Request: `{"type": "sql|sparql|nl|ograg", "query": "...", "context": "finance", "options": {"explain": false, "include_provenance": true}}`
Response: Standard envelope with data.columns, data.rows, data.row_count, meta.prov_o_uri

**HTTP 409** (context ambiguous):
```json
{"error": {"code": "CONTEXT_AMBIGUOUS", "message": "Metric 'balance' defined in 2 contexts: risk (EOD ledger) and ops (current). Specify X-USF-Context.", "detail": {"metric": "balance", "contexts": [{"name": "risk", "definition": "..."}, {"name": "ops", "definition": "..."}]}}}
```

### GET /metrics
Query params: `context`, `search`, `page`, `page_size`
Response: Paginated metric list with SDL metadata, ontology_class, dimensions, time_grains

### GET /entities/search
Query params: `q` (required), `entity_type`, `context`, `limit`
Response: `{"data": [{"iri": "...", "label": "Deutsche Bank AG", "ontology_class": "fibo:CommercialBank", "score": 0.94}]}`

### GET /health
Response: `{"status": "healthy", "version": "1.0.0", "dependencies": {"postgres": "healthy", "qlever": "healthy", "valkey": "healthy", "opa": "healthy"}}`

---

## usf-query (Port 8001, internal)

### POST /compile
Request: `{"metric": "total_exposure_by_counterparty", "context": "finance", "dimensions": [...], "target_dialect": "postgres"}`
Response: `{"data": {"compiled_sql": "...", "compiled_sparql": "...", "execution_plan": "sql"}}`

### POST /execute/sql
Request: Same as /compile. Response: Standard envelope with query results.

### POST /execute/sparql
Request: `{"sparql": "SELECT ...", "named_graph": "usf://...", "engine": "qlever|ontop", "timeout_ms": 30000}`

### POST /execute/nl
Request: `{"question": "...", "context": "risk", "language_model": "gpt-4o", "max_iterations": 3}`
Response: `{"data": {"generated_sparql": "...", "validation_result": "valid", "iterations": 1, "rows": [...]}}`
HTTP 422: NL2SPARQL failed — includes last_sparql_attempt and validation_errors

### POST /execute/ograg
Request: `{"question": "...", "entity_iris": [...], "context": "risk", "top_k_chunks": 5}`
Response: answer + supporting_triples + supporting_chunks with char_interval and confidence

### GET /explain/{metric}
Response: metric definition, OWL class, compiled SQL, source_tables, sdl_version lineage

---

## usf-kg (Port 8002, internal)

### POST /triples
Request: `{"named_graph": "usf://...", "triples": [...], "format": "json-triples|turtle|n-triples", "validate": true, "quarantine_on_violation": true}`
Response 201: `{"data": {"inserted": 3407, "quarantined": 14, "quarantine_graph": "usf://..."}}`

### GET /graphs
Query params: `type` (ontology|context|instance|provenance|access|schema|quarantine)
Response: Named graph list with triple_count, created_at, sdl_version

### GET /graphs/{uri}
Response: Graph metadata with triple_count, entity_count, ontology_classes

### GET /entities/{iri}
Query params: `depth` (default 1, max 3), `named_graph`
Response: Entity with properties, neighbors, prov_o block

### POST /validate
Request: `{"triples": "...", "format": "turtle", "shapes_graph": "usf://..."}`
Response: `{"data": {"conforms": false, "violations": [{"focus_node": "...", "shape": "...", "message": "...", "severity": "Violation"}]}}`

### POST /ontology/load
Request: `{"module": "fibo", "version": "2024-Q4", "named_graph": "usf://..."}`
Response 201: `{"data": {"classes_loaded": 8147, "properties_loaded": 12384, "shapes_loaded": 342}}`

### GET /provenance/{iri}
Response: PROV-O JSON-LD chain

---

## usf-sdl (Port 8003, internal)

### POST /validate
Request: `{"yaml_content": "entity:\n  name: BankAccount..."}`
Response: `{"data": {"valid": false, "errors": [{"path": "...", "message": "...", "severity": "error"}]}}`

### POST /compile
Request: `{"yaml_content": "...", "target_dialects": ["postgres", "snowflake"], "include_provenance_template": true}`
Response: `{"data": {"owl_turtle": "...", "sql": {"postgres": "..."}, "r2rml": "...", "shacl_shapes": "..."}}`

### GET /versions
Response: Paginated SDL version history with changelog

### POST /publish
Request: `{"yaml_content": "...", "version": "v2", "changelog": "..."}`
Response 201: `{"data": {"version_id": "uuid", "version": "v2", "named_graph": "usf://..."}}`

### GET /diff/{v1}/{v2}
Response: `{"data": {"added_entities": [], "removed_entities": [], "modified_entities": [...], "added_metrics": [...], "breaking_changes": false}}`

### GET /ontology/{module}
Query params: `search`, `parent_class`, `page`, `page_size`
Response: Classes list with iri, curie, label, parent, description

---

## usf-ingest (Port 8004, internal)

### POST /sources
Request: `{"name": "...", "type": "warehouse", "subtype": "postgres", "connection_config": {"host": "...", "password_secret_ref": "vault://..."}}`
Response 201: `{"data": {"id": "uuid", "status": "pending"}}`

### POST /jobs
Request: `{"source_id": "uuid", "mode": "full|incremental", "options": {"extraction_model": "gemini-1.5-pro", "validate_shacl": true}}`
Response 202: `{"data": {"job_id": "uuid", "status": "pending", "celery_task_id": "..."}}`

### GET /jobs/{id}
Response: Full job with triples_added, triples_quarantined, openlineage_run_id, named_graph_uri

### GET /jobs/{id}/trace
Response: Layer 1 debug trace — parser, chunks, extractions, confidence_histogram, entity_type_breakdown, openlineage_event

### POST /bootstrap/ontorag
Request: `{"source_ids": [...], "target_module": "fibo", "output_named_graph": "usf://..."}`
Response 202: job created

---

## usf-audit (Port 8005, internal)

### GET /log
Query params: `start_date`, `end_date`, `user_id`, `context`, `action`, `status`, `page`, `page_size`
Response: Paginated audit records with user, action, context, abac_decision, query_hash

### GET /log/{query_hash}
Response: Full PROV-O JSON-LD for the query

### GET /lineage/{iri}
Response: Entity lineage chain: source → extraction → triple_insert → query access

### POST /export
Request: `{"start_date": "...", "end_date": "...", "format": "turtle|jsonld"}`
Response 202: Export job started. GET /export/{id}/download when complete.

### GET /stats
Response: Query counts, permit/deny rates, top metrics, top users for dashboard

---

## usf-mcp (Port 8006, SSE)

Implemented with `fastmcp`. All tools call usf-api internally.

### Tool: list_metrics
Params: `context?: string`
Returns: Metrics with name, description, ontology_class, contexts, dimensions

### Tool: query_metric
Params: `metric: string`, `dimensions?: string[]`, `filters?: object`, `time_range?: {start, end, grain}`, `context?: string`
Returns: Result rows + provenance URI

### Tool: explain_metric
Params: `metric: string`, `context?: string`
Returns: Full SDL definition, OWL class, compiled SQL, lineage

### Tool: list_contexts
Params: none
Returns: Available contexts for authenticated tenant

### Tool: search_entities
Params: `query: string`, `entity_type?: string`, `context?: string`, `limit?: integer (max 50)`
Returns: Entities with iri, label, ontology_class, score

---

*End of API Contracts v1.0.0*
