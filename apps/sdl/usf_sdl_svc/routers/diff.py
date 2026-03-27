"""GET /diff/{v1}/{v2} — diff two SDL versions."""
from __future__ import annotations

import difflib
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .versions import _versions

router = APIRouter(prefix="/diff", tags=["diff"])


class DiffResponse(BaseModel):
    v1: str
    v2: str
    unified_diff: str
    entities_added: list[str]
    entities_removed: list[str]
    entities_modified: list[str]


@router.get("/{v1}/{v2}", response_model=DiffResponse)
async def diff_versions(v1: str, v2: str):
    if v1 not in _versions:
        raise HTTPException(status_code=404, detail=f"Version '{v1}' not found")
    if v2 not in _versions:
        raise HTTPException(status_code=404, detail=f"Version '{v2}' not found")

    yaml1 = _versions[v1]["yaml_content"]
    yaml2 = _versions[v2]["yaml_content"]

    lines1 = yaml1.splitlines(keepends=True)
    lines2 = yaml2.splitlines(keepends=True)
    diff = "".join(difflib.unified_diff(lines1, lines2, fromfile=v1, tofile=v2))

    # Entity-level diff
    sdl1 = yaml.safe_load(yaml1) or {}
    sdl2 = yaml.safe_load(yaml2) or {}

    names1 = {e["name"] for e in sdl1.get("entities", [])}
    names2 = {e["name"] for e in sdl2.get("entities", [])}

    added = sorted(names2 - names1)
    removed = sorted(names1 - names2)

    # Modified: same name but different field set
    modified = []
    for name in names1 & names2:
        e1 = next(e for e in sdl1["entities"] if e["name"] == name)
        e2 = next(e for e in sdl2["entities"] if e["name"] == name)
        if e1 != e2:
            modified.append(name)

    return DiffResponse(
        v1=v1,
        v2=v2,
        unified_diff=diff,
        entities_added=added,
        entities_removed=removed,
        entities_modified=modified,
    )
