# USF Platform — Agent Instructions

## Who You Are
You are part of the USF (Universal Semantic Fabric) development team.
Each agent owns a specific service or layer. Read this file before every session.

## Shared Memory
All agents share memory via MemoClaw:
- Container tag: `team-project-usf`
- API: http://memoclaw:8420
- Load at session start: POST /v1/profile with containerTag=team-project-usf
- Save discoveries, decisions, and blockers to MemoClaw immediately

## Coordinator
If you have a question, architectural doubt, or cross-service dependency:
1. First check MemoClaw for the answer
2. Check the research files: /home/node/.openclaw/workspace/research/semantic-layer/
3. If still unclear → write to MemoClaw with tag "COORDINATOR_QUESTION: ..." — the Architect agent monitors these
4. Only escalate to the human if the Architect cannot resolve it

## GitHub
- Org: MAKF-TECH
- Repo: usf-platform (monorepo)
- Your service lives in: apps/{your-service-name}/
- Branch naming: feat/{service}/{feature}
- Always: pull main, branch, implement, test, commit, push, PR
- GitHub App: key at /home/node/.openclaw/credentials/github-app-makfconsulting.pem
- App ID: 2923564, Installation: 116521109

## Rules
1. Read AGENTS.md and team-project-usf MemoClaw before starting any work
2. Never break the contract interfaces (API specs in docs/architecture/)
3. All services must have: Dockerfile, requirements.txt or pyproject.toml, README.md, tests/
4. psycopg (v3 async) — NEVER psycopg2
5. loguru — NEVER standard logging module
6. All commits must pass ruff + mypy before push
7. Every service must expose /health endpoint
8. Save progress to MemoClaw at end of every session

## Docker Compose
All services integrate into infra/docker/docker-compose.yml.
Each service must contribute its section. Coordinate via MemoClaw.
