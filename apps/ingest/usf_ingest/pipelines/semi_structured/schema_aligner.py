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


# ---------------------------------------------------------------------------
# Public API — align_schema (TASK 4)
# ---------------------------------------------------------------------------

from dataclasses import dataclass
from enum import Enum


class MatchType(str, Enum):
    EXACT = "exact"
    EMBEDDING = "embedding"
    LLM = "llm"
    UNMATCHED = "unmatched"


@dataclass
class FieldAlignment:
    field: str
    ontology_property: str | None
    confidence: float
    match_type: MatchType


# Module-level registry of known property labels per ontology module.
# These are used for exact-match and simple substring matching before
# falling back to embeddings or LLM.
_ONTOLOGY_PROPERTY_LABELS: dict[str, dict[str, str]] = {
    "fhir": {
        "patient_id": "fhir:identifier",
        "identifier": "fhir:identifier",
        "name": "fhir:name",
        "birth_date": "fhir:birthDate",
        "birthdate": "fhir:birthDate",
        "dob": "fhir:birthDate",
        "date_of_birth": "fhir:birthDate",
        "gender": "fhir:gender",
        "sex": "fhir:gender",
        "status": "fhir:status",
        "code": "fhir:code",
        "subject": "fhir:subject",
        "period": "fhir:period",
        "admission_date": "fhir:period",
        "discharge_date": "fhir:period",
    },
    "iec-cim": {
        "mrid": "cim:IdentifiedObject.mRID",
        "m_rid": "cim:IdentifiedObject.mRID",
        "name": "cim:IdentifiedObject.name",
        "measurement_type": "cim:Measurement.measurementType",
        "measurementtype": "cim:Measurement.measurementType",
        "unit_symbol": "cim:Measurement.unitSymbol",
        "unitsymbol": "cim:Measurement.unitSymbol",
        "in_service": "cim:Equipment.inService",
        "voltage_level": "cim:ConductingEquipment.BaseVoltage",
    },
    "rami40": {
        "asset_id": "aas:Identifiable.id",
        "id": "aas:Identifiable.id",
        "id_short": "aas:Referable.idShort",
        "idshort": "aas:Referable.idShort",
        "global_asset_id": "aas:AssetInformation.globalAssetId",
        "asset_kind": "aas:AssetInformation.assetKind",
        "semantic_id": "aas:HasSemantics.semanticId",
    },
    "fibo": {
        "counterparty": "fibo:Counterparty",
        "exposure": "fibo:CreditExposure",
        "transaction": "fibo:Transaction",
        "currency": "fibo:Currency",
        "amount": "fibo:MonetaryAmount",
    },
}

_FEW_SHOT_EXAMPLES = """
Examples of field → ontology property mappings:

fhir module:
  patient_id → fhir:identifier (confidence: 0.95)
  date_of_birth → fhir:birthDate (confidence: 0.98)
  admission_ts → fhir:period (confidence: 0.72)

iec-cim module:
  asset_uuid → cim:IdentifiedObject.mRID (confidence: 0.85)
  power_kw → cim:Measurement.measurementType (confidence: 0.60)

rami40 module:
  asset_short_id → aas:Referable.idShort (confidence: 0.90)
""".strip()


async def align_schema(
    fields: list[str],
    ontology_module: str,
    llm_client,
    confidence_threshold: float = 0.7,
) -> list[FieldAlignment]:
    """
    Map source field names to ontology property CURIEs with confidence scores.

    Strategy (in order):
    1. Exact match against known property labels for the ontology module.
    2. Normalised (lowercase, strip underscores) label match.
    3. LLM fallback with few-shot examples for remaining unmatched fields.

    Args:
        fields: Raw column/field names from the source dataset.
        ontology_module: One of 'fhir', 'iec-cim', 'rami40', 'fibo', etc.
        llm_client: Any object with an async ``complete(prompt: str) -> str`` method.
        confidence_threshold: Mappings below this score are still returned
            but marked with MatchType.LLM / MatchType.UNMATCHED — callers
            may quarantine them.

    Returns:
        List of FieldAlignment, one per input field, ordered by input order.
    """
    label_map: dict[str, str] = _ONTOLOGY_PROPERTY_LABELS.get(ontology_module, {})
    results: list[FieldAlignment] = []
    llm_fields: list[str] = []

    for field in fields:
        normalised = field.lower().replace("-", "_").strip()

        # 1. Exact match
        if normalised in label_map:
            results.append(FieldAlignment(
                field=field,
                ontology_property=label_map[normalised],
                confidence=0.95,
                match_type=MatchType.EXACT,
            ))
            continue

        # 2. Partial / normalised match (strip underscores)
        compact = normalised.replace("_", "")
        matched = None
        for label, uri in label_map.items():
            if compact == label.replace("_", ""):
                matched = uri
                break
        if matched:
            results.append(FieldAlignment(
                field=field,
                ontology_property=matched,
                confidence=0.80,
                match_type=MatchType.EMBEDDING,
            ))
            continue

        # 3. Needs LLM
        llm_fields.append(field)
        # Placeholder — will be filled after LLM batch call
        results.append(FieldAlignment(
            field=field,
            ontology_property=None,
            confidence=0.0,
            match_type=MatchType.UNMATCHED,
        ))

    # Batch LLM call for all unmatched fields
    if llm_fields:
        llm_results = await _llm_align(llm_fields, ontology_module, llm_client)
        llm_map = {r.field: r for r in llm_results}
        # Patch placeholder entries
        for i, alignment in enumerate(results):
            if alignment.field in llm_map:
                results[i] = llm_map[alignment.field]

    logger.info(
        "align_schema complete",
        extra={
            "ontology_module": ontology_module,
            "total": len(fields),
            "exact": sum(1 for r in results if r.match_type == MatchType.EXACT),
            "embedding": sum(1 for r in results if r.match_type == MatchType.EMBEDDING),
            "llm": sum(1 for r in results if r.match_type == MatchType.LLM),
            "unmatched": sum(1 for r in results if r.match_type == MatchType.UNMATCHED),
        },
    )
    return results


async def _llm_align(
    fields: list[str],
    ontology_module: str,
    llm_client,
) -> list[FieldAlignment]:
    """Call LLM to align a batch of fields to ontology properties."""
    prompt = f"""You are an ontology alignment expert for the {ontology_module} ontology.

{_FEW_SHOT_EXAMPLES}

Map each of these source field names to the most appropriate {ontology_module} property CURIE.
Return a JSON array with objects: {{field, ontology_property, confidence (0-1)}}.
If no mapping exists, use null for ontology_property and confidence 0.

Fields to map:
{json.dumps(fields, indent=2)}

Return ONLY a valid JSON array, no markdown."""

    try:
        raw = await llm_client.complete(prompt)
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(parsed, list):
            parsed = parsed.get("mappings", [])

        return [
            FieldAlignment(
                field=item["field"],
                ontology_property=item.get("ontology_property"),
                confidence=float(item.get("confidence", 0.0)),
                match_type=MatchType.LLM if item.get("ontology_property") else MatchType.UNMATCHED,
            )
            for item in parsed
            if item.get("field") in fields
        ]
    except Exception as exc:
        logger.warning("LLM align_schema failed, all fields unmatched", error=str(exc))
        return [
            FieldAlignment(field=f, ontology_property=None, confidence=0.0, match_type=MatchType.UNMATCHED)
            for f in fields
        ]
