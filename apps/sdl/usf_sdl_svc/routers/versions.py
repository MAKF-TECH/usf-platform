"""GET /versions, POST /publish — SDL version management."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/versions", tags=["versions"])

# In-memory store for now (will be backed by PostgreSQL via SQLModel)
_versions: dict[str, dict] = {}


class VersionOut(BaseModel):
    version: str
    is_active: bool
    published_at: str | None
    entity_count: int


class PublishRequest(BaseModel):
    version: str
    yaml_content: str
    compiled_owl: str | None = None
    compiled_sql: dict[str, str] | None = None
    compiled_r2rml: str | None = None


@router.get("", response_model=list[VersionOut])
async def list_versions():
    return [
        VersionOut(
            version=v,
            is_active=data.get("is_active", False),
            published_at=data.get("published_at"),
            entity_count=data.get("entity_count", 0),
        )
        for v, data in sorted(_versions.items())
    ]


@router.post("/publish", response_model=VersionOut, status_code=201)
async def publish_version(body: PublishRequest):
    from datetime import datetime, timezone
    import yaml

    if body.version in _versions:
        raise HTTPException(status_code=409, detail=f"Version '{body.version}' already exists")

    try:
        sdl = yaml.safe_load(body.yaml_content)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    entity_count = len(sdl.get("entities", []))
    now = datetime.now(timezone.utc).isoformat()

    _versions[body.version] = {
        "yaml_content": body.yaml_content,
        "is_active": True,
        "published_at": now,
        "entity_count": entity_count,
    }
    # Deactivate previous versions
    for v, data in _versions.items():
        if v != body.version:
            data["is_active"] = False

    return VersionOut(
        version=body.version,
        is_active=True,
        published_at=now,
        entity_count=entity_count,
    )
