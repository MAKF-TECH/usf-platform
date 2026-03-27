"""OWL loader — load OWL files into named graphs with owl:imports resolution."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from rdflib import Graph, URIRef, OWL
from loguru import logger


class OWLLoader:
    """Load OWL 2 ontology files into rdflib Graphs with imports resolution."""

    def __init__(
        self,
        catalog: dict[str, str] | None = None,
        fetch: Callable[[str], bytes] | None = None,
    ) -> None:
        """
        catalog: optional IRI → local path overrides (avoid network fetch)
        fetch: optional function(iri) → bytes for custom HTTP fetching
        """
        self._catalog: dict[str, str] = catalog or {}
        self._fetch = fetch
        self._loaded: set[str] = set()

    def load(self, iri_or_path: str, format: str = "turtle") -> Graph:
        """Load an OWL file and recursively resolve owl:imports."""
        g = Graph()
        self._load_recursive(g, iri_or_path, format)
        return g

    def _load_recursive(self, g: Graph, iri_or_path: str, fmt: str) -> None:
        if iri_or_path in self._loaded:
            return
        self._loaded.add(iri_or_path)

        local = self._catalog.get(iri_or_path, iri_or_path)
        if Path(local).exists():
            logger.debug("Loading OWL from file", path=local)
            g.parse(local, format=fmt)
        else:
            logger.debug("Loading OWL from IRI", iri=iri_or_path)
            if self._fetch:
                data = self._fetch(iri_or_path)
                g.parse(data=data, format=fmt)
            else:
                g.parse(iri_or_path)

        # Follow owl:imports
        imports = list(g.objects(predicate=OWL.imports))
        for imp in imports:
            self._load_recursive(g, str(imp), fmt)

    def to_turtle(self, g: Graph) -> str:
        return g.serialize(format="turtle")
