from __future__ import annotations

"""R2RML mapping generator from introspected schema + FIBO class hints."""

from typing import Any

from loguru import logger
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

R2RML = Namespace("http://www.w3.org/ns/r2rml#")
FIBO_FBC = Namespace("https://spec.edmcouncil.org/fibo/ontology/FBC/")
FIBO_FND = Namespace("https://spec.edmcouncil.org/fibo/ontology/FND/")
USF = Namespace("https://usf.platform/ontology/")

SEMANTIC_TO_FIBO_CLASS: dict[str, str] = {
    "financial_institution": "https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/FinancialServicesEntities/CommercialBank",
    "account_identifier": "https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/ClientsAndAccounts/Account",
    "monetary_amount": "https://spec.edmcouncil.org/fibo/ontology/FND/Accounting/CurrencyAmount/MonetaryAmount",
    "currency_code": "https://spec.edmcouncil.org/fibo/ontology/FND/Accounting/ISO4217-CurrencyCodes/Currency",
}


def generate_r2rml(
    table_name: str,
    schema_info: dict[str, Any],
    db_connection: str,
    base_uri: str = "https://usf.platform/resource/",
    fibo_hints: dict[str, str] | None = None,
) -> str:
    from usf_ingest.pipelines.structured.schema_introspect import infer_column_semantics

    g = Graph()
    g.bind("rr", R2RML)
    g.bind("usf", USF)

    map_node = URIRef(f"{base_uri}mapping/{table_name}")
    logical_table = URIRef(f"{base_uri}mapping/{table_name}/logicalTable")
    subject_map = URIRef(f"{base_uri}mapping/{table_name}/subjectMap")

    g.add((map_node, RDF.type, R2RML.TriplesMap))
    g.add((map_node, R2RML.logicalTable, logical_table))
    g.add((logical_table, R2RML.tableName, Literal(table_name)))
    g.add((map_node, R2RML.subjectMap, subject_map))

    pks = schema_info.get("primary_keys", [])
    pk_template = "/".join([f"{{{pk}}}" for pk in pks]) if pks else "{rownum}"
    g.add((subject_map, R2RML.template, Literal(f"{base_uri}{table_name}/{pk_template}")))
    g.add((subject_map, R2RML["class"], USF[table_name.title()]))

    hints = fibo_hints or {}
    for col in schema_info.get("columns", []):
        col_name, col_type = col["name"], col["type"]
        semantic = infer_column_semantics(col_name, col_type)
        fibo_class = hints.get(col_name) or SEMANTIC_TO_FIBO_CLASS.get(semantic)

        po = URIRef(f"{base_uri}mapping/{table_name}/po/{col_name}")
        pred = URIRef(f"{base_uri}mapping/{table_name}/pred/{col_name}")
        obj = URIRef(f"{base_uri}mapping/{table_name}/obj/{col_name}")

        g.add((map_node, R2RML.predicateObjectMap, po))
        g.add((po, R2RML.predicateMap, pred))
        g.add((po, R2RML.objectMap, obj))
        g.add((pred, R2RML.constant, URIRef(fibo_class) if fibo_class else USF[col_name]))
        g.add((obj, R2RML.column, Literal(col_name)))
        xsd_type = _sql_to_xsd(col_type)
        if xsd_type:
            g.add((obj, R2RML.datatype, xsd_type))

    logger.info(f"Generated R2RML for {table_name}: {len(g)} triples")
    return g.serialize(format="turtle")


def _sql_to_xsd(sql_type: str) -> URIRef | None:
    t = sql_type.lower()
    if any(k in t for k in ("int", "serial", "bigint")):
        return XSD.integer
    if any(k in t for k in ("float", "double", "numeric", "decimal", "real")):
        return XSD.decimal
    if "bool" in t:
        return XSD.boolean
    if "timestamp" in t or "datetime" in t:
        return XSD.dateTime
    if t == "date":
        return XSD.date
    return None
