# @usf/sdk — TypeScript/JavaScript SDK for Universal Semantic Fabric

[![npm](https://img.shields.io/npm/v/@usf/sdk)](https://www.npmjs.com/package/@usf/sdk)

Zero-dependency TypeScript client for the USF platform. Uses native `fetch` (Node ≥18 / browser).

## Installation

```bash
npm install @usf/sdk
```

## Quick Start

```typescript
import { USFClient, ContextAmbiguousError } from "@usf/sdk";

const client = new USFClient("http://localhost:8000", { context: "finance" });
await client.login("analyst@acme-bank.com", "demo123");

const result = await client.query("total_exposure_by_counterparty", {
  dimensions: ["counterparty_name", "counterparty_country"],
  timeRange: { start: "2024-01-01", end: "2024-03-31" },
});
console.log(result.data);
```

## API Reference

### `new USFClient(baseUrl, options?)`

| Option | Type | Description |
|--------|------|-------------|
| `context` | `string` | Default semantic context for all requests |
| `apiKey` | `string` | Pre-issued API key (skips `login`) |
| `tenant` | `string` | Tenant UUID for `X-USF-Tenant-ID` header |

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `login(email, password)` | `Promise<this>` | Authenticate, store JWT |
| `listContexts()` | `Promise<string[]>` | Available contexts |
| `listMetrics(context?)` | `Promise<MetricSummary[]>` | Metric catalogue |
| `query(metric, options?)` | `Promise<QueryResult>` | Execute semantic query |
| `explain(metric, context?)` | `Promise<MetricExplanation>` | Full metric definition |
| `searchEntities(query, options?)` | `Promise<EntityResult[]>` | KG entity search |
| `getEntity(iri, depth?)` | `Promise<EntityDetail>` | Entity + provenance |
| `sparql(query, context?)` | `Promise<Record<string,unknown>[]>` | Raw SPARQL |

### Error Handling

```typescript
import { ContextAmbiguousError, AuthError } from "@usf/sdk";

try {
  await client.query("balance");
} catch (e) {
  if (e instanceof ContextAmbiguousError) {
    // e.availableContexts: string[]
    const result = await client.query("balance", { context: e.availableContexts[0] });
  }
}
```

## Examples

- [`examples/banking-pilot.ts`](examples/banking-pilot.ts) — full FIBO banking demo
