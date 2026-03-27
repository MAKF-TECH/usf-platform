"""R2RML generator — SDL entity fields → R2RML mapping document."""
from __future__ import annotations

from rdflib import Graph, URIRef, Literal, Namespace, BNode
from rdflib.namespace import RDF, XSD

RR = Namespace("http://www.w3.org/ns/r2rml#")
USF = Namespace("https://usf.makf.tech/ontology/")

_XSD_MAP = {
    "string": "xsd:string",
    "integer": "xsd:integer",
    "decimal": "xsd:decimal",
    "boolean": "xsd:boolean",
    "datetime": "xsd:dateTime",
    "date": "xsd:date",
    "float": "xsd:float",
}


def generate_r2rml(sdl: dict, table_map: dict[str, str] | None = None) -> str:
    """
    Generate an R2RML mapping document from SDL entity definitions.
    table_map: {EntityName: "sql_table_name"}
    Returns Turtle string.
    """
    g = Graph()
    g.bind("rr", RR)
    g.bind("usf", USF)
    g.bind("xsd", XSD)

    ns = Namespace(sdl.get("namespace", str(USF)))
    g.bind("ns", ns)

    table_map = table_map or {}

    for entity in sdl.get("entities", []):
        entity_name = entity["name"]
        table = table_map.get(entity_name, entity_name.lower())
        class_iri = URIRef(ns + entity_name)
        fibo_class = entity.get("fibo_class")

        # TriplesMap
        map_node = URIRef(f"https://usf.makf.tech/r2rml/{entity_name}Map")
        g.add((map_node, RDF.type, RR.TriplesMap))

        # LogicalTable
        logical_table = BNode()
        g.add((map_node, RR.logicalTable, logical_table))
        g.add((logical_table, RR.tableName, Literal(table)))

        # SubjectMap — use first field ending in "id" or "Id" as IRI template
        id_field = next(
            (f["name"] for f in entity.get("fields", []) if f["name"].lower().endswith("id")),
            "id",
        )
        subject_map = BNode()
        g.add((map_node, RR.subjectMap, subject_map))
        g.add((subject_map, RR.template, Literal(f"{ns}{entity_name}/{{{id_field}}}")))
        g.add((subject_map, RR.termType, RR.IRI))
        g.add((subject_map, RR["class"], class_iri))
        if fibo_class:
            g.add((subject_map, RR["class"], URIRef(fibo_class)))

        # PredicateObjectMaps
        for field in entity.get("fields", []):
            field_name = field["name"]
            fibo_prop = field.get("fibo_property", str(ns) + entity_name + "_" + field_name)
            field_type = field.get("type", "string")

            pom = BNode()
            g.add((map_node, RR.predicateObjectMap, pom))

            pred_map = BNode()
            g.add((pom, RR.predicateMap, pred_map))
            g.add((pred_map, RR.constant, URIRef(fibo_prop)))

            obj_map = BNode()
            g.add((pom, RR.objectMap, obj_map))

            if field_type.startswith("ref("):
                target_name = field_type[4:-1]
                target_table = table_map.get(target_name, target_name.lower())
                g.add((obj_map, RR.template, Literal(f"{ns}{target_name}/{{{field_name}}}")))
                g.add((obj_map, RR.termType, RR.IRI))
            else:
                g.add((obj_map, RR.column, Literal(field_name)))
                xsd_type = _XSD_MAP.get(field_type, "xsd:string")
                g.add((obj_map, RR.datatype, URIRef(f"http://www.w3.org/2001/XMLSchema#{xsd_type.split(':')[1]}")))

    return g.serialize(format="turtle")
