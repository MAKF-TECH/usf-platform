"""Banking pilot demo using USF Python SDK."""
import asyncio
from usf_sdk import USFClient, ContextAmbiguousError


async def main() -> None:
    async with USFClient("http://localhost:8000", context="finance") as client:
        await client.login("analyst@acme-bank.com", "demo123")

        # ── List available metrics ────────────────────────────────────────────
        metrics = await client.list_metrics()
        print(f"Available metrics: {[m.name for m in metrics]}")

        # ── Query total counterparty exposure ─────────────────────────────────
        result = await client.query(
            metric="total_exposure_by_counterparty",
            dimensions=["counterparty_name", "counterparty_country"],
            time_range={"start": "2024-01-01", "end": "2024-03-31"},
        )
        print(f"Result: {len(result.data)} rows")
        print(
            f"Provenance: {result.provenance['prov:wasGeneratedBy']['usf:contextApplied']}"
        )

        # ── Context disambiguation demo ───────────────────────────────────────
        # "balance" is defined in risk, finance, and ops contexts.
        # Querying without context → 409 ContextAmbiguousError.
        try:
            await client.query("balance")  # No context → expects 409
        except ContextAmbiguousError as e:
            print(f"409 as expected. Available contexts: {e.available_contexts}")

        # ── Knowledge-graph entity search ─────────────────────────────────────
        entities = await client.search_entities(
            "Deutsche Bank", entity_type="fibo:LegalEntity"
        )
        print(f"Found {len(entities)} legal entities matching 'Deutsche Bank'")

        # ── Explain a metric ──────────────────────────────────────────────────
        explanation = await client.explain(
            "total_exposure_by_counterparty", context="risk"
        )
        print(f"Metric SQL (first 200 chars): {(explanation.compiled_sql or '')[:200]}")

        # ── Raw SPARQL ────────────────────────────────────────────────────────
        sparql_rows = await client.sparql(
            """
            PREFIX fibo: <https://spec.edmcouncil.org/fibo/ontology/>
            SELECT ?bank ?name WHERE {
              ?bank a fibo:CommercialBank ;
                    fibo:hasLegalName ?name .
            }
            LIMIT 10
            """,
            context="finance",
        )
        print(f"SPARQL returned {len(sparql_rows)} banks")


if __name__ == "__main__":
    asyncio.run(main())
