# USF — Universal Semantic Fabric

**Multi-tenant SaaS that maps any industry's data onto formal ontologies, enabling semantic queries,
regulatory-grade provenance, and AI-ready knowledge graphs — without changing your database.**

---

## Architecture

USF is built on four semantic layers:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 4 — Access & Intelligence                                     │
│  REST API (8000) · MCP Tools (8006) · Angular UI (4200)             │
│  Natural Language queries · OG-RAG · SPARQL                         │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 3 — Semantic Query Engine (8001)                              │
│  SDL → SQL compiler (SQLGlot, 4 dialects)                           │
│  SDL → SPARQL via R2RML/Ontop                                        │
│  NL2SPARQL (LLM-validated)                                           │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 2 — Ontology-Grounded Knowledge Graph (8002)                  │
│  ArcadeDB + QLever (OWL 2 QL SPARQL engine)                         │
│  SHACL validation · PROV-O provenance chains                         │
│  Named-graph isolation per tenant × context                          │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 1 — Ingestion & SDL Compiler (8003 / 8004)                    │
│  SDL YAML → OWL + SQL + R2RML + SHACL                               │
│  CSV/warehouse → triples (Gemini extraction, confidence scoring)     │
│  OpenLineage audit events                                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Docker + Docker Compose v2
- 8 GB RAM recommended (runs ArcadeDB + QLever + 7 FastAPI services)

### Start the Stack

```bash
git clone https://github.com/MAKF-TECH/usf-platform.git
cd usf-platform
make up
```

### Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| **API** | http://localhost:8000 | Main REST API + auth |
| **UI** | http://localhost:4200 | Angular dashboard |
| **Grafana** | http://localhost:3000 | Observability (admin/admin) |
| **ArcadeDB** | http://localhost:2480 | Knowledge graph browser |
| **QLever** | http://localhost:7001 | SPARQL endpoint |
| **OPA** | http://localhost:8181 | Access control policy engine |

### Load Banking Pilot Data

```bash
make pilot-data    # loads IBM AML dataset (~200k transactions) into Postgres
```

Then navigate to http://localhost:4200 and log in with `admin@usf.local` / `admin`.

---

## Python SDK

```bash
pip install usf-sdk
```

```python
import asyncio
from usf_sdk import USFClient, ContextAmbiguousError

async def main():
    async with USFClient("http://localhost:8000", context="finance") as client:
        await client.login("analyst@acme-bank.com", "demo123")
        result = await client.query(
            "total_exposure_by_counterparty",
            dimensions=["counterparty_name", "counterparty_country"],
            time_range={"start": "2024-01-01", "end": "2024-03-31"},
        )
        print(result.data)

asyncio.run(main())
```

→ Full docs: [`packages/sdk-python/README.md`](packages/sdk-python/README.md)

---

## TypeScript SDK

```bash
npm install @usf/sdk
```

```typescript
import { USFClient } from "@usf/sdk";

const client = new USFClient("http://localhost:8000", { context: "finance" });
await client.login("analyst@acme-bank.com", "demo123");

const result = await client.query("total_exposure_by_counterparty", {
  dimensions: ["counterparty_name", "counterparty_country"],
  timeRange: { start: "2024-01-01", end: "2024-03-31" },
});
console.log(result.data);
```

→ Full docs: [`packages/sdk-typescript/README.md`](packages/sdk-typescript/README.md)

---

## Industry Ontology Modules

| Industry | Module Key | Standard | Onboarding Guide |
|----------|-----------|----------|-----------------|
| Banking / Capital Markets | `fibo` | FIBO OWL-DL (EDM Council / OMG) | [fibo-banking.md](docs/ontologies/fibo-banking.md) |
| Healthcare | `fhir` | HL7 FHIR R4 | [fhir-healthcare.md](docs/ontologies/fhir-healthcare.md) |
| Energy / Utilities | `iec-cim` | IEC 61970/61968 CIM | [iec-cim-energy.md](docs/ontologies/iec-cim-energy.md) |
| Manufacturing / Industry 4.0 | `rami40` | RAMI 4.0 / AAS (IEC 62890) | [rami40-manufacturing.md](docs/ontologies/rami40-manufacturing.md) |

---

## SDL — Semantic Definition Language

SDL is the YAML language for defining semantic layer concepts. It compiles to:
OWL 2 QL (Turtle) · SQL (4 dialects) · R2RML (Ontop) · SHACL · PROV-O

→ [SDL Language Reference](docs/sdl/LANGUAGE_REFERENCE.md)

---

## Pilot Demo

The FIBO banking pilot uses the IBM AML Transactions dataset (~200k synthetic transactions)
to demonstrate:

- Context-sensitive metric queries (risk vs. finance vs. ops)
- 409 context disambiguation
- PROV-O provenance chains
- AML suspicious transaction analysis via SPARQL

→ [Pilot Demo](pilot/fibo-banking/README.md)

---

## Development

```bash
make up          # Start all services
make down        # Stop all services
make build       # Rebuild Docker images
make test        # Run all service test suites
make lint        # Ruff + mypy across all services
make health      # Check /health on all 7 services (ports 8000–8006)
make logs service=usf-api   # Tail a specific service's logs
make pilot-data  # Load IBM AML dataset into Postgres
```

### Repository Structure

```
usf-platform/
├── apps/                    # FastAPI microservices
│   ├── api/                 # usf-api (port 8000) — auth, query proxy, contexts
│   ├── query/               # usf-query (port 8001) — SQL/SPARQL/NL compiler
│   ├── kg/                  # usf-kg (port 8002) — knowledge graph operations
│   ├── sdl/                 # usf-sdl (port 8003) — SDL compiler + versioning
│   ├── ingest/              # usf-ingest (port 8004) — CSV/warehouse ingestion
│   ├── audit/               # usf-audit (port 8005) — provenance + lineage
│   └── mcp/                 # usf-mcp (port 8006) — AI agent MCP tools
├── packages/
│   ├── sdk-python/          # Python SDK (usf-sdk)
│   ├── sdk-typescript/      # TypeScript SDK (@usf/sdk)
│   └── sdl-schema/          # Shared SDL Pydantic models
├── pilot/fibo-banking/      # Banking pilot — IBM AML dataset
├── docs/
│   ├── architecture/        # API contracts, schemas, conventions
│   ├── sdl/                 # SDL Language Reference
│   └── ontologies/          # Per-industry onboarding guides
└── infra/docker/            # Docker Compose stack
```

---

## API Reference

→ [docs/architecture/api-contracts.md](docs/architecture/api-contracts.md)

All 7 microservices expose `/health` and follow the standard response envelope:

```json
{
  "data": {},
  "meta": {
    "request_id": "uuid", "tenant_id": "uuid", "context": "finance",
    "named_graph": "usf://tenant/context/finance/v1",
    "prov_o_uri": "usf://tenant/provenance/...",
    "cached": false, "execution_ms": 187
  }
}
```
