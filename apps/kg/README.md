# usf-kg — Knowledge Graph Service

## Overview

`usf-kg` is the Layer 2 knowledge graph service in the USF platform. It manages:

- **Named graphs** in QLever (RDF quad store)
- **Entity resolution** (owl:sameAs + canonical IRI assignment)
- **SHACL validation** against FIBO/FHIR shapes with quarantine routing
- **PROV-O provenance** queries
- **OWL ontology loading** (FIBO modules, custom shapes)
- **ArcadeDB** property graph sync for Cypher queries and vector search

## Tech Stack

- Python 3.12 + FastAPI + uvicorn
- QLever (SPARQL 1.1 + named graphs)
- ArcadeDB (property graph + vector index, Cypher)
- pySHACL + rdflib via `packages/rdf`
- loguru (structured JSON logs)

## Running Locally

```bash
# From repo root
docker compose up qlever arcadedb postgres

cd apps/kg
pip install -e ".[dev]" -e ../../packages/rdf -e ../../packages/core
uvicorn usf_kg.main:app --reload
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /triples | Bulk insert triples into named graph |
| GET | /graphs | List all named graphs |
| GET | /graphs/{uri} | Describe a named graph |
| GET | /entities/{iri} | Entity detail + properties |
| POST | /entities/resolve | Entity resolution (owl:sameAs) |
| POST | /validate | Run pySHACL on a named graph |
| POST | /ontology/load | Load OWL/Turtle into named graph |
| GET | /provenance/{iri} | PROV-O chain for entity |

## Configuration (env vars with prefix `USF_KG_`)

| Variable | Default | Description |
|----------|---------|-------------|
| `USF_KG_QLEVER_URL` | `http://qlever:7001` | QLever SPARQL query endpoint |
| `USF_KG_QLEVER_UPDATE_URL` | `http://qlever:7001/update` | QLever SPARQL update endpoint |
| `USF_KG_ARCADEDB_URL` | `http://arcadedb:2480` | ArcadeDB HTTP API |
| `USF_KG_ARCADEDB_USER` | `root` | ArcadeDB user |
| `USF_KG_ARCADEDB_PASS` | `changeme` | ArcadeDB password |
| `USF_KG_DATABASE_URL` | `postgresql+psycopg://...` | PostgreSQL (shared) |
