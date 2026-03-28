/**
 * Banking pilot demo — USF TypeScript SDK.
 * Run: npx tsx examples/banking-pilot.ts
 */
import { USFClient, ContextAmbiguousError } from "../src/index.js";

async function main(): Promise<void> {
  const client = new USFClient("http://localhost:8000", { context: "finance" });
  await client.login("analyst@acme-bank.com", "demo123");

  // ── List available metrics ─────────────────────────────────────────────────
  const metrics = await client.listMetrics();
  console.log("Available metrics:", metrics.map((m) => m.name));

  // ── Query total counterparty exposure ──────────────────────────────────────
  const result = await client.query("total_exposure_by_counterparty", {
    dimensions: ["counterparty_name", "counterparty_country"],
    timeRange: { start: "2024-01-01", end: "2024-03-31" },
  });
  console.log(`Result: ${result.row_count} rows`);
  console.log(
    "Provenance context:",
    result.provenance["prov:wasGeneratedBy"]["usf:contextApplied"],
  );

  // ── Context disambiguation ─────────────────────────────────────────────────
  // "balance" is defined in risk, finance, and ops — 409 expected without context
  try {
    const noContextClient = new USFClient("http://localhost:8000"); // no default context
    await noContextClient.login("analyst@acme-bank.com", "demo123");
    await noContextClient.query("balance");
  } catch (e) {
    if (e instanceof ContextAmbiguousError) {
      console.log("409 as expected. Available contexts:", e.availableContexts);
    } else {
      throw e;
    }
  }

  // ── Entity search ──────────────────────────────────────────────────────────
  const entities = await client.searchEntities("Deutsche Bank", {
    entityType: "fibo:LegalEntity",
  });
  console.log(`Found ${entities.length} legal entities matching 'Deutsche Bank'`);

  // ── Explain a metric ───────────────────────────────────────────────────────
  const explanation = await client.explain("total_exposure_by_counterparty", "risk");
  console.log("SQL (first 200 chars):", (explanation.compiled_sql ?? "").slice(0, 200));

  // ── Raw SPARQL ─────────────────────────────────────────────────────────────
  const sparqlRows = await client.sparql(
    `PREFIX fibo: <https://spec.edmcouncil.org/fibo/ontology/>
SELECT ?bank ?name WHERE {
  ?bank a fibo:CommercialBank ;
        fibo:hasLegalName ?name .
} LIMIT 10`,
    "finance",
  );
  console.log(`SPARQL returned ${sparqlRows.length} banks`);
}

main().catch(console.error);
