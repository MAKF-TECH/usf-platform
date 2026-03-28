# USF Docker Development Environment

## Quick Start
```bash
cd infra/docker
cp .env.example .env
docker compose up -d
```

## Architecture
20 containers running: 9 USF services + 5 databases + 3 sidecars + 3 observability

## Ports
| Container | Port | Description |
|-----------|------|-------------|
| usf-api | 8000 | Main API gateway (FastAPI docs at /docs) |
| usf-query | 8001 | Query compilation + NL2SPARQL |
| usf-kg | 8002 | Knowledge graph management |
| usf-ingest | 8003 | Data ingestion (structured + unstructured) |
| usf-sdl | 8004 | SDL YAML compiler |
| usf-mcp | 8005 | MCP server for AI agents |
| usf-audit | 8006 | Audit log + compliance |
| usf-ui | 4200 | Angular frontend |
| qlever | 7001 | SPARQL endpoint |
| arcadedb | 2480 | Property graph + vector (Cypher HTTP) |
| postgres | 5432 | Platform DB |
| valkey | 6379 | Cache + Celery broker |
| redpanda | 19092 | Event bus (Kafka-compatible) |
| opa | 8181 | ABAC policy engine |
| grafana | 3000 | Dashboards (admin/admin) |
| prometheus | 9090 | Metrics |
| loki | 3100 | Log aggregation |

## Useful Commands
```bash
# Check health of all services
make health

# View logs for a service
make logs service=usf-api

# Shell into a container
make shell service=usf-kg

# Rebuild a single service
docker compose build usf-api && docker compose up -d usf-api

# Clean everything (removes data!)
make clean
```

## Troubleshooting

### Service won't start
Check logs: `docker compose logs usf-<service>`.

### Database connection refused
Ensure postgres is healthy: `docker compose ps postgres`.

### Reset everything
```bash
docker compose down -v
docker compose up -d
```
