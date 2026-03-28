"""POST /compile — compile SDL YAML → OWL+SQL+R2RML+prov_template."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.owl_compiler import compile_sdl_to_owl
from ..services.sql_compiler import compile_all_dialects
from ..services.r2rml_gen import generate_r2rml
from ..services.skos_aligner import SKOSAligner

router = APIRouter(prefix="/compile", tags=["compile"])
_aligner = SKOSAligner()

SUPPORTED_DIALECTS = ("postgres", "snowflake", "bigquery")


class CompileRequest(BaseModel):
    yaml_content: str
    table_map: dict[str, str] | None = Field(
        default=None,
        description="Override table names per entity: {EntityName: 'sql_table'}",
    )
    namespace: str = Field(
        default="https://usf.makf.tech/ontology/",
        description="Ontology namespace for OWL/R2RML output",
    )


class SqlArtifacts(BaseModel):
    postgres: str = ""
    snowflake: str = ""
    bigquery: str = ""


class CompileResponse(BaseModel):
    owl_turtle: str
    sql: dict[str, SqlArtifacts]  # keyed by metric name
    r2rml: str
    prov_template: dict[str, Any]
    skos_mappings: str
    entity_count: int
    metric_count: int


def _build_prov_template(sdl: dict, namespace: str) -> dict[str, Any]:
    """Build a PROV-O JSON-LD template for the compiled SDL document."""
    compile_id = f"compile-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    entities = [e["name"] for e in sdl.get("entities", [])]
    metrics = [m["name"] for m in sdl.get("metrics", [])]
    return {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "usf": "https://usf.makf.tech/ontology/",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        },
        "@id": f"https://usf.makf.tech/prov/compile/{compile_id}",
        "@type": "prov:Activity",
        "prov:startedAtTime": {"@value": now, "@type": "xsd:dateTime"},
        "prov:endedAtTime": {"@value": now, "@type": "xsd:dateTime"},
        "usf:sdlVersion": sdl.get("version", "1.0"),
        "usf:namespace": namespace,
        "usf:entities": entities,
        "usf:metrics": metrics,
        "prov:generated": [
            {"@id": f"https://usf.makf.tech/artifact/owl/{compile_id}"},
            {"@id": f"https://usf.makf.tech/artifact/r2rml/{compile_id}"},
        ],
    }


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

    # OWL compilation
    try:
        owl = compile_sdl_to_owl(sdl)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OWL compilation failed: {exc}") from exc

    # SQL per metric × dialect
    sql_artifacts: dict[str, SqlArtifacts] = {}
    for metric in sdl.get("metrics", []):
        metric_name = metric.get("name", "unknown")
        dialects = compile_all_dialects(metric, entity_map)
        sql_artifacts[metric_name] = SqlArtifacts(
            postgres=dialects.get("postgres", ""),
            snowflake=dialects.get("snowflake", ""),
            bigquery=dialects.get("bigquery", ""),
        )

    # R2RML generation
    try:
        r2rml = generate_r2rml(sdl, entity_map)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"R2RML generation failed: {exc}") from exc

    # SKOS alignments
    skos = _aligner.generate_skos_mappings(sdl)
    prov_template = _build_prov_template(sdl, body.namespace)

    # PROV-O template
    prov_template = _build_prov_template(sdl, body.namespace)

    return CompileResponse(
        owl_turtle=owl,
        sql=sql_artifacts,
        r2rml=r2rml,
        prov_template=prov_template,
        skos_mappings=skos,
        entity_count=len(sdl.get("entities", [])),
        metric_count=len(sdl.get("metrics", [])),
    )
