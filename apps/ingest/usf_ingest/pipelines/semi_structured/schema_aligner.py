from __future__ import annotations

"""LLM-assisted schema aligner.

Maps source fields → ontology properties with confidence scores.
Quarantines low-confidence mappings.
"""

import json
from typing import Any

import httpx
from loguru import logger
from rdflib import Graph, URIRef

from usf_ingest.config import get_settings
from usf_ingest.utils.confidence import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    FieldMapping,
    filter_mappings,
    score_stats,
)


async def align_fields(
    fields: list[dict[str, str]],
    ontology_context: str = "FIBO 2024-Q4",
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> tuple[list[FieldMapping], list[FieldMapping]]:
    """
    Use LLM to map source fields → ontology properties with confidence scores.

    Args:
        fields: List of {name, type, description} dicts.
        ontology_context: Which ontology to align against.
        threshold: Minimum confidence to accept a mapping.

    Returns:
        (accepted_mappings, quarantined_mappings)
    """
    settings = get_settings()

    prompt = f"""You are an ontology alignment expert for {ontology_context}.
Map each source field to the most appropriate ontology property URI.
Respond with a JSON array of objects with keys:
  source_field, target_property (full URI), confidence (0-1), reasoning

Fields to map:
{json.dumps(fields, indent=2)}

Return ONLY valid JSON array, no markdown."""

    raw_mappings = await _call_llm(prompt, settings)

    mappings = [
        FieldMapping(
            source_field=m["source_field"],
            target_property=m["target_property"],
            confidence=float(m.get("confidence", 0.5)),
            reasoning=m.get("reasoning", ""),
        )
        for m in raw_mappings
    ]

    accepted, quarantined = filter_mappings(mappings, threshold)
    stats = score_stats(mappings)
    logger.info(
        "Schema alignment complete",
        extra={"stats": stats, "accepted": len(accepted), "quarantined": len(quarantined)},
    )
    return accepted, quarantined


async def align_graph(
    graph: Graph,
    tenant_id: str,
) -> tuple[Graph, int]:
    """
    Align predicates in an rdflib Graph to FIBO properties.

    Returns (aligned_graph, quarantined_count).
    This is a best-effort transformation; URIs with high confidence
    are rewritten; others are left as-is.
    """
    # Extract unique predicates for alignment
    predicates = list({str(p) for _, p, _ in graph})
    fields = [{"name": p.split("/")[-1].split("#")[-1], "type": "uri", "description": p} for p in predicates[:30]]

    if not fields:
        return graph, 0

    accepted, quarantined = await align_fields(fields)
    mapping = {m.source_field: m.target_property for m in accepted}

    # Rewrite graph with aligned predicates
    new_graph = Graph()
    for prefix, namespace in graph.namespaces():
        new_graph.bind(prefix, namespace)

    quarantined_triples = 0
    for s, p, o in graph:
        p_local = str(p).split("/")[-1].split("#")[-1]
        if p_local in mapping:
            new_graph.add((s, URIRef(mapping[p_local]), o))
        else:
            # Check if full URI was quarantined
            is_quarantined = str(p) in {m.source_field for m in quarantined}
            if not is_quarantined:
                new_graph.add((s, p, o))
            else:
                quarantined_triples += 1

    return new_graph, quarantined_triples


async def _call_llm(prompt: str, settings) -> list[dict]:
    """Call LLM API and parse JSON response."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.LLM_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        # Handle both array and {mappings: [...]} formats
        if isinstance(parsed, list):
            return parsed
        return parsed.get("mappings", parsed.get("fields", []))
