# Contributing to USF

## Development Setup

```bash
git clone https://github.com/MAKF-TECH/usf-platform.git
cd usf-platform
cp infra/docker/.env.example infra/docker/.env
make up
```

## Service Development

Each service is a self-contained FastAPI app:

```bash
cd apps/api
pip install -e ../../packages/core -e ../../packages/rdf -e ../../packages/sdl-schema
pip install -e ".[dev]"
uvicorn usf_api.main:app --reload --port 8000
```

### Service Ports

| Service | Port | Description |
|---------|------|-------------|
| usf-api | 8000 | API Gateway |
| usf-query | 8001 | Query Engine |
| usf-kg | 8002 | Knowledge Graph |
| usf-ingest | 8003 | Data Ingestion |
| usf-sdl | 8004 | SDL Compiler |
| usf-mcp | 8005 | MCP Tools |
| usf-audit | 8006 | Audit Service |

## Code Standards

- **Python 3.12+**
- **`ruff`** for linting + formatting
- **`mypy`** for type checking
- **psycopg v3** async — never psycopg2
- **loguru** — never standard logging
- **Pydantic v2** — `model_dump()` not `.dict()`
- **FastAPI** with type-annotated endpoints
- **SQLModel** for database models

## OpenAPI Documentation

Every endpoint must have:
- `summary` — short one-liner
- `description` — detailed behavior, including ABAC/context/PROV-O impact
- `response_model` — typed return value
- `responses` — error status codes with descriptions
- `tags` — matching the service's `openapi_tags`

## PR Guidelines

- Branch from `main`: `feat/{area}/{description}`
- Tests required for new endpoints
- `ruff check .` + `mypy .` must pass
- Describe the 409/ABAC impact of any context-related changes
- One commit per logical change

## Architecture

See `docs/architecture/` for contracts and conventions.
See `docs/api/API_REFERENCE.md` for the unified API reference.
