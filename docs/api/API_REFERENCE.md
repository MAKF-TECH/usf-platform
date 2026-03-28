# USF API Reference

## Base URL

All API requests go through the gateway: `http://localhost:8000`

Individual services are also directly accessible for development:

| Service | Port | Docs |
|---------|------|------|
| usf-api (gateway) | 8000 | http://localhost:8000/docs |
| usf-query | 8001 | http://localhost:8001/docs |
| usf-kg | 8002 | http://localhost:8002/docs |
| usf-ingest | 8003 | http://localhost:8003/docs |
| usf-sdl | 8004 | http://localhost:8004/docs |
| usf-mcp | 8005 | http://localhost:8005/docs |
| usf-audit | 8006 | http://localhost:8006/docs |

## Authentication

```
POST /auth/login
Content-Type: application/json

{"email": "analyst@acme-bank.com", "password": "demo123"}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

Include in all requests: `Authorization: Bearer {access_token}`

Refresh: `POST /auth/refresh` with `{"refresh_token": "..."}`

## Context Headers

**X-USF-Context**: Required for metrics defined in multiple contexts.

- If set → query scoped to that context's named graph
- If omitted + metric has ONE context → auto-resolves
- If omitted + metric has MULTIPLE contexts → **409 Conflict**

```json
{
  "error": "context_ambiguous",
  "metric": "balance",
  "available_contexts": ["finance", "risk", "ops"],
  "hint": "Set X-USF-Context header to one of the available_contexts"
}
```

## Response Envelope

All query responses follow this structure:

```json
{
  "meta": {
    "requestId": "uuid",
    "context": "finance",
    "tenant": "acme-bank",
    "semanticModelVersion": "v2026-Q1",
    "queryTimeMs": 142,
    "cacheHit": false
  },
  "data": [ ... ],
  "schema": {
    "metrics": ["total_exposure_by_counterparty"],
    "dimensions": ["counterparty_name", "counterparty_country"],
    "ontologyClasses": {
      "total_exposure_by_counterparty": "fibo:FinancialExposure"
    }
  },
  "provenance": {
    "@context": {"prov": "http://www.w3.org/ns/prov#"},
    "@type": "prov:Entity",
    "prov:wasGeneratedBy": {
      "@type": "prov:Activity",
      "usf:contextApplied": "finance",
      "usf:ontologyVersion": "fibo-2024-Q4",
      "usf:queryHash": "sha256:a3f..."
    }
  }
}
```

## Gateway Endpoints (usf-api, port 8000)

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Get JWT access + refresh tokens |
| POST | `/auth/refresh` | Refresh access token |
| GET | `/auth/me` | Current user claims |

### Semantic Queries

| Method | Path | Description |
|--------|------|-------------|
| POST | `/query` | Execute semantic query (SQL/SPARQL/NL) with PROV-O |
| GET | `/metrics` | List available metrics (ABAC-filtered) |
| GET | `/metrics/{name}` | Metric definition + lineage |
| GET | `/contexts` | List tenant's semantic contexts |
| GET | `/entities/search?q=...` | Search KG entities |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |

## Knowledge Graph (usf-kg, port 8002)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/triples` | Insert triples to named graph |
| GET | `/graphs` | List named graphs for tenant |
| GET | `/graphs/{uri}` | Named graph metadata + stats |
| GET | `/entities/{iri}` | Entity detail + neighbors |
| POST | `/entities/resolve-by-label` | Entity resolution (canonical IRI) |
| POST | `/validate` | SHACL validation |
| POST | `/ontology/load` | Load industry ontology module |
| GET | `/provenance/{iri}` | PROV-O chain for entity/query |

## Query Engine (usf-query, port 8001)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/compile` | SDL metric → SQL + SPARQL |
| POST | `/execute/sql` | Compile + run SQL (Wren/DataFusion) |
| POST | `/execute/sparql` | Compile + run SPARQL (Ontop/QLever) |
| POST | `/execute/nl` | NL → SPARQL with ontology validation |
| POST | `/execute/ograg` | OG-RAG hybrid retrieval for AI agents |
| GET | `/explain/{metric}` | Full metric definition + lineage |

## SDL Compiler (usf-sdl, port 8004)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/validate` | Validate SDL YAML syntax |
| POST | `/compile` | SDL → OWL + SQL + R2RML + PROV-O template |
| GET | `/versions` | SDL version history |
| POST | `/publish` | Publish new SDL version to KG |
| GET | `/diff/{v1}/{v2}` | Semantic diff between versions |
| GET | `/ontology/{module}` | Browse ontology module classes |

## Ingestion (usf-ingest, port 8003)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/sources` | Register a data source |
| GET | `/sources` | List data sources |
| GET | `/sources/{id}` | Data source detail |
| POST | `/jobs` | Trigger ingestion job (async) |
| GET | `/jobs/{id}` | Job status + stats |
| GET | `/jobs/{id}/trace` | Full Layer 1 trace |
| POST | `/bootstrap/ontorag` | Trigger OntoRAG ontology derivation |

## Audit (usf-audit, port 8006)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/log` | Paginated audit log (filtered) |
| GET | `/log/{query_hash}` | Full PROV-O for specific query |
| GET | `/lineage/{iri}` | Entity lineage chain |
| POST | `/export` | Export PROV-O as Turtle/JSON-LD |
| GET | `/stats` | Audit statistics for dashboard |

## MCP Tools (usf-mcp, port 8005)

Available as MCP tools for AI agents:

| Tool | Description |
|------|-------------|
| `usf_list_metrics` | List available metrics (optional context filter) |
| `usf_query_metric` | Execute governed metric query with provenance |
| `usf_explain_metric` | Get metric definition + SQL + OWL class |
| `usf_search_entities` | Semantic search over KG entities |
| `usf_get_entity` | Get entity detail + PROV-O |
| `usf_list_contexts` | Available contexts for current user |

## Error Codes

| Code | Error | Description |
|------|-------|-------------|
| 400 | `validation_error` | Invalid request parameters |
| 401 | `unauthorized` | Missing or invalid JWT |
| 403 | `access_denied` | ABAC policy denied (wrong role/clearance) |
| 404 | `not_found` | Resource or context not found |
| 409 | `context_ambiguous` | Metric defined in multiple contexts — set X-USF-Context |
| 422 | `sdl_compile_error` | SDL YAML compilation failed |
| 429 | `rate_limit_exceeded` | Too many requests (60/min per tenant) |
| 500 | `internal_error` | Server error |
| 502 | `sidecar_unavailable` | QLever/ArcadeDB/OPA sidecar down |
