"""POST /validate — pySHACL validation of a named graph."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from rdflib import Graph

from ..models import ValidateRequest, ValidateResponse, ViolationOut
from ..config import settings

router = APIRouter(prefix="/validate", tags=["validate"])


@router.post("", response_model=ValidateResponse)
async def validate(request: Request, body: ValidateRequest):
    qlever = request.app.state.qlever
    shacl_svc = request.app.state.shacl_service

    # Fetch data from QLever as N-Triples, parse into rdflib Graph
    try:
        sparql_result = await qlever.client.query(
            f"CONSTRUCT {{ ?s ?p ?o }} WHERE {{ GRAPH <{body.graph_uri}> {{ ?s ?p ?o }} }}",
            accept="text/plain",  # N-Triples
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch graph: {exc}") from exc

    data_graph = Graph()
    if isinstance(sparql_result, str):
        data_graph.parse(data=sparql_result, format="nt")
    # If QLever returns JSON for CONSTRUCT, handle both formats

    shapes_graph = None
    if body.shapes_turtle:
        shapes_graph = Graph()
        shapes_graph.parse(data=body.shapes_turtle, format="turtle")

    quarantine_graph = f"{settings.quarantine_graph_prefix}{body.graph_uri.split('/')[-1]}"

    try:
        conforms, violations = await shacl_svc.validate_graph(
            data_graph,
            shapes_graph=shapes_graph,
            quarantine_graph=quarantine_graph,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    violation_out = [
        ViolationOut(
            focus_node=v.focus_node,
            result_path=v.result_path,
            value=v.value,
            source_shape=v.source_shape,
            message=v.message,
            severity=v.severity,
        )
        for v in violations
    ]
    return ValidateResponse(
        conforms=conforms,
        violations=violation_out,
        quarantined_graph=quarantine_graph if not conforms else None,
    )
