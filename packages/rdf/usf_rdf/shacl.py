"""SHACL validation using pySHACL."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rdflib import Graph
from loguru import logger
import pyshacl


@dataclass
class SHACLViolation:
    focus_node: str
    result_path: str | None
    value: str | None
    source_shape: str | None
    message: str
    severity: str  # sh:Violation | sh:Warning | sh:Info


class SHACLValidator:
    """Validate RDF data against SHACL shapes."""

    def __init__(self, shapes_graph: Graph | None = None) -> None:
        self._shapes: Graph | None = shapes_graph

    def load_shapes_turtle(self, turtle: str) -> None:
        """Load SHACL shapes from Turtle string."""
        g = Graph()
        g.parse(data=turtle, format="turtle")
        if self._shapes is None:
            self._shapes = g
        else:
            self._shapes += g

    def validate(
        self,
        data_graph: Graph,
        shapes_graph: Graph | None = None,
    ) -> tuple[bool, list[SHACLViolation]]:
        """
        Validate data_graph against shapes.
        Returns (conforms, violations).
        """
        shapes = shapes_graph or self._shapes
        if shapes is None:
            raise ValueError("No SHACL shapes loaded")

        conforms, results_graph, _ = pyshacl.validate(
            data_graph,
            shacl_graph=shapes,
            inference="rdfs",
            abort_on_first=False,
            meta_shacl=False,
        )

        violations = _parse_results(results_graph)
        logger.info(
            "SHACL validation complete",
            conforms=conforms,
            violations=len(violations),
        )
        return conforms, violations


def _parse_results(results_graph: Graph) -> list[SHACLViolation]:
    SH = "http://www.w3.org/ns/shacl#"
    violations: list[SHACLViolation] = []

    for result in results_graph.subjects(
        predicate=results_graph.namespace_manager.normalizeUri(f"{SH}focusNode"),
        unique=False,
    ):
        pass  # rely on SPARQL query below for clean parsing

    # Parse via SPARQL over results graph
    q = f"""
    PREFIX sh: <{SH}>
    SELECT ?focus ?path ?value ?shape ?msg ?severity WHERE {{
        ?r a sh:ValidationResult ;
           sh:focusNode ?focus ;
           sh:resultSeverity ?severity .
        OPTIONAL {{ ?r sh:resultPath ?path }}
        OPTIONAL {{ ?r sh:value ?value }}
        OPTIONAL {{ ?r sh:sourceShape ?shape }}
        OPTIONAL {{ ?r sh:resultMessage ?msg }}
    }}
    """
    for row in results_graph.query(q):
        violations.append(
            SHACLViolation(
                focus_node=str(row.focus),
                result_path=str(row.path) if row.path else None,
                value=str(row.value) if row.value else None,
                source_shape=str(row.shape) if row.shape else None,
                message=str(row.msg) if row.msg else "",
                severity=str(row.severity).split("#")[-1],
            )
        )
    return violations
