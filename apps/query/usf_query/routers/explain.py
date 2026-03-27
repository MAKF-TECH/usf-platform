from __future__ import annotations

from fastapi import APIRouter, HTTPException

from usf_query.models import MetricDefinition

router = APIRouter(prefix="/explain", tags=["explain"])


def _get_metric_lineage(metric_name: str) -> dict:
    """
    Fetch full metric lineage from SDL/KG layer.
    In production: call usf-kg /metrics/{name}/lineage
    """
    # TODO: replace with real usf-kg call
    return {
        "sources": ["warehouse.transactions", "warehouse.accounts"],
        "transformations": ["join on account_id", "filter by context"],
        "sdl_version": "1.0.0",
        "ontology_mapping": "fibo:FinancialExposure → fibo:hasMonetaryAmount",
    }


@router.get("/{metric}", response_model=MetricDefinition)
async def explain_metric(metric: str) -> MetricDefinition:
    """
    Return full metric definition + lineage for the given metric name.
    Includes ontology class mapping, available contexts, SQL template, SPARQL template.
    """
    # TODO: replace with real SDL/KG lookup
    lineage = _get_metric_lineage(metric)

    return MetricDefinition(
        name=metric,
        description=f"Semantic metric: {metric}",
        ontology_class="fibo:FinancialExposure",
        contexts=["risk", "finance", "ops"],
        sql_template=f"SELECT SUM(amount) AS {metric} FROM facts WHERE context = '{{context}}'",
        sparql_template=(
            f"SELECT ?{metric} WHERE {{ GRAPH <urn:usf:context:{{context}}> "
            f"{{ ?s a fibo:FinancialExposure ; fibo:hasMonetaryAmount ?{metric} }} }}"
        ),
        dimensions=["counterparty", "currency", "region"],
        lineage=lineage,
    )
