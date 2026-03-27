"""Extract an ontology skeleton from a set of documents using an LLM.

OntoRAG step 1 of 3. Produces a DraftOntology with:
  - classes: discovered entity types with properties
  - relationships: directed relationships between entity types
  - hierarchy: inferred class hierarchy (parent → [children])

Based on the OntoRAG paper (Tiwari et al., May 2025):
  "LLM-guided extraction of ontological structure from domain documents."
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from loguru import logger


@dataclass
class DraftClass:
    name: str
    description: str
    properties: dict[str, str]   # {property_name: datatype_hint}
    examples: list[str]           # Example text spans


@dataclass
class DraftRelationship:
    name: str
    from_class: str
    to_class: str
    description: str
    cardinality: str = "many-to-many"  # "one-to-one" | "one-to-many" | "many-to-many"


@dataclass
class DraftOntology:
    """Draft ontology derived from a document set."""

    classes: list[DraftClass] = field(default_factory=list)
    relationships: list[DraftRelationship] = field(default_factory=list)
    hierarchy: dict[str, list[str]] = field(default_factory=dict)  # parent → [children]
    source_documents: list[str] = field(default_factory=list)
    domain_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "classes": [
                {
                    "name": c.name,
                    "description": c.description,
                    "properties": c.properties,
                    "examples": c.examples,
                }
                for c in self.classes
            ],
            "relationships": [
                {
                    "name": r.name,
                    "from": r.from_class,
                    "to": r.to_class,
                    "description": r.description,
                    "cardinality": r.cardinality,
                }
                for r in self.relationships
            ],
            "hierarchy": self.hierarchy,
            "source_documents": self.source_documents,
            "domain_hint": self.domain_hint,
        }


_ONTOLOGY_EXTRACTION_PROMPT = """You are an expert ontology engineer. Analyse the provided text and extract a structured ontology skeleton.

Output a single JSON object with this structure:
{
  "domain": "<one-line domain description>",
  "classes": [
    {
      "name": "<PascalCase class name>",
      "description": "<one-line description>",
      "properties": {"<propName>": "<datatype: string|integer|decimal|boolean|date>"},
      "examples": ["<exact text span 1>", "<exact text span 2>"]
    }
  ],
  "relationships": [
    {
      "name": "<camelCase relationship name>",
      "from": "<ClassName>",
      "to": "<ClassName>",
      "description": "<one-line>",
      "cardinality": "one-to-many"
    }
  ],
  "hierarchy": {
    "<ParentClass>": ["<ChildClass1>", "<ChildClass2>"]
  }
}

Rules:
- Identify 5-15 core entity types from the text
- Properties should be observable attributes (not relationships)
- Numeric properties are valuable for metric derivation
- Infer class hierarchy from context (e.g., CommercialBank is-a LegalEntity)
- Use domain-standard terminology where evident
- Output ONLY the JSON, no prose before or after."""


class OntologyExtractor:
    """Extract ontology skeleton from documents via LLM.

    Uses a single structured LLM call per document batch.
    Aggregates results across documents by merging class definitions.
    """

    def __init__(
        self,
        llm_config: dict[str, Any] | None = None,
        max_text_chars: int = 40_000,  # Roughly 10k tokens
    ) -> None:
        self._llm_config = llm_config or {}
        self._max_text_chars = max_text_chars

    async def extract_from_documents(
        self,
        document_paths: list[str | Path],
        domain_hint: str = "",
    ) -> DraftOntology:
        """Extract ontology from a list of documents.

        Args:
            document_paths: Paths to PDFs, HTMLs, or text files.
            domain_hint: Optional domain context hint for the LLM.

        Returns:
            DraftOntology with merged classes, relationships, hierarchy.
        """
        from ..unstructured.docling_parser import DoclingParser

        parser = DoclingParser()
        all_text_snippets: list[str] = []

        for path in document_paths:
            try:
                doc = await parser.parse(str(path))
                # Take first N chars to stay within LLM context
                snippet = doc.text[: self._max_text_chars // len(document_paths)]
                all_text_snippets.append(snippet)
                logger.debug("Loaded document for ontology extraction", path=str(path))
            except Exception as e:
                logger.warning("Failed to parse document", path=str(path), error=str(e))

        combined_text = "\n\n---\n\n".join(all_text_snippets)
        if not combined_text.strip():
            logger.warning("No text extracted from documents, returning empty ontology")
            return DraftOntology(source_documents=[str(p) for p in document_paths])

        raw = await self._call_llm(combined_text, domain_hint)
        ontology = self._parse_llm_response(raw)
        ontology.source_documents = [str(p) for p in document_paths]
        ontology.domain_hint = domain_hint

        logger.info(
            "Ontology extraction complete",
            classes=len(ontology.classes),
            relationships=len(ontology.relationships),
            hierarchy_roots=len(ontology.hierarchy),
        )
        return ontology

    async def extract_from_text(self, text: str, domain_hint: str = "") -> DraftOntology:
        """Extract ontology from a raw text string."""
        raw = await self._call_llm(text[: self._max_text_chars], domain_hint)
        return self._parse_llm_response(raw)

    async def _call_llm(self, text: str, domain_hint: str) -> str:
        """Call the configured LLM and return raw JSON string."""
        import asyncio

        prompt_text = _ONTOLOGY_EXTRACTION_PROMPT
        if domain_hint:
            prompt_text = f"Domain context: {domain_hint}\n\n" + prompt_text

        return await asyncio.get_event_loop().run_in_executor(
            None, self._call_llm_sync, prompt_text, text
        )

    def _call_llm_sync(self, system_prompt: str, user_text: str) -> str:
        provider = self._llm_config.get("provider", "openai").lower()
        if provider == "openai":
            return self._call_openai(system_prompt, user_text)
        if provider == "gemini":
            return self._call_gemini(system_prompt, user_text)
        if provider == "ollama":
            return self._call_ollama(system_prompt, user_text)
        raise ValueError(f"Unknown LLM provider: {provider}")

    def _call_openai(self, system_prompt: str, user_text: str) -> str:
        import os, httpx

        api_key = self._llm_config.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
        model = self._llm_config.get("model", "gpt-4o")
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_gemini(self, system_prompt: str, user_text: str) -> str:
        import os, httpx

        api_key = self._llm_config.get("api_key") or os.environ.get("GEMINI_API_KEY", "")
        model = self._llm_config.get("model", "gemini-2.5-flash")
        combined = f"{system_prompt}\n\nText to analyse:\n{user_text}"
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        resp = httpx.post(
            url,
            json={
                "contents": [{"parts": [{"text": combined}]}],
                "generationConfig": {"temperature": 0.1},
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

    def _call_ollama(self, system_prompt: str, user_text: str) -> str:
        import httpx

        base_url = self._llm_config.get("base_url", "http://localhost:11434")
        model = self._llm_config.get("model", "llama3")
        resp = httpx.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "system": system_prompt,
                "prompt": user_text,
                "stream": False,
                "format": "json",
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        return resp.json().get("response", "{}")

    def _parse_llm_response(self, raw: str) -> DraftOntology:
        """Parse LLM JSON output into DraftOntology."""
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM ontology response", error=str(e), raw=raw[:500])
            return DraftOntology()

        classes = [
            DraftClass(
                name=c.get("name", "Unknown"),
                description=c.get("description", ""),
                properties=c.get("properties", {}),
                examples=c.get("examples", []),
            )
            for c in data.get("classes", [])
        ]
        relationships = [
            DraftRelationship(
                name=r.get("name", "relatedTo"),
                from_class=r.get("from", ""),
                to_class=r.get("to", ""),
                description=r.get("description", ""),
                cardinality=r.get("cardinality", "many-to-many"),
            )
            for r in data.get("relationships", [])
        ]

        return DraftOntology(
            classes=classes,
            relationships=relationships,
            hierarchy=data.get("hierarchy", {}),
            domain_hint=data.get("domain", ""),
        )
