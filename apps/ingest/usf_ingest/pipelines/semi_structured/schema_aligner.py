from __future__ import annotations

"""LLM-assisted schema aligner — fields → ontology properties with confidence scores."""

import json

import httpx
from loguru import logger
from rdflib import Graph, URIRef

from usf_ingest.config import get_settings
from usf_ingest.utils.confidence import DEFAULT_CONFIDENCE_THRESHOLD, FieldMapping, filter_mappings, score_stats


async def align_fields(
    fields: list[dict[str, str]],
    ontology_context: str = "FIBO 2024-Q4",
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> tuple[list[FieldMapping], list[FieldMapping]]:
    settings = get_settings()
    prompt = f"""You are an ontology alignment expert for {ontology_context}.
Map each source field to the most appropriate ontology property URI.
Respond with a JSON array: [{{source_field, target_property (full URI), confidence (0-1), reasoning}}]

Fields:
{json.dumps(fields, indent=2)}

Return ONLY a valid JSON array."""

    raw = await _call_llm(prompt, settings)
    mappings = [
        FieldMapping(
            source_field=m["source_field"],
            target_property=m["target_property"],
            confidence=float(m.get("confidence", 0.5)),
            reasoning=m.get("reasoning", ""),
        )
        for m in raw
    ]
    accepted, quarantined = filter_mappings(mappings, threshold)
    logger.info("Schema alignment", extra={**score_stats(mappings), "accepted": len(accepted), "quarantined": len(quarantined)})
    return accepted, quarantined


async def align_graph(graph: Graph, tenant_id: str) -> tuple[Graph, int]:
    predicates = list({str(p) for _, p, _ in graph})
    if not predicates:
        return graph, 0

    fields = [{"name": p.split("/")[-1].split("#")[-1], "type": "uri", "description": p} for p in predicates[:30]]
    accepted, quarantined = await align_fields(fields)
    mapping = {m.source_field: m.target_property for m in accepted}
    quarantined_set = {m.source_field for m in quarantined}

    new_g = Graph()
    quarantined_count = 0
    for s, p, o in graph:
        p_local = str(p).split("/")[-1].split("#")[-1]
        if p_local in mapping:
            new_g.add((s, URIRef(mapping[p_local]), o))
        elif p_local in quarantined_set:
            quarantined_count += 1
        else:
            new_g.add((s, p, o))
    return new_g, quarantined_count


async def _call_llm(prompt: str, settings) -> list[dict]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{settings.LLM_API_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"},
            json={"model": settings.LLM_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1},
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        # Strip markdown fences if present
        content = content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        parsed = json.loads(content)
        return parsed if isinstance(parsed, list) else parsed.get("mappings", [])
