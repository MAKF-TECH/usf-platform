from __future__ import annotations
from fastapi import APIRouter
from usf_query.models import MetricDefinition

router = APIRouter(prefix="/explain", tags=["explain"])


@router.get("/{metric}", response_model=MetricDefinition)
async def explain_metric(metric: str) -> MetricDefinition:
    # TODO: replace with real SDL/KG lookup
    return MetricDefinition(
        name=metric,
        description=f"Semantic metric: {metric}",
        ontology_class="fibo:FinancialExposure",
        contexts=["risk", "finance", "ops"],
        sql_template=f"SELECT SUM(amount) AS {metric} FROM facts WHERE context = '{{context}}'",
        sparql_template=f"SELECT ?{metric} WHERE {{ GRAPH <urn:usf:context:{{context}}> {{ ?s a fibo:FinancialExposure ; fibo:hasMonetaryAmount ?{metric} }} }}",
        dimensions=["counterparty", "currency", "region"],
        lineage={{"sources": ["warehouse.transactions"], "sdl_version": "1.0.0"}},
    )
