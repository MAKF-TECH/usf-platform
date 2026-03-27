from __future__ import annotations
from fastapi import APIRouter
from usf_query.models import CompileRequest, CompiledQuery
from usf_query.services.sql_generator import generate_metric_sql

router = APIRouter(prefix="/compile", tags=["compile"])

_SPARQL_TMPL = """PREFIX usf: <urn:usf:>
SELECT ?dim ?{metric}
WHERE {{
  GRAPH <urn:usf:context:{context}> {{
    ?s a <{cls}> ; usf:{measure} ?{metric} .
    OPTIONAL {{ ?s usf:dimension ?dim }}
  }}
}} GROUP BY ?dim"""


def _get_metric_def(name: str, context: str) -> dict:
    # TODO: real SDL lookup from usf-kg
    return {
        "name": name, "type": "sum", "measure": "amount", "table": "facts",
        "dimensions": ["counterparty", "currency"],
        "ontology_class": "fibo:FinancialExposure",
        "time_grains": ["day", "month", "quarter"],
        "contexts": {context: {"filter": "status = 'active'", "table": "facts"}},
    }


@router.post("/", response_model=CompiledQuery)
async def compile_metric(req: CompileRequest) -> CompiledQuery:
    m = _get_metric_def(req.metric_name, req.context)
    sql = generate_metric_sql(metric=m, context=req.context, dialect=req.dialect)
    sparql = _SPARQL_TMPL.format(
        metric=req.metric_name, context=req.context,
        cls=m.get("ontology_class", "owl:Thing"), measure=m.get("measure", "value"),
    )
    return CompiledQuery(metric_name=req.metric_name, context=req.context, sql=sql,
                         sparql=sparql, dialect=req.dialect, ontology_class=m.get("ontology_class"))
