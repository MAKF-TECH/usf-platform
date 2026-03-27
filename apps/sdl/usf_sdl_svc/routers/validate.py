"""POST /validate — Pydantic SDL validation."""
from __future__ import annotations

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/validate", tags=["validate"])

REQUIRED_TOP_KEYS = {"version", "namespace", "entities"}


class SDLValidateRequest(BaseModel):
    yaml_content: str


class SDLValidateResponse(BaseModel):
    valid: bool
    errors: list[str]
    entity_count: int
    metric_count: int


@router.post("", response_model=SDLValidateResponse)
async def validate_sdl(body: SDLValidateRequest):
    errors: list[str] = []

    try:
        sdl = yaml.safe_load(body.yaml_content)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=422, detail=f"YAML parse error: {exc}") from exc

    if not isinstance(sdl, dict):
        raise HTTPException(status_code=422, detail="SDL must be a YAML object")

    # Check required top-level keys
    for key in REQUIRED_TOP_KEYS:
        if key not in sdl:
            errors.append(f"Missing required key: '{key}'")

    # Validate entities
    entity_count = 0
    for i, entity in enumerate(sdl.get("entities", [])):
        entity_count += 1
        if "name" not in entity:
            errors.append(f"Entity[{i}] missing 'name'")
        if "fields" not in entity:
            errors.append(f"Entity '{entity.get('name', i)}' missing 'fields'")
        for j, field in enumerate(entity.get("fields", [])):
            if "name" not in field:
                errors.append(f"Entity '{entity.get('name', i)}' field[{j}] missing 'name'")

    # Validate metrics
    metric_count = 0
    for i, metric in enumerate(sdl.get("metrics", [])):
        metric_count += 1
        for key in ("name", "entity", "aggregation", "field"):
            if key not in metric:
                errors.append(f"Metric[{i}] missing '{key}'")

    return SDLValidateResponse(
        valid=len(errors) == 0,
        errors=errors,
        entity_count=entity_count,
        metric_count=metric_count,
    )
