"""SHACL validation service — run pySHACL, route violations to quarantine graph."""
from __future__ import annotations

from loguru import logger
from rdflib import Graph, URIRef, Literal

from usf_rdf import SHACLValidator
from usf_rdf.triples import Triple, batch_to_sparql_update

from .qlever import QLeverService
from ..config import settings


class SHACLService:
    """Run SHACL validation and route violations to quarantine named graph."""

    SHACL_VIOLATION_TYPE = "http://www.w3.org/ns/shacl#ValidationResult"
    QUARANTINE_PRED_FOCUS = "http://www.w3.org/ns/shacl#focusNode"
    QUARANTINE_PRED_MSG = "http://www.w3.org/ns/shacl#resultMessage"

    def __init__(self, qlever: QLeverService) -> None:
        self._qlever = qlever
        self._validator = SHACLValidator()

    def load_shapes_turtle(self, turtle: str) -> None:
        self._validator.load_shapes_turtle(turtle)

    async def validate_graph(
        self,
        data_graph: Graph,
        shapes_graph: Graph | None = None,
        quarantine_graph: str | None = None,
    ) -> tuple[bool, list]:
        """
        Validate data_graph. If violations found, insert them into quarantine_graph in QLever.
        Returns (conforms, violations).
        """
        conforms, violations = self._validator.validate(data_graph, shapes_graph)

        if not conforms and violations and quarantine_graph:
            await self._write_quarantine(violations, quarantine_graph)

        return conforms, violations

    async def _write_quarantine(self, violations, quarantine_graph: str) -> None:
        """Write SHACL violations as triples to the quarantine named graph."""
        from rdflib import BNode
        import uuid

        triples: list[Triple] = []
        for v in violations:
            result_node = URIRef(
                f"https://usf.makf.tech/quarantine/result/{uuid.uuid4().hex[:8]}"
            )
            triples.append(
                Triple(
                    subject=result_node,
                    predicate=URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                    obj=URIRef(self.SHACL_VIOLATION_TYPE),
                )
            )
            triples.append(
                Triple(
                    subject=result_node,
                    predicate=URIRef(self.QUARANTINE_PRED_FOCUS),
                    obj=URIRef(v.focus_node) if v.focus_node.startswith("http") else Literal(v.focus_node),
                )
            )
            triples.append(
                Triple(
                    subject=result_node,
                    predicate=URIRef(self.QUARANTINE_PRED_MSG),
                    obj=Literal(v.message),
                )
            )

        await self._qlever.insert_triples(quarantine_graph, triples)
        logger.warning(
            "Violations quarantined",
            graph=quarantine_graph,
            count=len(violations),
        )
