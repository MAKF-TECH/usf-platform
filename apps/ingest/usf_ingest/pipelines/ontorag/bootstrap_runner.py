"""OntoRAG bootstrap runner — full pipeline orchestration.

Runs: documents → OntologyExtractor → SKOSAligner → SDLGenerator
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from loguru import logger

from .ontology_extractor import OntologyExtractor, DraftOntology
from .skos_aligner import SKOSAligner, AlignmentMap
from .sdl_generator import SDLGenerator


@dataclass
class OntoRAGConfig:
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    target_ontology_modules: list[str] = field(default_factory=lambda: ["fibo"])
    embedder_api_key: str = ""
    output_path: str = ""
    tenant_id: str = "default"
    domain_hint: str = ""
    max_text_chars: int = 40_000


@dataclass
class OntoRAGResult:
    draft_ontology: DraftOntology | None = None
    alignment_map: AlignmentMap | None = None
    sdl: dict[str, Any] | None = None
    sdl_path: str = ""
    error: str | None = None
    success: bool = True


class OntoRAGRunner:
    """Orchestrate the full OntoRAG bootstrap pipeline.

    Usage:
        runner = OntoRAGRunner(config)
        result = await runner.run(["path/to/doc1.pdf", "path/to/doc2.html"])
    """

    def __init__(self, config: OntoRAGConfig) -> None:
        self._config = config

        llm_cfg = {
            "provider": config.llm_provider,
            "api_key": config.llm_api_key,
            "model": config.llm_model,
        }
        self._extractor = OntologyExtractor(
            llm_config=llm_cfg,
            max_text_chars=config.max_text_chars,
        )
        self._aligner = SKOSAligner(
            target_modules=config.target_ontology_modules,
            embedder_config={"api_key": config.embedder_api_key},
        )
        self._generator = SDLGenerator(output_path=config.output_path or None)

    async def run(
        self,
        document_paths: list[str | Path],
        domain_hint: str | None = None,
    ) -> OntoRAGResult:
        """Run the full OntoRAG bootstrap pipeline.

        Args:
            document_paths: Source documents (PDFs, HTMLs, text files).
            domain_hint: Optional domain context string.

        Returns:
            OntoRAGResult with draft ontology, alignment map, and SDL.
        """
        result = OntoRAGResult()
        hint = domain_hint or self._config.domain_hint

        try:
            logger.info(
                "OntoRAG bootstrap starting",
                documents=len(document_paths),
                modules=self._config.target_ontology_modules,
            )

            # Step 1: Extract ontology skeleton
            logger.info("Step 1/3: Extracting ontology from documents")
            draft = await self._extractor.extract_from_documents(
                document_paths=document_paths,
                domain_hint=hint,
            )
            result.draft_ontology = draft

            # Step 2: Align to industry standards
            logger.info(
                "Step 2/3: SKOS alignment",
                draft_classes=len(draft.classes),
                modules=self._config.target_ontology_modules,
            )
            alignment = await self._aligner.align(draft)
            result.alignment_map = alignment

            # Step 3: Generate SDL YAML
            logger.info("Step 3/3: Generating SDL YAML")
            sdl = self._generator.generate(
                draft_ontology=draft,
                alignment_map=alignment,
                tenant_id=self._config.tenant_id,
                ontology_module=self._config.target_ontology_modules[0],
            )
            result.sdl = sdl
            result.sdl_path = str(self._generator._output_path)
            result.success = True

            logger.info(
                "OntoRAG bootstrap complete",
                classes=len(draft.classes),
                aligned=sum(1 for a in alignment.values() if a.matched_class),
                sdl_entities=len(sdl.get("entities", [])),
                sdl_metrics=len(sdl.get("metrics", [])),
                sdl_path=result.sdl_path,
            )

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error("OntoRAG bootstrap failed", error=str(e), exc_info=True)
            raise

        return result
