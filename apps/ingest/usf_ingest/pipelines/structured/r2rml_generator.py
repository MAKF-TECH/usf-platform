from __future__ import annotations

"""R2RML mapping generator.

Takes introspected schema + FIBO class hints → generates R2RML Turtle document.
"""

from typing import Any

from loguru import logger
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

R2RML = Namespace("http://www.w3.org/ns/r2rml#")
RR = R2RML  # alias
FIBO_FND = Namespace("https://spec.edmcouncil.org/fibo/ontology/FND/")
FIBO_FBC = Namespace("https://spec.edmcouncil.org/fibo/ontology/FBC/")
USF = Namespace("https://usf.platform/ontology/")

# ── Default FIBO type hints per semantic category ─────────────────────────────

SEMANTIC_TO_FIBO_CLASS: dict[str, str] = {
    "financial_institution": "https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/FinancialServicesEntities/CommercialBank",
    "account_identifier": "https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/ClientsAndAccounts/Account",
    "monetary_amount": "https://spec.edmcouncil.org/fibo/ontology/FND/Accounting/CurrencyAmount/MonetaryAmount",
    "currency_code": "https://spec.edmcouncil.org/fibo/ontology/FND/Accounting/ISO4217-CurrencyCodes/Currency",
    "boolean_flag": str(XSD.boolean),
}


def generate_r2rml(
    table_name: str,
    schema_info: dict[str, Any],
    db_connection: str,
    base_uri: str = "https://usf.platform/resource/",
    fibo_hints: dict[str, str] | None = None,
) -> str:
    """
    Generate an R2RML Turtle mapping document for a single table.

    Args:
        table_name: The SQL table name.
        schema_info: Output from schema_introspect.introspect_postgres for this table.
        db_connection: JDBC-style connection URL (for R2RML logical table).
        base_uri: Base URI for generated resource IRIs.
        fibo_hints: Optional {column_name: fibo_class_uri} overrides.

    Returns:
        R2RML mapping as Turtle string.
    """
    from usf_ingest.pipelines.structured.schema_introspect import infer_column_semantics

    g = Graph()
    g.bind("rr", R2RML)
    g.bind("rdf", RDF)
    g.bind("xsd", XSD)
    g.bind("fibo-fnd", FIBO_FND)
    g.bind("fibo-fbc", FIBO_FBC)
    g.bind("usf", USF)

    map_node = URIRef(f"{base_uri}mapping/{table_name}")
    logical_table = URIRef(f"{base_uri}mapping/{table_name}/logicalTable")
    subject_map = URIRef(f"{base_uri}mapping/{table_name}/subjectMap")

    # TriplesMap
    g.add((map_node, RDF.type, RR.TriplesMap))
    g.add((map_node, RR.logicalTable, logical_table))
    g.add((logical_table, RR.tableName, Literal(table_name)))
    g.add((map_node, RR.subjectMap, subject_map))

    # Subject: use primary key columns
    pks = schema_info.get("primary_keys", [])
    pk_template = "/".join([f"{{{pk}}}" for pk in pks]) if pks else "{rownum}"
    g.add((subject_map, RR.template, Literal(f"{base_uri}{table_name}/{pk_template}")))
    g.add((subject_map, RR["class"], USF[table_name.title()]))

    # Predicate-object maps per column
    columns: list[dict] = schema_info.get("columns", [])
    hints = fibo_hints or {}

    for col in columns:
        col_name = col["name"]
        col_type = col["type"]
        semantic = infer_column_semantics(col_name, col_type)
        fibo_class = hints.get(col_name) or SEMANTIC_TO_FIBO_CLASS.get(semantic)

        po_node = URIRef(f"{base_uri}mapping/{table_name}/po/{col_name}")
        pred_node = URIRef(f"{base_uri}mapping/{table_name}/pred/{col_name}")
        obj_node = URIRef(f"{base_uri}mapping/{table_name}/obj/{col_name}")

        g.add((map_node, RR.predicateObjectMap, po_node))
        g.add((po_node, RR.predicateMap, pred_node))
        g.add((po_node, RR.objectMap, obj_node))

        # Map to FIBO property if available, else usf: property
        if fibo_class:
            g.add((pred_node, RR.constant, URIRef(fibo_class)))
        else:
            g.add((pred_node, RR.constant, USF[col_name]))

        g.add((obj_node, RR.column, Literal(col_name)))
        xsd_type = _sql_type_to_xsd(col_type)
        if xsd_type:
            g.add((obj_node, RR.datatype, xsd_type))

    turtle = g.serialize(format="turtle")
    logger.info(f"Generated R2RML for {table_name}: {len(g)} triples")
    return turtle


def _sql_type_to_xsd(sql_type: str) -> URIRef | None:
    t = sql_type.lower()
    if any(k in t for k in ("int", "serial", "bigint", "smallint")):
        return XSD.integer
    if any(k in t for k in ("float", "double", "numeric", "decimal", "real")):
        return XSD.decimal
    if any(k in t for k in ("bool",)):
        return XSD.boolean
    if any(k in t for k in ("timestamp", "datetime")):
        return XSD.dateTime
    if any(k in t for k in ("date",)):
        return XSD.date
    return None
