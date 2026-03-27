"""POST /compile — compile SDL YAML → OWL+SQL+R2RML+prov_template."""
from __future__ import annotations

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.owl_compiler import compile_sdl_to_owl
from ..services.sql_compiler import compile_all_dialects
from ..services.r2rml_gen import generate_r2rml
from ..services.skos_aligner import SKOSAligner

router = APIRouter(prefix="/compile", tags=["compile"])
_aligner = SKOSAligner()


class CompileRequest(BaseModel):
    yaml_content: str
    table_map: dict[str, str] | None = None  # {EntityName: "sql_table"}


class CompileResponse(BaseModel):
    owl_turtle: str
    sql_by_dialect: dict[str, str]
    r2rml: str
    skos_mappings: str
    entity_count: int
    metric_count: int


@router.post("", response_model=CompileResponse, status_code=200)
async def compile_sdl(body: CompileRequest):
    try:
        sdl = yaml.safe_load(body.yaml_content)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=422, detail=f"YAML parse error: {exc}") from exc

    if not isinstance(sdl, dict):
        raise HTTPException(status_code=422, detail="SDL must be a YAML object")

    entity_map = body.table_map or {
        e["name"]: e["name"].lower()
        for e in sdl.get("entities", [])
    }

    try:
        owl = compile_sdl_to_owl(sdl)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OWL compilation failed: {exc}") from exc

    sql_all: dict[str, str] = {}
    for metric in sdl.get("metrics", []):
        dialects = compile_all_dialects(metric, entity_map)
        for dialect, sql in dialects.items():
            sql_all[f"{metric['name']}.{dialect}"] = sql

    try:
        r2rml = generate_r2rml(sdl, entity_map)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"R2RML generation failed: {exc}") from exc

    skos = _aligner.generate_skos_mappings(sdl)

    return CompileResponse(
        owl_turtle=owl,
        sql_by_dialect=sql_all,
        r2rml=r2rml,
        skos_mappings=skos,
        entity_count=len(sdl.get("entities", [])),
        metric_count=len(sdl.get("metrics", [])),
    )
