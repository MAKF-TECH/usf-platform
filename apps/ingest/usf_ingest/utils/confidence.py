from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from loguru import logger

DEFAULT_CONFIDENCE_THRESHOLD = 0.75


@dataclass
class FieldMapping:
    source_field: str
    target_property: str
    confidence: float
    reasoning: str = ""
    accepted: bool = False


def filter_mappings(
    mappings: Sequence[FieldMapping],
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> tuple[list[FieldMapping], list[FieldMapping]]:
    accepted, quarantined = [], []
    for m in mappings:
        if m.confidence >= threshold:
            m.accepted = True
            accepted.append(m)
        else:
            quarantined.append(m)
    logger.debug("Confidence filter", extra={"total": len(mappings), "accepted": len(accepted), "threshold": threshold})
    return accepted, quarantined


def score_stats(mappings: Sequence[FieldMapping]) -> dict:
    if not mappings:
        return {"mean": 0.0, "min": 0.0, "max": 0.0, "count": 0}
    scores = [m.confidence for m in mappings]
    return {"mean": round(sum(scores) / len(scores), 4), "min": round(min(scores), 4), "max": round(max(scores), 4), "count": len(scores)}
