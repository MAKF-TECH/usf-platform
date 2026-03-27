.PHONY: up down build logs shell test lint health pilot-data

DOCKER_DIR=infra/docker

up:
	cd $(DOCKER_DIR) && docker compose up -d
	@echo ""
	@echo "USF stack starting — services:"
	@echo "  API:      http://localhost:8000"
	@echo "  UI:       http://localhost:4200"
	@echo "  Grafana:  http://localhost:3000"
	@echo "  ArcadeDB: http://localhost:2480"
	@echo "  QLever:   http://localhost:7001"
	@echo "  OPA:      http://localhost:8181"
	@echo ""

down:
	cd $(DOCKER_DIR) && docker compose down

down-v:
	cd $(DOCKER_DIR) && docker compose down -v

build:
	cd $(DOCKER_DIR) && docker compose build

logs:
	cd $(DOCKER_DIR) && docker compose logs -f $(service)

shell:
	cd $(DOCKER_DIR) && docker compose exec $(service) /bin/sh

test:
	@for svc in api query kg ingest sdl mcp audit worker; do \
		echo "Testing apps/$$svc..."; \
		cd apps/$$svc && pip install -e ".[dev]" -q && pytest -q && cd ../..; \
	done

lint:
	@for svc in api query kg ingest sdl mcp audit worker; do \
		echo "Linting apps/$$svc..."; \
		cd apps/$$svc && ruff check . && mypy . --ignore-missing-imports && cd ../..; \
	done

health:
	@echo "Checking service health..."
	@for port in 8000 8001 8002 8003 8004 8005 8006; do \
		printf "Port $$port: "; \
		curl -sf http://localhost:$$port/health && echo "OK" || echo "FAIL"; \
	done

pilot-data:
	python3 pilot/fibo-banking/load_aml_dataset.py
