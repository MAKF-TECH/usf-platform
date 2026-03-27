"""PDF/DOCX/HTML parsing via Docling.

Preserves section structure, tables, and headers.
Returns DocumentResult with text + layout metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from loguru import logger


@dataclass
class TableCell:
    row: int
    col: int
    text: str
    row_span: int = 1
    col_span: int = 1


@dataclass
class TableElement:
    caption: str | None
    cells: list[TableCell]
    char_start: int
    char_end: int


@dataclass
class SectionElement:
    heading: str
    level: int  # 1 = H1, 2 = H2, etc.
    char_start: int
    char_end: int


@dataclass
class DocumentResult:
    """Full parsed document with text and structural metadata."""

    source_path: str
    mime_type: str
    text: str  # Full concatenated text (for LangExtract)
    sections: list[SectionElement] = field(default_factory=list)
    tables: list[TableElement] = field(default_factory=list)
    page_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return len(self.text.split())


class DoclingParser:
    """Parse documents using Docling. Supports PDF, DOCX, HTML.

    Docling preserves the full layout tree — headings, paragraphs, tables,
    lists — and serialises everything to a Markdown-compatible text stream
    while also exposing the underlying element positions.
    """

    def __init__(self, ocr_enabled: bool = True, table_mode: str = "accurate") -> None:
        """
        Args:
            ocr_enabled: Enable OCR for scanned PDFs.
            table_mode: Docling table extraction mode ("accurate" | "fast").
        """
        self._ocr_enabled = ocr_enabled
        self._table_mode = table_mode
        self._converter: Any = None

    def _get_converter(self) -> Any:
        """Lazy-init Docling converter (heavy import)."""
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter, PdfPipelineOptions
                from docling.datamodel.pipeline_options import TableFormerMode

                pdf_opts = PdfPipelineOptions()
                pdf_opts.do_ocr = self._ocr_enabled
                pdf_opts.do_table_structure = True
                pdf_opts.table_structure_options.mode = (
                    TableFormerMode.ACCURATE
                    if self._table_mode == "accurate"
                    else TableFormerMode.FAST
                )
                self._converter = DocumentConverter(
                    artifacts_path=None,
                    pipeline_options=pdf_opts,
                )
            except ImportError as exc:
                raise RuntimeError(
                    "docling is not installed. Add docling to pyproject.toml dependencies."
                ) from exc
        return self._converter

    async def parse(self, source: str | Path) -> DocumentResult:
        """Parse a document asynchronously.

        Args:
            source: File path or URL.

        Returns:
            DocumentResult with full text and layout metadata.
        """
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None, self._parse_sync, str(source)
        )

    def _parse_sync(self, source: str) -> DocumentResult:
        """Synchronous Docling parse (runs in thread pool)."""
        logger.info("Parsing document", source=source)
        converter = self._get_converter()

        result = converter.convert(source)
        doc = result.document

        # Build full text — use Docling's markdown export which preserves
        # headings (##), table delimiters, and paragraph breaks.
        full_text = doc.export_to_markdown()

        sections: list[SectionElement] = []
        tables: list[TableElement] = []
        char_offset = 0

        # Walk Docling element tree to collect structural metadata
        for elem in doc.iterate_items():
            elem_text = self._elem_text(elem)
            if not elem_text:
                continue

            # Locate element in the full text
            try:
                idx = full_text.index(elem_text, char_offset)
                char_start = idx
                char_end = idx + len(elem_text)
            except ValueError:
                # Element text not found verbatim (normalised differently)
                char_start = char_offset
                char_end = char_offset + len(elem_text)

            elem_type = type(elem).__name__

            if "SectionHeader" in elem_type or "Title" in elem_type:
                level = getattr(elem, "level", 1) or 1
                sections.append(
                    SectionElement(
                        heading=elem_text.strip(),
                        level=level,
                        char_start=char_start,
                        char_end=char_end,
                    )
                )
            elif "Table" in elem_type:
                cells = self._extract_table_cells(elem)
                tables.append(
                    TableElement(
                        caption=getattr(elem, "caption_text", None),
                        cells=cells,
                        char_start=char_start,
                        char_end=char_end,
                    )
                )

            char_offset = max(char_offset, char_end)

        page_count = getattr(doc, "num_pages", 0) or 0

        mime_type = self._detect_mime(source)

        logger.info(
            "Document parsed",
            source=source,
            pages=page_count,
            sections=len(sections),
            tables=len(tables),
            words=len(full_text.split()),
        )

        return DocumentResult(
            source_path=source,
            mime_type=mime_type,
            text=full_text,
            sections=sections,
            tables=tables,
            page_count=page_count,
            metadata={"docling_version": self._get_docling_version()},
        )

    def _elem_text(self, elem: Any) -> str:
        """Extract plain text from a Docling element."""
        for attr in ("text", "caption_text", "content"):
            val = getattr(elem, attr, None)
            if val and isinstance(val, str):
                return val
        return ""

    def _extract_table_cells(self, table_elem: Any) -> list[TableCell]:
        cells: list[TableCell] = []
        try:
            for cell in table_elem.data.table_cells:
                cells.append(
                    TableCell(
                        row=cell.start_row_offset_idx,
                        col=cell.start_col_offset_idx,
                        text=cell.text,
                        row_span=cell.row_span,
                        col_span=cell.col_span,
                    )
                )
        except AttributeError:
            pass
        return cells

    def _detect_mime(self, source: str) -> str:
        source_lower = source.lower()
        if source_lower.endswith(".pdf"):
            return "application/pdf"
        if source_lower.endswith(".docx"):
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if source_lower.endswith((".html", ".htm")):
            return "text/html"
        return "application/octet-stream"

    def _get_docling_version(self) -> str:
        try:
            import docling
            return getattr(docling, "__version__", "unknown")
        except ImportError:
            return "not-installed"
