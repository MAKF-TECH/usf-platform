# usf-sdk — Python SDK for Universal Semantic Fabric

[![PyPI](https://img.shields.io/pypi/v/usf-sdk)](https://pypi.org/project/usf-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/usf-sdk)](https://pypi.org/project/usf-sdk/)

Async-first Python client for the [USF platform](../../README.md) — query ontology-aligned
business metrics, traverse the knowledge graph, and run raw SPARQL.

## Installation

```bash
pip install usf-sdk
```

## Quick Start

```python
import asyncio
from usf_sdk import USFClient, ContextAmbiguousError

async def main():
    async with USFClient("http://localhost:8000", context="finance") as client:
        await client.login("analyst@acme-bank.com", "demo123")

        metrics = await client.list_metrics()
        result = await client.query(
            "total_exposure_by_counterparty",
            dimensions=["counterparty_name", "counterparty_country"],
            time_range={"start": "2024-01-01", "end": "2024-03-31"},
        )
        print(result.data)

asyncio.run(main())
```

## API Reference

### `USFClient(base_url, *, api_key=None, tenant=None, context=None)`

| Method | Description |
|--------|-------------|
| `login(email, password)` | Authenticate, store JWT. Returns `self`. |
| `list_contexts()` | List semantic contexts available to this tenant. |
| `list_metrics(context, search)` | Paginated metric catalogue. |
| `query(metric, dimensions, filters, time_range, context)` | Execute a semantic query. |
| `explain(metric, context)` | Full metric definition + compiled SQL. |
| `search_entities(query, entity_type, context)` | Semantic KG search. |
| `get_entity(iri, depth)` | Entity detail with PROV-O provenance. |
| `sparql(query, context)` | Raw SPARQL SELECT. |
| `ingest_csv(file_path, source_name, ontology_module)` | Trigger CSV ingestion. |
| `job_status(job_id)` | Check ingestion job. |

### Error Handling

| Exception | HTTP | When |
|-----------|------|------|
| `AuthError` | 401 | Token missing or expired |
| `ContextAmbiguousError` | 409 | Metric spans multiple contexts; check `.available_contexts` |
| `AccessDeniedError` | 403 | ABAC policy denied |
| `NotFoundError` | 404 | Metric/entity not found |
| `ValidationError` | 400/422 | Bad request or semantic validation failure |

```python
from usf_sdk import ContextAmbiguousError

try:
    result = await client.query("balance")
except ContextAmbiguousError as e:
    print(f"Set context to one of: {e.available_contexts}")
    result = await client.query("balance", context=e.available_contexts[0])
```

## Examples

- [`examples/banking_pilot.py`](examples/banking_pilot.py) — full FIBO banking demo
