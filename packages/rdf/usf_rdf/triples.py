"""Triple dataclass and batch insert helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import XSD


RDFNode = URIRef | Literal | BNode


@dataclass
class Triple:
    subject: RDFNode
    predicate: URIRef
    obj: RDFNode
    graph: str | None = None  # named graph URI, None = default graph

    # RDF-star annotation metadata (optional)
    annotations: dict[str, Any] = field(default_factory=dict)

    def to_tuple(self) -> tuple[RDFNode, URIRef, RDFNode]:
        return (self.subject, self.predicate, self.obj)


def triples_to_graph(triples: list[Triple]) -> Graph:
    """Convert a list of Triples into an rdflib Graph."""
    g = Graph()
    for t in triples:
        g.add(t.to_tuple())
    return g


def triples_to_turtle(triples: list[Triple], prefixes: dict[str, str] | None = None) -> str:
    """Serialise triples as Turtle string."""
    g = triples_to_graph(triples)
    if prefixes:
        for prefix, uri in prefixes.items():
            g.bind(prefix, uri)
    return g.serialize(format="turtle")


def batch_to_sparql_update(
    triples: list[Triple],
    graph_uri: str,
) -> str:
    """Build a SPARQL INSERT DATA statement for a named graph."""
    lines = [f"INSERT DATA {{ GRAPH <{graph_uri}> {{"]
    for t in triples:
        s = _node_to_sparql(t.subject)
        p = _node_to_sparql(t.predicate)
        o = _node_to_sparql(t.obj)
        lines.append(f"  {s} {p} {o} .")
    lines.append("} }")
    return "\n".join(lines)


def _node_to_sparql(node: RDFNode) -> str:
    if isinstance(node, URIRef):
        return f"<{node}>"
    if isinstance(node, Literal):
        if node.datatype:
            return f'"{node}"^^<{node.datatype}>'
        if node.language:
            return f'"{node}"@{node.language}'
        return f'"{node}"'
    # BNode
    return f"_:{node}"
