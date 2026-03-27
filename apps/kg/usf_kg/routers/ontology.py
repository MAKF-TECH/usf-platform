"""POST /ontology/load — load OWL/Turtle module into a named graph."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Request
from rdflib import Graph

from ..models import OntologyLoadRequest, OntologyLoadResponse
from usf_rdf import OWLLoader

router = APIRouter(prefix="/ontology", tags=["ontology"])


@router.post("/load", response_model=OntologyLoadResponse, status_code=201)
async def load_ontology(request: Request, body: OntologyLoadRequest):
    qlever = request.app.state.qlever

    turtle_content = body.turtle_content
    if not turtle_content and body.turtle_url:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(body.turtle_url)
                resp.raise_for_status()
                turtle_content = resp.text
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to fetch turtle: {exc}") from exc

    if not turtle_content:
        raise HTTPException(status_code=400, detail="Provide turtle_content or turtle_url")

    # Parse Turtle → rdflib Graph
    g = Graph()
    try:
        g.parse(data=turtle_content, format="turtle")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid Turtle: {exc}") from exc

    if body.resolve_imports:
        loader = OWLLoader()
        try:
            g = loader.load(body.turtle_url or "", format="turtle")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"OWL imports resolution failed: {exc}") from exc

    # Serialize to N-Triples for SPARQL INSERT
    nt = g.serialize(format="nt")
    sparql = f"INSERT DATA {{ GRAPH <{body.named_graph}> {{\n{nt}\n}} }}"
    try:
        await qlever.client.update(sparql)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"QLever insert failed: {exc}") from exc

    return OntologyLoadResponse(
        named_graph=body.named_graph,
        triples_loaded=len(g),
    )
