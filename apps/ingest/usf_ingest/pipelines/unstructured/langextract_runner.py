"""LangExtract orchestration for ontology-guided entity extraction.

Accepts document text + ontology_module, loads few-shot examples,
configures the LLM backend, and runs multi-pass extraction.

Every ExtractionResult carries:
  - char_interval: (start, end) tuple in the source text — None = ungrounded
  - confidence_score: 0.0–1.0 (LangExtract extraction confidence)
  - model_id: which LLM produced this extraction
  - ontology_class: FIBO/FHIR/CIM class IRI string
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from loguru import logger

# Base path to few-shot packages — relative to repo root at runtime
_ONTOLOGIES_BASE = Path(__file__).parents[7] / "packages" / "ontologies"

# Allow override via env var for containerised deployments
import os
_ONTOLOGIES_BASE = Path(os.environ.get("USF_ONTOLOGIES_PATH", str(_ONTOLOGIES_BASE)))


@dataclass
class ExtractionResult:
    """A single extracted entity or relationship from a document."""

    extraction_type: str        # e.g. "LegalEntity", "Account"
    text_span: str              # Exact text from source
    ontology_class: str         # FIBO/FHIR IRI or short form
    attributes: dict[str, Any]  # Domain-specific attributes
    char_interval: tuple[int, int] | None  # (start, end) in source text
    confidence_score: float     # 0.0 – 1.0
    model_id: str               # e.g. "gemini-2.5-flash"
    chunk_index: int | None = None
    raw: Any = field(default=None, repr=False)  # Original LangExtract object


def _load_few_shot_examples(module: str, entity_type: str) -> list[Any]:
    """Load few-shot JSON for a given ontology module + entity type.

    Looks up: packages/ontologies/{module}/few_shot/{entity_type}.json
    Returns a list of lx.data.ExampleData instances.
    """
    few_shot_path = _ONTOLOGIES_BASE / module / "few_shot" / f"{entity_type}.json"
    if not few_shot_path.exists():
        logger.warning(
            "Few-shot file not found, using empty examples",
            path=str(few_shot_path),
        )
        return []

    try:
        import langextract as lx

        raw: list[dict] = json.loads(few_shot_path.read_text())
        examples = []
        for item in raw:
            extractions = [
                lx.data.Extraction(
                    extraction_type=e["class"],
                    text=e["text"],
                    attributes=e.get("attributes", {}),
                )
                for e in item.get("extractions", [])
            ]
            examples.append(
                lx.data.ExampleData(
                    text=item["text"],
                    extractions=extractions,
                )
            )
        return examples
    except ImportError as exc:
        raise RuntimeError(
            "langextract is not installed. Add langextract to pyproject.toml."
        ) from exc


def _load_all_few_shot_examples(module: str) -> list[Any]:
    """Load all few-shot files for an ontology module."""
    few_shot_dir = _ONTOLOGIES_BASE / module / "few_shot"
    if not few_shot_dir.exists():
        logger.warning("Few-shot directory not found", path=str(few_shot_dir))
        return []

    all_examples = []
    for json_file in sorted(few_shot_dir.glob("*.json")):
        entity_type = json_file.stem
        all_examples.extend(_load_few_shot_examples(module, entity_type))

    logger.debug(
        "Loaded few-shot examples",
        module=module,
        total=len(all_examples),
        files=len(list(few_shot_dir.glob("*.json"))),
    )
    return all_examples


def _build_prompt(module: str) -> str:
    """Build an ontology-aware extraction prompt."""
    prompts = {
        "fibo": (
            "Extract financial entities from the text. "
            "Focus on: legal entities (banks, companies, counterparties), "
            "financial accounts (credit agreements, deposits, loans), "
            "transactions (payments, transfers, trades), and monetary amounts. "
            "Map each extraction to its FIBO ontology class. "
            "Use exact text spans — do not paraphrase or normalise the text."
        ),
        "fhir": (
            "Extract healthcare entities from the clinical text. "
            "Focus on: patients, observations (measurements, diagnoses), "
            "medications (drugs, dosages, prescriptions), and clinical procedures. "
            "Map each extraction to its FHIR resource type. "
            "Use exact text spans — do not paraphrase."
        ),
        "cim": (
            "Extract energy/utility entities from the document. "
            "Focus on: equipment, substations, power lines, metering points, "
            "operational limits, and fault events. "
            "Map each extraction to the IEC CIM class. "
            "Use exact text spans — do not paraphrase."
        ),
    }
    return prompts.get(
        module,
        (
            f"Extract domain entities from the text guided by the {module} ontology. "
            "Use exact text spans — do not paraphrase."
        ),
    )


def _select_model_id(cfg: dict[str, Any]) -> str:
    """Select model_id based on config LLM provider."""
    provider = cfg.get("llm_provider", "gemini").lower()
    if provider == "gemini":
        return cfg.get("gemini_model", "gemini-2.5-flash")
    if provider == "openai":
        return cfg.get("openai_model", "gpt-4o")
    if provider == "ollama":
        base = cfg.get("ollama_base_url", "http://localhost:11434")
        model = cfg.get("ollama_model", "llama3")
        return f"ollama/{model}@{base}"
    return "gemini-2.5-flash"


class LangExtractRunner:
    """Orchestrate LangExtract extraction against an ontology module.

    Usage:
        runner = LangExtractRunner(config={"llm_provider": "gemini"})
        results = await runner.extract(text, ontology_module="fibo")
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        extraction_passes: int = 3,
        max_workers: int = 10,
    ) -> None:
        self._config: dict[str, Any] = config or {}
        self._extraction_passes = extraction_passes
        self._max_workers = max_workers

    async def extract(
        self,
        text: str,
        ontology_module: str = "fibo",
        chunk_index: int | None = None,
    ) -> list[ExtractionResult]:
        """Extract entities from text using LangExtract.

        Args:
            text: Source text (one chunk or full document).
            ontology_module: Ontology module name, e.g. "fibo", "fhir".
            chunk_index: Optional chunk index for traceability.

        Returns:
            List of ExtractionResult with char_interval + confidence_score.
        """
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None, self._extract_sync, text, ontology_module, chunk_index
        )

    def _extract_sync(
        self,
        text: str,
        ontology_module: str,
        chunk_index: int | None,
    ) -> list[ExtractionResult]:
        try:
            import langextract as lx
        except ImportError as exc:
            raise RuntimeError(
                "langextract is not installed. Add langextract to pyproject.toml."
            ) from exc

        model_id = _select_model_id(self._config)
        examples = _load_all_few_shot_examples(ontology_module)
        prompt = _build_prompt(ontology_module)

        logger.info(
            "Running LangExtract",
            module=ontology_module,
            model_id=model_id,
            text_len=len(text),
            examples=len(examples),
            passes=self._extraction_passes,
        )

        # Configure API key / base URL per provider
        self._configure_llm_env(model_id)

        raw_result = lx.extract(
            text_or_documents=text,
            prompt_description=prompt,
            examples=examples if examples else None,
            model_id=model_id,
            extraction_passes=self._extraction_passes,
            max_workers=self._max_workers,
        )

        results = self._parse_lx_result(raw_result, model_id, chunk_index)

        logger.info(
            "LangExtract complete",
            total=len(results),
            grounded=sum(1 for r in results if r.char_interval is not None),
            ungrounded=sum(1 for r in results if r.char_interval is None),
        )
        return results

    def _configure_llm_env(self, model_id: str) -> None:
        """Set required env vars for the selected LLM backend."""
        import os

        provider = self._config.get("llm_provider", "gemini").lower()
        if provider == "gemini":
            api_key = self._config.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
            if api_key:
                os.environ["GOOGLE_API_KEY"] = api_key
        elif provider == "openai":
            api_key = self._config.get("openai_api_key") or os.environ.get("OPENAI_API_KEY", "")
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
        # Ollama: no API key needed, uses base URL in model_id string

    def _parse_lx_result(
        self,
        raw_result: Any,
        model_id: str,
        chunk_index: int | None,
    ) -> list[ExtractionResult]:
        """Convert LangExtract output to ExtractionResult list."""
        results: list[ExtractionResult] = []

        # LangExtract returns an ExtractionResult object with .extractions list
        extractions = getattr(raw_result, "extractions", []) or []

        for ext in extractions:
            # char_interval: LangExtract provides (start, end) offsets
            char_interval: tuple[int, int] | None = None
            if hasattr(ext, "char_interval") and ext.char_interval is not None:
                ci = ext.char_interval
                if isinstance(ci, (list, tuple)) and len(ci) == 2:
                    char_interval = (int(ci[0]), int(ci[1]))

            # Confidence: LangExtract may provide extraction confidence
            confidence = float(getattr(ext, "confidence", 1.0) or 1.0)

            # Ontology class: prefer attributes["class"] or extraction_type
            attributes: dict = getattr(ext, "attributes", {}) or {}
            ontology_class = (
                attributes.pop("class", None)
                or attributes.get("fibo_class")
                or attributes.get("fhir_class")
                or getattr(ext, "extraction_type", "Unknown")
            )

            results.append(
                ExtractionResult(
                    extraction_type=getattr(ext, "extraction_type", "Unknown"),
                    text_span=getattr(ext, "text", ""),
                    ontology_class=str(ontology_class),
                    attributes=attributes,
                    char_interval=char_interval,
                    confidence_score=confidence,
                    model_id=model_id,
                    chunk_index=chunk_index,
                    raw=ext,
                )
            )

        return results
