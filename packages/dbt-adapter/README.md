# USF dbt Adapter

Import your existing dbt Semantic Layer metrics into USF.

## Installation

```bash
pip install -e packages/dbt-adapter
```

## Usage

```python
from usf_dbt import USFDbtAdapter

adapter = USFDbtAdapter(
    dbt_project_path="./my-dbt-project",
    usf_api_url="http://localhost:8000"
)

# Discover and convert
metrics = adapter.discover_metrics()
sdl_yaml = adapter.export_sdl_yaml()

# Or sync directly to USF
result = adapter.sync_to_usf(tenant_id="acme-bank", context="finance")
```

## Supported dbt metric types → USF metric types

| dbt             | USF            |
|-----------------|----------------|
| sum             | sum            |
| count           | count          |
| average         | avg            |
| count_distinct  | count_distinct |
| derived         | derived        |

## How It Works

1. **Discover** — Scans your dbt project for `schema.yml` files containing metric definitions
2. **Convert** — Maps dbt metric fields to USF SDL metric format
3. **Export** — Produces SDL-compatible YAML ready for `usf-sdl /compile`
4. **Sync** — Optionally POSTs the SDL directly to a running USF instance
