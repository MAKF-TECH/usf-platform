# USF API Contracts — OpenAPI Specifications

**Version**: 1.0.0  
**Status**: FROZEN — all services must implement these interfaces exactly  
**Date**: 2026-03-27  
**Author**: usf-architect

> These contracts are the source of truth for all inter-service communication.
> Every service must validate incoming requests and outgoing responses against these specs.
> Changes require an ADR and a version bump.

---

## Common Conventions

### Request Headers (all services)
```
X-USF-Tenant-ID: {uuid}          # required on all protected endpoints
X-USF-Context: {context_name}    # optional; triggers context resolution
X-Request-ID: {uuid}             # optional; propagated for tracing
Authorization: Bearer {jwt}      # required on all protected endpoints
```

### Response Envelope (all 200/201 responses)
```json
{
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "tenant_id": "uuid",
    "context": "finance | null",
    "named_graph": "usf://tenant/context/finance/v1 | null",
    "query_hash": "sha256hex",
    "prov_o_uri": "usf://tenant/provenance/2026-03-27/abc123 | null",
    "cached": false,
    "execution_ms": 187
  }
}
```

### Error Envelope
```json
{
  "error": {
    "code": "CONTEXT_AMBIGUOUS | ACCESS_DENIED | VALIDATION_ERROR | NOT_FOUND | INTERNAL",
    "message": "Human-readable description",
    "detail": { ... },
    "request_id": "uuid"
  }
}
```

### HTTP Status Codes
| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Validation error (malformed input) |
| 401 | Authentication required |
| 403 | Access denied (ABAC policy) |
| 404 | Resource not found |
| 409 | Context ambiguous — caller must specify `X-USF-Context` |
| 422 | Semantic validation error (ontology mismatch) |
| 429 | Rate limited |
| 500 | Internal error |
| 503 | Dependency unavailable (QLever, ArcadeDB etc.) |

---

## Service: usf-api (Port 8000)

The single HTTP entry point for all external clients (UI, SDK, MCP).

### POST /auth/login
**Description**: Authenticate with email + password, receive JWT pair.

**Request**
```json
{
  "email": "analyst@acme-bank.com",
  "password": "string"
}
```

**Response 200**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "opaque-refresh-token"
}
```
Note: `refresh_token` is also set as an `HttpOnly; Secure; SameSite=Strict` cookie.

**Response 401**
```json
{"error": {"code": "AUTH_FAILED", "message": "Invalid credentials"}}
```

---

### POST /auth/refresh
**Description**: Obtain a new access token using refresh token (cookie or body).

**Request** (body optional if cookie present)
```json
{"refresh_token": "opaque-refresh-token"}
```

**Response 200**: Same shape as `/auth/login` (new access_token, same refresh_token).

---

### GET /contexts
**Description**: List all available contexts for the authenticated tenant.

**Response 200**
```json
{
  "data": [
    {
      "name": "finance",
      "description": "Finance reporting context",
      "named_graph_uri": "usf://acme-bank/context/finance/v1",
      "parent_context": null,
      "metric_count": 14,
      "entity_count": 3421
    },
    {
      "name": "risk",
      "description": "Credit risk context",
      "named_graph_uri": "usf://acme-bank/context/risk/v1",
      "parent_context": null,
      "metric_count": 8,
      "entity_count": 3421
    }
  ]
}
```

---

### POST /query
**Description**: Main query endpoint. Routes to usf-query based on type.

**Request**
```json
{
  "type": "sql | sparql | nl | ograg",
  "query": "SELECT ...",
  "context": "finance",
  "parameters": {},
  "options": {
    "explain": false,
    "include_provenance": true,
    "format": "json | csv | turtle"
  }
}
```

**Response 200**
```json
{
  "data": {
    "columns": ["counterparty", "total_exposure"],
    "rows": [["Deutsche Bank AG", 45200000.00]],
    "row_count": 1,
    "format": "json"
  },
  "meta": {
    "request_id": "uuid",
    "context": "finance",
    "named_graph": "usf://acme-bank/context/finance/v1",
    "query_hash": "sha256hex",
    "prov_o_uri": "usf://acme-bank/provenance/2026-03-27/abc123",
    "cached": false,
    "execution_ms": 187,
    "compiled_query": "SELECT ... (if explain=true)",
    "abac_decision": "permit | permit_with_filter",
    "abac_filter_applied": "status = 'settled'"
  }
}
```

**Response 409** (context ambiguous)
```json
{
  "error": {
    "code": "CONTEXT_AMBIGUOUS",
    "message": "Metric 'balance' is defined in 2 contexts: 'risk' (EOD ledger) and 'ops' (current balance). Specify X-USF-Context header.",
    "detail": {
      "metric": "balance",
      "contexts": [
        {"name": "risk", "definition": "End-of-day ledger balance"},
        {"name": "ops", "definition": "Current operational balance"}
      ]
    }
  }
}
```

---

### GET /metrics
**Description**: List all SDL metrics accessible to the authenticated user (ABAC filtered).

**Query params**: `context` (optional), `search` (optional string), `page` (int, default 1), `page_size` (int, default 50)

**Response 200**
```json
{
  "data": [
    {
      "name": "total_exposure_by_counterparty",
      "description": "Total monetary exposure aggregated by counterparty legal entity",
      "type": "sum",
      "ontology_class": "fibo:FinancialExposure",
      "contexts": ["risk", "finance"],
      "dimensions": ["counterparty_name", "counterparty_country", "transaction_type"],
      "time_grains": ["day", "month", "quarter"],
      "access_policy": {"read": ["role:risk_analyst", "role:finance_analyst"]}
    }
  ],
  "total": 14,
  "page": 1,
  "page_size": 50
}
```

---

### GET /entities/search
**Description**: Full-text + semantic search over the knowledge graph.

**Query params**: `q` (required string), `entity_type` (optional ontology class IRI), `context` (optional), `limit` (int, default 20)

**Response 200**
```json
{
  "data": [
    {
      "iri": "usf://acme-bank/instance/warehouse/batch-001#entity-4521",
      "label": "Deutsche Bank AG",
      "ontology_class": "fibo:CommercialBank",
      "score": 0.94,
      "snippet": "...largest commercial bank in Germany...",
      "named_graph": "usf://acme-bank/instance/warehouse/batch-001"
    }
  ]
}
```

---

### GET /health
**Description**: Liveness + readiness probe.

**Response 200**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "postgres": "healthy",
    "qlever": "healthy",
    "valkey": "healthy",
    "opa": "healthy"
  }
}
```

**Response 503** (degraded)
```json
{
  "status": "degraded",
  "dependencies": {
    "postgres": "healthy",
    "qlever": "unhealthy",
    "valkey": "healthy",
    "opa": "healthy"
  }
}
```

---

## Service: usf-query (Port 8001, internal only)

Query execution engine. Never exposed to external clients directly.

### POST /compile
**Description**: Compile an SDL metric name or raw query to executable form.

**Request**
```json
{
  "metric": "total_exposure_by_counterparty",
  "context": "finance",
  "dimensions": ["counterparty_name"],
  "filters": {"time_range": {"start": "2024-01-01", "end": "2024-03-31"}},
  "target_dialect": "postgres | snowflake | bigquery | sparql"
}
```

**Response 200**
```json
{
  "data": {
    "compiled_sql": "SELECT counterparty_name, SUM(amount) AS total_exposure FROM ...",
    "compiled_sparql": "SELECT ?name ?exposure WHERE { ... }",
    "execution_plan": "sql",
    "target_dialect": "postgres"
  }
}
```

---

### POST /execute/sql
**Description**: Compile SDL metric + execute SQL via Wren Engine / DataFusion.

**Request**: Same as `/compile` (includes metric, context, dimensions, filters).

**Response 200**: Full response envelope with `data.columns`, `data.rows`.

---

### POST /execute/sparql
**Description**: Execute SPARQL query against QLever or Ontop.

**Request**
```json
{
  "sparql": "SELECT ?s ?p ?o WHERE { ... }",
  "named_graph": "usf://acme-bank/context/finance/v1",
  "engine": "qlever | ontop",
  "timeout_ms": 30000
}
```

**Response 200**: Standard envelope with SPARQL result bindings.

---

### POST /execute/nl
**Description**: Natural language → SPARQL → execute pipeline.

**Request**
```json
{
  "question": "What is total credit exposure in the EU?",
  "context": "risk",
  "language_model": "gpt-4o | gemini-1.5-pro",
  "max_iterations": 3
}
```

**Response 200**
```json
{
  "data": {
    "generated_sparql": "SELECT ... WHERE { ... }",
    "validation_result": "valid",
    "iterations": 1,
    "rows": [...],
    "columns": [...]
  },
  "meta": { "..." : "..." }
}
```

**Response 422** (SPARQL ontology validation failed after max iterations)
```json
{
  "error": {
    "code": "NL2SPARQL_FAILED",
    "message": "Could not generate valid SPARQL after 3 iterations",
    "detail": {
      "last_sparql_attempt": "SELECT ...",
      "validation_errors": ["Unknown class: fibo:BankAccount (did you mean fibo:Account?)"]
    }
  }
}
```

---

### POST /execute/ograg
**Description**: OG-RAG hybrid retrieval for AI agents (structured KG + unstructured text).

**Request**
```json
{
  "question": "What regulatory text supports this AML finding?",
  "entity_iris": ["usf://acme-bank/instance/..."],
  "context": "risk",
  "top_k_chunks": 5
}
```

**Response 200**
```json
{
  "data": {
    "answer": "...",
    "supporting_triples": [{"s": "...", "p": "...", "o": "..."}],
    "supporting_chunks": [
      {
        "text": "...",
        "source_iri": "usf://acme-bank/instance/docs/basel-iii-annex-4",
        "char_interval": [1240, 1890],
        "confidence": 0.87
      }
    ]
  }
}
```

---

### GET /explain/{metric}
**Description**: Full metric definition, ontology lineage, and compilation trace.

**Path params**: `metric` — SDL metric name

**Query params**: `context` (optional)

**Response 200**
```json
{
  "data": {
    "metric": "total_exposure_by_counterparty",
    "ontology_class": "fibo:FinancialExposure",
    "owl_definition": "<owl:Class rdf:about=\"fibo:FinancialExposure\"> ...",
    "compiled_sql": "SELECT ...",
    "lineage": {
      "source_tables": ["transactions", "accounts"],
      "source_named_graphs": ["usf://acme-bank/instance/warehouse/batch-001"],
      "sdl_version": "v2"
    }
  }
}
```

---

## Service: usf-kg (Port 8002, internal only)

Knowledge graph state management. Named graph CRUD. Validation.

### POST /triples
**Description**: Bulk insert RDF triples into a named graph.

**Request**
```json
{
  "named_graph": "usf://acme-bank/instance/warehouse/batch-001",
  "triples": [
    {
      "subject": "usf://acme-bank/entity/bank-4521",
      "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
      "object": "https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/FinancialServicesEntities/CommercialBank"
    }
  ],
  "format": "json-triples | turtle | n-triples",
  "validate": true,
  "quarantine_on_violation": true
}
```

**Response 201**
```json
{
  "data": {
    "inserted": 3407,
    "quarantined": 14,
    "quarantine_graph": "usf://acme-bank/quarantine/2026-03-27",
    "validation_report_uri": "usf://acme-bank/provenance/2026-03-27/shacl-report-abc"
  }
}
```

---

### GET /graphs
**Description**: List all named graphs for the tenant.

**Query params**: `type` (optional: ontology|context|instance|provenance|access|schema|quarantine)

**Response 200**
```json
{
  "data": [
    {
      "uri": "usf://acme-bank/context/finance/v1",
      "type": "context",
      "triple_count": 12847,
      "created_at": "2026-03-27T10:00:00Z",
      "sdl_version": "v1"
    }
  ]
}
```

---

### GET /graphs/{uri}
**Description**: Named graph metadata and statistics.

**Path params**: `uri` — URL-encoded named graph URI

**Response 200**
```json
{
  "data": {
    "uri": "usf://acme-bank/context/finance/v1",
    "type": "context",
    "triple_count": 12847,
    "entity_count": 3421,
    "ontology_classes": ["fibo:CommercialBank", "fibo:Account", "fibo:FinancialTransaction"],
    "created_at": "2026-03-27T10:00:00Z",
    "last_modified": "2026-03-27T12:00:00Z"
  }
}
```

---

### GET /entities/{iri}
**Description**: Single entity detail with neighbors.

**Path params**: `iri` — URL-encoded entity IRI

**Query params**: `depth` (int, default 1, max 3), `named_graph` (optional filter)

**Response 200**
```json
{
  "data": {
    "iri": "usf://acme-bank/entity/bank-4521",
    "label": "Deutsche Bank AG",
    "ontology_class": "fibo:CommercialBank",
    "properties": [
      {"predicate": "fibo:hasIdentifier", "object": "DE-BANKID-001", "graph": "usf://acme-bank/instance/warehouse/batch-001"}
    ],
    "neighbors": [
      {"iri": "usf://acme-bank/entity/account-99", "predicate": "fibo:hasAccount", "direction": "out"}
    ],
    "prov_o": {
      "was_derived_from": "usf://acme-bank/instance/docs/kyc-001",
      "generated_at_time": "2026-03-27T10:00:00Z",
      "was_attributed_to": "usf://acme-bank/agent/usf-ingest"
    }
  }
}
```

---

### POST /validate
**Description**: Run pySHACL validation on a set of triples against the tenant's loaded shapes.

**Request**
```json
{
  "triples": "...",
  "format": "turtle | json-ld",
  "shapes_graph": "usf://acme-bank/ontology/fibo/2024-Q4"
}
```

**Response 200**
```json
{
  "data": {
    "conforms": false,
    "violations": [
      {
        "focus_node": "usf://acme-bank/entity/bank-999",
        "result_path": "fibo:hasIdentifier",
        "message": "Value does not match datatype xsd:string",
        "severity": "Violation | Warning | Info",
        "shape": "fibo:BankIdentifierShape"
      }
    ]
  }
}
```

---

### POST /ontology/load
**Description**: Load an industry ontology module (OWL + SHACL shapes) into the tenant's KG.

**Request**
```json
{
  "module": "fibo | fhir | iec-cim | rami40",
  "version": "2024-Q4",
  "named_graph": "usf://acme-bank/ontology/fibo/2024-Q4"
}
```

**Response 201**
```json
{
  "data": {
    "classes_loaded": 8147,
    "properties_loaded": 12384,
    "shapes_loaded": 342,
    "named_graph": "usf://acme-bank/ontology/fibo/2024-Q4"
  }
}
```

---

### GET /provenance/{iri}
**Description**: PROV-O chain for an entity or query result.

**Path params**: `iri` — URL-encoded entity or query result IRI

**Response 200**
```json
{
  "data": {
    "prov_o_graph": "usf://acme-bank/provenance/2026-03-27",
    "jsonld": {
      "@context": {"prov": "http://www.w3.org/ns/prov#"},
      "@graph": [...]
    }
  }
}
```

---

## Service: usf-sdl (Port 8003, internal only)

SDL lifecycle management. Authoring API. Compiler.

### POST /validate
**Description**: Validate SDL YAML against the Pydantic schema.

**Request** (multipart/form-data OR application/json)
```json
{
  "yaml_content": "entity:\n  name: BankAccount\n  ..."
}
```

**Response 200**
```json
{
  "data": {
    "valid": false,
    "errors": [
      {
        "path": "entity.properties[0].ontology_property",
        "message": "Unknown ontology property: fibo:hasBalanceX (did you mean fibo:hasBalance?)",
        "severity": "error"
      }
    ]
  }
}
```

---

### POST /compile
**Description**: Compile SDL YAML → OWL Turtle + SQL (per dialect) + R2RML + PROV-O template.

**Request**
```json
{
  "yaml_content": "entity:\n  ...",
  "target_dialects": ["postgres", "snowflake"],
  "include_provenance_template": true
}
```

**Response 200**
```json
{
  "data": {
    "owl_turtle": "@prefix fibo: <...> . fibo:BankAccount a owl:Class ...",
    "sql": {
      "postgres": "CREATE VIEW usf_bank_account AS SELECT ...",
      "snowflake": "CREATE VIEW usf_bank_account AS SELECT ..."
    },
    "r2rml": "@prefix rr: <http://www.w3.org/ns/r2rml#> . ...",
    "prov_o_template": {"@context": {...}, "@graph": [...]},
    "shacl_shapes": "@prefix sh: <http://www.w3.org/ns/shacl#> . ..."
  }
}
```

---

### GET /versions
**Description**: List SDL version history for the tenant.

**Query params**: `page`, `page_size`

**Response 200**
```json
{
  "data": [
    {
      "id": "uuid",
      "version": "v2",
      "is_active": true,
      "published_at": "2026-03-27T12:00:00Z",
      "published_by": "user@acme-bank.com",
      "entity_count": 3,
      "metric_count": 5
    }
  ]
}
```

---

### POST /publish
**Description**: Publish a new SDL version → writes schema named graph to usf-kg.

**Request**
```json
{
  "yaml_content": "...",
  "version": "v2",
  "changelog": "Added total_exposure_by_counterparty metric"
}
```

**Response 201**
```json
{
  "data": {
    "version_id": "uuid",
    "version": "v2",
    "named_graph": "usf://acme-bank/schema/v2",
    "published_at": "2026-03-27T12:00:00Z"
  }
}
```

---

### GET /diff/{v1}/{v2}
**Description**: Semantic diff between two SDL versions.

**Path params**: `v1`, `v2` — SDL version strings (e.g., "v1", "v2")

**Response 200**
```json
{
  "data": {
    "added_entities": [],
    "removed_entities": [],
    "modified_entities": [
      {
        "name": "BankAccount",
        "changes": [
          {"type": "property_added", "property": "risk_weight", "ontology_property": "fibo:hasRiskWeight"}
        ]
      }
    ],
    "added_metrics": ["total_exposure_by_counterparty"],
    "removed_metrics": [],
    "breaking_changes": false
  }
}
```

---

### GET /ontology/{module}
**Description**: Browse industry ontology module classes and properties.

**Path params**: `module` — e.g., "fibo", "fhir", "iec-cim"

**Query params**: `search` (optional), `parent_class` (optional IRI), `page`, `page_size`

**Response 200**
```json
{
  "data": {
    "module": "fibo",
    "version": "2024-Q4",
    "classes": [
      {
        "iri": "https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/FinancialServicesEntities/CommercialBank",
        "curie": "fibo:CommercialBank",
        "label": "Commercial Bank",
        "parent": "fibo:LegalEntity",
        "description": "A bank that serves businesses and individuals..."
      }
    ]
  }
}
```

---

## Service: usf-ingest (Port 8004, internal only)

Data acquisition and extraction. Structured, unstructured, semi-structured paths.

### POST /sources
**Description**: Register a new data source.

**Request**
```json
{
  "name": "Acme Bank Warehouse",
  "type": "warehouse",
  "subtype": "postgres",
  "connection_config": {
    "host": "db.acme.internal",
    "port": 5432,
    "database": "warehouse",
    "username": "usf_reader",
    "password_secret_ref": "vault://acme-bank/pg-password"
  }
}
```

**Response 201**
```json
{
  "data": {
    "id": "uuid",
    "name": "Acme Bank Warehouse",
    "status": "pending",
    "schema_preview": null
  }
}
```

---

### POST /jobs
**Description**: Trigger an ingestion job (async). Returns job_id immediately.

**Request**
```json
{
  "source_id": "uuid",
  "mode": "full | incremental",
  "options": {
    "extraction_model": "gemini-1.5-pro",
    "ontology_version": "fibo-2024-Q4",
    "validate_shacl": true,
    "quarantine_on_violation": true
  }
}
```

**Response 202**
```json
{
  "data": {
    "job_id": "uuid",
    "status": "pending",
    "celery_task_id": "celery-uuid"
  }
}
```

---

### GET /jobs/{id}
**Description**: Job status and statistics.

**Response 200**
```json
{
  "data": {
    "id": "uuid",
    "source_id": "uuid",
    "status": "running | complete | failed",
    "triples_added": 3407,
    "triples_quarantined": 14,
    "extraction_model": "gemini-1.5-pro",
    "ontology_version": "fibo-2024-Q4",
    "openlineage_run_id": "ol-uuid",
    "started_at": "2026-03-27T10:00:00Z",
    "completed_at": null,
    "error": null
  }
}
```

---

### GET /jobs/{id}/trace
**Description**: Full Layer 1 trace for the ingestion job (used by the UI Layer Debug Panel).

**Response 200**
```json
{
  "data": {
    "job_id": "uuid",
    "parser": "docling-v2.1 | dlt-postgres | cimpy",
    "chunks": 847,
    "avg_chunk_chars": 312,
    "extractions": 3421,
    "grounded": 3407,
    "ungrounded": 14,
    "entity_type_breakdown": [
      {"ontology_class": "fibo:CommercialBank", "count": 1204, "pct": 35.2}
    ],
    "confidence_histogram": [
      {"bucket": "0.9-1.0", "count": 2800},
      {"bucket": "0.7-0.9", "count": 607},
      {"bucket": "0.0-0.7", "count": 14}
    ],
    "openlineage_event": {"eventType": "COMPLETE", "run": {...}, "job": {...}}
  }
}
```

---

### POST /bootstrap/ontorag
**Description**: Trigger OntoRAG ontology derivation from a document corpus.

**Request**
```json
{
  "source_ids": ["uuid"],
  "target_module": "fibo",
  "output_named_graph": "usf://acme-bank/ontology/derived/v1"
}
```

**Response 202**: `{"data": {"job_id": "uuid", "status": "pending"}}`

---

## Service: usf-audit (Port 8005, internal only)

Compliance, lineage, and provenance.

### GET /log
**Description**: Paginated audit log with filters.

**Query params**: `start_date`, `end_date`, `user_id`, `context`, `action`, `status`, `page`, `page_size`

**Response 200**
```json
{
  "data": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "user_email": "analyst@acme-bank.com",
      "action": "query",
      "context": "finance",
      "metric_or_entity": "total_exposure_by_counterparty",
      "abac_decision": "permit",
      "query_hash": "sha256hex",
      "created_at": "2026-03-27T14:22:00Z"
    }
  ],
  "total": 4821,
  "page": 1,
  "page_size": 50
}
```

---

### GET /log/{query_hash}
**Description**: Full PROV-O JSON-LD for a specific query execution.

**Response 200**
```json
{
  "data": {
    "query_hash": "sha256hex",
    "prov_o_graph_uri": "usf://acme-bank/provenance/2026-03-27",
    "prov_o_jsonld": {
      "@context": {"prov": "http://www.w3.org/ns/prov#"},
      "@graph": [...]
    }
  }
}
```

---

### GET /lineage/{iri}
**Description**: Full entity lineage chain from source to KG.

**Path params**: `iri` — URL-encoded entity IRI

**Response 200**
```json
{
  "data": {
    "entity_iri": "usf://acme-bank/entity/bank-4521",
    "lineage_chain": [
      {"step": 1, "type": "source", "description": "CSV file: kaggle-aml.csv row 4521"},
      {"step": 2, "type": "extraction", "description": "LangExtract FIBO few-shot, confidence 0.97"},
      {"step": 3, "type": "validation", "description": "pySHACL passed: fibo:BankIdentifierShape"},
      {"step": 4, "type": "triple_insert", "description": "Inserted to usf://acme-bank/instance/warehouse/batch-001"},
      {"step": 5, "type": "query", "description": "Accessed in query abc123 by user analyst@acme-bank.com"}
    ]
  }
}
```

---

### POST /export
**Description**: Export audit period as RDF/Turtle or JSON-LD for regulatory submission.

**Request**
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-03-31",
  "format": "turtle | jsonld",
  "include_prov_o": true
}
```

**Response 202**: `{"data": {"export_job_id": "uuid", "status": "pending"}}`

Result available via `GET /export/{export_job_id}/download` when status = complete.

---

### GET /stats
**Description**: Audit statistics for the dashboard.

**Response 200**
```json
{
  "data": {
    "total_queries": 4821,
    "queries_today": 142,
    "permit_rate": 0.987,
    "deny_rate": 0.013,
    "top_metrics": [
      {"metric": "total_exposure_by_counterparty", "count": 842}
    ],
    "top_users": [
      {"user": "analyst@acme-bank.com", "count": 320}
    ]
  }
}
```

---

## Service: usf-mcp (Port 8006, SSE transport)

LLM-facing MCP server. Implements the Model Context Protocol.
Implementation: `fastmcp` Python library wrapping usf-api endpoints.

### MCP Tool: list_metrics

**Description**: List all metrics available in the knowledge graph, optionally filtered by context.

**Parameters**
```json
{
  "context": {
    "type": "string",
    "description": "Optional context name to filter metrics (e.g., 'risk', 'finance')",
    "required": false
  }
}
```

**Returns**
```json
[
  {
    "name": "total_exposure_by_counterparty",
    "description": "Total monetary exposure aggregated by counterparty legal entity",
    "ontology_class": "fibo:FinancialExposure",
    "contexts": ["risk", "finance"],
    "dimensions": ["counterparty_name", "counterparty_country"],
    "time_grains": ["day", "month", "quarter"]
  }
]
```

---

### MCP Tool: query_metric

**Description**: Query a specific metric with dimensions, filters, and time range.

**Parameters**
```json
{
  "metric": {"type": "string", "description": "Metric name from list_metrics", "required": true},
  "dimensions": {"type": "array", "items": {"type": "string"}, "description": "Grouping dimensions", "required": false},
  "filters": {"type": "object", "description": "Key-value filter pairs", "required": false},
  "time_range": {
    "type": "object",
    "properties": {
      "start": {"type": "string", "format": "date"},
      "end": {"type": "string", "format": "date"},
      "grain": {"type": "string", "enum": ["day", "month", "quarter"]}
    },
    "required": false
  },
  "context": {"type": "string", "description": "Context to use (required if metric is context-ambiguous)", "required": false}
}
```

**Returns**: Query result with columns, rows, and provenance URI.

---

### MCP Tool: explain_metric

**Description**: Get full definition, ontology class, lineage, and example values for a metric.

**Parameters**
```json
{
  "metric": {"type": "string", "required": true},
  "context": {"type": "string", "required": false}
}
```

**Returns**: Metric definition, OWL class description, compiled SQL, lineage.

---

### MCP Tool: list_contexts

**Description**: List all available contexts for the authenticated tenant.

**Parameters**: none

**Returns**: Array of context objects (name, description, metric_count).

---

### MCP Tool: search_entities

**Description**: Search the knowledge graph for entities by name or description.

**Parameters**
```json
{
  "query": {"type": "string", "description": "Search query", "required": true},
  "entity_type": {"type": "string", "description": "Filter by ontology class IRI (e.g., fibo:CommercialBank)", "required": false},
  "context": {"type": "string", "required": false},
  "limit": {"type": "integer", "default": 10, "maximum": 50}
}
```

**Returns**: Array of entity objects with IRI, label, ontology_class, score.

---

*End of API Contracts v1.0.0*
