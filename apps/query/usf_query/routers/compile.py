from __future__ import annotations

from fastapi import APIRouter, HTTPException

from usf_query.models import CompileRequest, CompiledQuery
from usf_query.services.sql_generator import generate_metric_sql

router = APIRouter(prefix="/compile", tags=["compile"])

# Minimal SPARQL template for a metric
_SPARQL_TEMPLATE = """
PREFIX usf: <urn:usf:>
PREFIX fibo: <https://spec.edmcouncil.org/fibo/ontology/>

SELECT ?dimension ?{metric_name}
WHERE {{
  GRAPH <urn:usf:context:{context}> {{
    ?subject a <{ontology_class}> ;
             usf:{measure} ?raw_value .
    OPTIONAL {{ ?subject usf:dimension ?dimension }}
  }}
}}
GROUP BY ?dimension
""".strip()


def _get_metric_definition(metric_name: str, context: str) -> dict:
    """
    Fetch metric definition from SDL layer.
    In production this calls usf-kg or usf-sdl service.
    For now, returns a placeholder structure.
    """
    # TODO: replace with real SDL lookup via usf-kg HTTP call
    return {
        "name": metric_name,
        "type": "sum",
        "measure": "amount",
        "table": "facts",
        "dimensions": ["counterparty", "currency"],
        "ontology_class": "fibo:FinancialExposure",
        "time_grains": ["day", "month", "quarter"],
        "contexts": {
            context: {
                "filter": "status = 'active'",
                "table": "facts",
            }
        },
    }


@router.post("/", response_model=CompiledQuery)
async def compile_metric(req: CompileRequest) -> CompiledQuery:
    """
    Compile an SDL metric name + context into SQL (via SQLGlot)
    and a SPARQL template.
    """
    metric_def = _get_metric_definition(req.metric_name, req.context)

    sql = generate_metric_sql(
        metric=metric_def,
        context=req.context,
        dialect=req.dialect,
    )

    sparql = _SPARQL_TEMPLATE.format(
        metric_name=req.metric_name,
        context=req.context,
        ontology_class=metric_def.get("ontology_class", "owl:Thing"),
        measure=metric_def.get("measure", "value"),
    )

    return CompiledQuery(
        metric_name=req.metric_name,
        context=req.context,
        sql=sql,
        sparql=sparql,
        dialect=req.dialect,
        ontology_class=metric_def.get("ontology_class"),
    )
