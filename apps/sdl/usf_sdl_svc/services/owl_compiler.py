"""OWL 2 QL compiler — SDL entity → OWL axioms using rdflib."""
from __future__ import annotations

from typing import Any

from rdflib import Graph, URIRef, Literal, Namespace, BNode
from rdflib.namespace import OWL, RDF, RDFS, XSD

USF = Namespace("https://usf.makf.tech/ontology/")

_XSD_MAP: dict[str, Any] = {
    "string": XSD.string,
    "integer": XSD.integer,
    "decimal": XSD.decimal,
    "boolean": XSD.boolean,
    "datetime": XSD.dateTime,
    "date": XSD.date,
    "float": XSD.float,
}


def compile_sdl_to_owl(sdl: dict) -> str:
    """
    Convert a parsed SDL document to OWL 2 QL Turtle.
    sdl is the parsed YAML content.
    Returns Turtle string.
    """
    g = Graph()
    ns = Namespace(sdl.get("namespace", str(USF)))
    g.bind("usf", USF)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)
    g.bind("ns", ns)

    # Ontology declaration
    onto_iri = URIRef(sdl.get("namespace", str(USF)).rstrip("/") + "/ontology")
    g.add((onto_iri, RDF.type, OWL.Ontology))

    for entity in sdl.get("entities", []):
        class_iri = URIRef(ns + entity["name"])
        fibo_class = entity.get("fibo_class")

        g.add((class_iri, RDF.type, OWL.Class))
        if entity.get("description"):
            g.add((class_iri, RDFS.comment, Literal(entity["description"])))
        g.add((class_iri, RDFS.label, Literal(entity["name"])))

        if fibo_class:
            g.add((class_iri, OWL.equivalentClass, URIRef(fibo_class)))

        for field in entity.get("fields", []):
            field_iri = URIRef(
                field.get("fibo_property") or str(ns) + entity["name"] + "_" + field["name"]
            )
            field_type = field.get("type", "string")

            if field_type.startswith("ref("):
                # Object property
                target_name = field_type[4:-1]
                target_iri = URIRef(ns + target_name)
                g.add((field_iri, RDF.type, OWL.ObjectProperty))
                g.add((field_iri, RDFS.domain, class_iri))
                g.add((field_iri, RDFS.range, target_iri))
            else:
                # Data property
                g.add((field_iri, RDF.type, OWL.DatatypeProperty))
                g.add((field_iri, RDFS.domain, class_iri))
                xsd_type = _XSD_MAP.get(field_type, XSD.string)
                g.add((field_iri, RDFS.range, xsd_type))

            g.add((field_iri, RDFS.label, Literal(field["name"])))
            if field.get("description"):
                g.add((field_iri, RDFS.comment, Literal(field["description"])))

            if field.get("required"):
                # OWL restriction: minCardinality 1
                restriction = BNode()
                g.add((restriction, RDF.type, OWL.Restriction))
                g.add((restriction, OWL.onProperty, field_iri))
                g.add((restriction, OWL.minCardinality, Literal(1, datatype=XSD.nonNegativeInteger)))
                g.add((class_iri, RDFS.subClassOf, restriction))

    return g.serialize(format="turtle")
