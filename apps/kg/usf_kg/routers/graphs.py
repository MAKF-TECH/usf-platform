"""GET /graphs, GET /graphs/{uri} — list and describe named graphs."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from urllib.parse import unquote

from ..models import GraphListResponse, GraphSummary

router = APIRouter(prefix="/graphs", tags=["graphs"])


@router.get("", response_model=GraphListResponse)
async def list_graphs(request: Request):
    qlever = request.app.state.qlever
    try:
        uris = await qlever.list_graphs()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return GraphListResponse(
        graphs=[GraphSummary(uri=u) for u in uris],
        total=len(uris),
    )


@router.get("/{graph_uri:path}", response_model=GraphSummary)
async def get_graph(graph_uri: str, request: Request):
    qlever = request.app.state.qlever
    uri = unquote(graph_uri)
    try:
        count = await qlever.triple_count(uri)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return GraphSummary(uri=uri, triple_count=count)
