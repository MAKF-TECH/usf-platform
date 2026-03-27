"""Confidence filter for LangExtract extraction results.

Rules:
1. Extractions where char_interval is None → QUARANTINE (ungrounded)
2. Extractions with confidence_score < threshold → QUARANTINE (low confidence)
3. All others → PASS

Quarantined items are returned with a human-readable reason for audit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple
from loguru import logger

from .langextract_runner import ExtractionResult

# Default confidence threshold — can be overridden per pipeline run
DEFAULT_CONFIDENCE_THRESHOLD = 0.5


class FilterDecision(str, Enum):
    PASS = "PASS"
    QUARANTINE = "QUARANTINE"


@dataclass
class FilterResult:
    """Decision for a single extraction."""

    extraction: ExtractionResult
    decision: FilterDecision
    reason: str | None = None  # Populated when QUARANTINE


class QuarantineRecord(NamedTuple):
    extraction: ExtractionResult
    reason: str
    job_id: str | None


class ConfidenceFilter:
    """Filter extraction results by grounding and confidence.

    Usage:
        flt = ConfidenceFilter(threshold=0.5)
        passed, quarantined = flt.filter(extractions, job_id="job-123")
    """

    def __init__(self, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> None:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError(f"confidence_threshold must be in [0, 1], got {confidence_threshold}")
        self._threshold = confidence_threshold

    def filter(
        self,
        extractions: list[ExtractionResult],
        job_id: str | None = None,
    ) -> tuple[list[ExtractionResult], list[QuarantineRecord]]:
        """Split extractions into passed and quarantined sets.

        Args:
            extractions: Raw output from LangExtractRunner.
            job_id: Optional job ID for quarantine audit records.

        Returns:
            (passed, quarantined) — passed are safe to insert into KG.
        """
        passed: list[ExtractionResult] = []
        quarantined: list[QuarantineRecord] = []

        for ext in extractions:
            result = self._evaluate(ext)
            if result.decision == FilterDecision.PASS:
                passed.append(ext)
            else:
                reason = result.reason or "unknown"
                quarantined.append(
                    QuarantineRecord(
                        extraction=ext,
                        reason=reason,
                        job_id=job_id,
                    )
                )

        logger.info(
            "Confidence filter applied",
            total=len(extractions),
            passed=len(passed),
            quarantined=len(quarantined),
            threshold=self._threshold,
            job_id=job_id,
        )

        if quarantined:
            for q in quarantined:
                logger.debug(
                    "Quarantined extraction",
                    text_span=q.extraction.text_span[:80],
                    reason=q.reason,
                    char_interval=q.extraction.char_interval,
                    confidence=q.extraction.confidence_score,
                )

        return passed, quarantined

    def _evaluate(self, ext: ExtractionResult) -> FilterResult:
        """Evaluate a single extraction against filter rules."""
        # Rule 1: grounding check
        if ext.char_interval is None:
            return FilterResult(
                extraction=ext,
                decision=FilterDecision.QUARANTINE,
                reason=(
                    "ungrounded: char_interval is None — "
                    "LLM did not produce a verifiable text span"
                ),
            )

        # Rule 2: char_interval sanity check
        start, end = ext.char_interval
        if start < 0 or end <= start:
            return FilterResult(
                extraction=ext,
                decision=FilterDecision.QUARANTINE,
                reason=f"invalid char_interval ({start}, {end}) — negative or zero-length span",
            )

        # Rule 3: confidence threshold
        if ext.confidence_score < self._threshold:
            return FilterResult(
                extraction=ext,
                decision=FilterDecision.QUARANTINE,
                reason=(
                    f"low confidence: {ext.confidence_score:.3f} "
                    f"< threshold {self._threshold:.3f}"
                ),
            )

        return FilterResult(extraction=ext, decision=FilterDecision.PASS)
