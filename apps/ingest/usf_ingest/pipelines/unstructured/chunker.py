"""Semantic chunking via chonkie.

Respects sentence/paragraph boundaries.
Returns list[Chunk] with char offsets into the original document text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from loguru import logger


@dataclass
class Chunk:
    """A semantically coherent text segment with source position."""

    text: str
    char_start: int
    char_end: int
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def length(self) -> int:
        return len(self.text)


class SemanticChunker:
    """Chunk document text respecting sentence/paragraph boundaries.

    Uses chonkie's SemanticChunker which groups semantically similar
    sentences together, keeping related ideas in the same chunk.
    Falls back to SentenceChunker if semantic mode is unavailable.

    Design:
    - max_chunk_size: target token budget per chunk (~512 tokens)
    - chunk_overlap: overlap between adjacent chunks (useful for extraction
      that spans chunk boundaries)
    - Char offsets are computed by searching for chunk text in the source.
    """

    def __init__(
        self,
        max_chunk_size: int = 512,
        chunk_overlap: int = 50,
        similarity_threshold: float = 0.5,
        embedding_model: str = "minishlab/potion-base-8M",
    ) -> None:
        self._max_chunk_size = max_chunk_size
        self._chunk_overlap = chunk_overlap
        self._similarity_threshold = similarity_threshold
        self._embedding_model = embedding_model
        self._chunker: Any = None

    def _get_chunker(self) -> Any:
        if self._chunker is None:
            try:
                from chonkie import SemanticChunker as _SemanticChunker

                self._chunker = _SemanticChunker(
                    embedding_model=self._embedding_model,
                    chunk_size=self._max_chunk_size,
                    threshold=self._similarity_threshold,
                )
                logger.debug("Using chonkie SemanticChunker")
            except (ImportError, Exception) as e:
                logger.warning(
                    "SemanticChunker unavailable, falling back to SentenceChunker",
                    error=str(e),
                )
                try:
                    from chonkie import SentenceChunker as _SentenceChunker

                    self._chunker = _SentenceChunker(
                        chunk_size=self._max_chunk_size,
                        chunk_overlap=self._chunk_overlap,
                    )
                except ImportError as exc:
                    raise RuntimeError(
                        "chonkie is not installed. Add chonkie to pyproject.toml."
                    ) from exc
        return self._chunker

    async def chunk(self, text: str) -> list[Chunk]:
        """Split text into semantic chunks with char offsets.

        Args:
            text: Source document text (from DoclingParser.text).

        Returns:
            List of Chunk objects sorted by char_start.
        """
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None, self._chunk_sync, text
        )

    def _chunk_sync(self, text: str) -> list[Chunk]:
        chunker = self._get_chunker()
        raw_chunks = chunker.chunk(text)

        chunks: list[Chunk] = []
        search_offset = 0

        for idx, raw in enumerate(raw_chunks):
            chunk_text: str = raw.text if hasattr(raw, "text") else str(raw)
            if not chunk_text.strip():
                continue

            # Locate chunk in source text to get char offsets
            pos = text.find(chunk_text, search_offset)
            if pos == -1:
                # Fallback: scan from beginning (handles minor whitespace diffs)
                pos = text.find(chunk_text.strip(), 0)
            if pos == -1:
                logger.warning(
                    "Chunk text not found in source, using approximate offset",
                    chunk_index=idx,
                    chunk_preview=chunk_text[:80],
                )
                pos = search_offset

            char_start = pos
            char_end = pos + len(chunk_text)
            search_offset = max(search_offset, char_end - len(chunk_text) // 4)

            chunks.append(
                Chunk(
                    text=chunk_text,
                    char_start=char_start,
                    char_end=char_end,
                    chunk_index=idx,
                    metadata={
                        "token_count": getattr(raw, "token_count", None),
                    },
                )
            )

        logger.info(
            "Chunking complete",
            total_chars=len(text),
            chunks=len(chunks),
            avg_chunk_len=sum(c.length for c in chunks) // max(len(chunks), 1),
        )
        return chunks
