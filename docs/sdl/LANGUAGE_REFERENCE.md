# USF Semantic Definition Language (SDL) Reference

**Version**: 1.0 | **Schema**: `packages/sdl-schema/usf_sdl/models.py`

---

## Overview

SDL is a YAML-based language for defining semantic layer concepts in the Universal Semantic Fabric.
An SDL file declares **entities** (things), **metrics** (measurements), **contexts** (perspectives), and
**access policies** — everything the platform needs to compile SQL, OWL, R2RML, and PROV-O automatically.

SDL is validated by Pydantic v2 models in `usf_sdl.models.SDLDocument`.
The `usf-sdl` service exposes `POST /validate` and `POST /compile` for programmatic use.

### Supported Ontology Modules

`fibo` · `fhir` · `iec-cim` · `rami40` · `obo` · `dcat` · `gs1` · `sid`

---

## Document Structure

Every SDL file is a YAML mapping at the top level:

```yaml
sdl_version: "1.0"        # required — always "1.0"
tenant: acme-bank          # optional slug — scopes this definition to a tenant
ontology_module: fibo      # optional — one of the supported modules above

contexts: [...]            # list of ContextDefinition
access_policies: [...]     # list of AccessPolicyDefinition
entities: [...]            # list of EntityDefinition
metrics: [...]             # list of MetricDefinition
```

Names must be globally unique within their type (entities, metrics, contexts, access_policies).

---

## Context Definition

Contexts represent orthogonal business perspectives over the same data (e.g. risk vs. finance vs. ops).

```yaml
contexts:
  - name: risk                          # required | slug [a-z][a-z0-9_-]{0,63}
    description: >                      # required | human-readable string
      Credit risk context. EOD balances.
    named_graph_uri: usf://acme/risk/v1 # optional | IRI for this context's named graph
    parent_context: global              # optional | inherits from this context
    ontology_scope: [fibo:CreditRisk]   # optional | list of OWL class CURIEs scoping this context
```

### Inheritance Rules

When `parent_context` is set:
- The child inherits all entity/metric definitions from the parent.
- Child-level overrides (per entity/metric `contexts:` block) replace inherited values.
- Policies from the parent are **not** inherited — always set access_policy explicitly.

---

## Access Policy Definition

Named, reusable policies referenced by entities and metrics.

```yaml
access_policies:
  - name: risk_restricted               # required | slug
    description: Restricted to Risk     # required
    read: [role:risk_analyst, role:admin] # required | list of role or group CURIEs
    write: [role:admin]                 # optional | default []
    pii: false                          # required | boolean
    clearance: confidential             # required | public|internal|confidential|restricted|top_secret
    row_filter:                         # optional | column→value filter injected into every query
      tenant_id: "{{tenant}}"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | slug | ✅ | Unique identifier |
| `description` | string | ✅ | Human-readable purpose |
| `read` | list[string] | ✅ | Min 1 role. Format: `role:name` or `group:name` |
| `write` | list[string] | ❌ | Roles that can modify definitions |
| `pii` | boolean | ✅ | Whether this data contains PII |
| `clearance` | enum | ✅ | Data classification level |
| `row_filter` | dict | ❌ | Row-level security predicates |

Policies may also be declared **inline** on an entity or metric:

```yaml
access_policy:
  read: [role:analyst]
  pii: false
  clearance: internal
```

---

## Entity Definition

An entity maps a database table (or view) to an OWL class.

```yaml
entities:
  - name: BankAccount                   # required | PascalCase [A-Z][a-zA-Z0-9]{0,63}
    ontology_class: fibo:Account        # required | CURIE
    description: A financial account.   # required
    sql_table: accounts                 # optional | defaults to snake_case(name)
    sql_schema: public                  # optional | default "public"
    contexts:                           # optional | per-context table/description overrides
      risk:
        description: Account as credit exposure unit
        sql_table: accounts_risk_view
    properties: [...]                   # required | min 1 PropertyDefinition
    access_policy: public_read          # optional | policy name or inline block
```

### Property Definition

```yaml
properties:
  - name: account_id                    # required | snake_case
    ontology_property: fibo:hasIdentifier # required | CURIE
    sql_column: account_id              # conditional — required unless contexts provide it
    type: string                        # optional | string|integer|decimal|date|datetime|boolean|anyURI|float
    nullable: true                      # optional | default true
    description: Unique account ID      # optional
    allowed_values: [checking, savings] # optional | enum constraint
    references:                         # optional | foreign-key style link
      entity: LegalEntity
      property: entity_id
    contexts:                           # optional | per-context column overrides
      risk:
        sql_column: eod_balance
      finance:
        sql_column: current_balance
```

> **Rule**: either `sql_column` at property level **or** `contexts[*].sql_column` for every context
> must be present. The validator will reject ambiguous definitions.

---

## Metric Definition

A metric is a reusable, ontology-grounded aggregation expression.

```yaml
metrics:
  - name: total_exposure_by_counterparty   # required | snake_case [a-z][a-z0-9_]{0,79}
    ontology_class: fibo:FinancialExposure # required | CURIE
    description: >                         # required
      Total monetary exposure by counterparty.
    type: sum                              # required | sum|count|avg|min|max|count_distinct|custom
    measure: amount                        # required | property name on measure_entity
    measure_entity: FinancialTransaction   # required | entity name
    measure_sql: "SUM(t.amount)"          # optional | override compiled SQL expression
    dimensions: [...]                      # required | min 1 DimensionDefinition
    contexts:                              # optional | per-context filter/description overrides
      risk:
        description: Credit risk instruments only
        filter: "t.transaction_type IN ('loan', 'derivative', 'bond')"
      finance:
        filter: "t.status = 'settled'"
    default_filter: "t.status != 'cancelled'" # optional | applied in all contexts
    time_grains: [day, week, month, quarter, year] # optional | requires time_column + time_entity
    time_column: "t.transaction_date"      # conditional | required when time_grains set
    time_entity: FinancialTransaction      # conditional | required when time_grains set
    access_policy: risk_restricted         # optional | policy name or inline block
    examples:                              # optional | query examples for SDK/MCP
      - description: Q1 2024 EU exposure
        parameters:
          dimensions: [counterparty_name]
          time_range: {start: "2024-01-01", end: "2024-03-31", grain: quarter}
          context: risk
```

### Dimension Definition

```yaml
dimensions:
  - name: counterparty_name              # required | snake_case
    entity: LegalEntity                  # required | entity name
    property: legal_name                 # required | property name on that entity
    ontology_property: fibo:hasLegalName # required | CURIE
    description: Legal entity name       # optional
```

### Aggregation Types

| Type | SQL | Use case |
|------|-----|---------|
| `sum` | `SUM(col)` | Monetary totals, balances |
| `count` | `COUNT(col)` | Transaction volumes |
| `count_distinct` | `COUNT(DISTINCT col)` | Unique counterparties |
| `avg` | `AVG(col)` | Average exposure |
| `min` / `max` | `MIN/MAX(col)` | Range analysis |
| `custom` | Uses `measure_sql` verbatim | Complex expressions |

---

## Context Disambiguation (HTTP 409)

When a metric has different definitions across contexts, USF **cannot** safely choose one automatically.
A query without `X-USF-Context` returns:

```json
HTTP 409 Context Ambiguous

{
  "error": {
    "code": "CONTEXT_AMBIGUOUS",
    "message": "Metric 'balance' defined in 3 contexts: risk (EOD ledger), finance (current), ops (real-time). Specify X-USF-Context.",
    "detail": {
      "metric": "balance",
      "contexts": [
        {"name": "risk", "definition": "EOD ledger balance"},
        {"name": "finance", "definition": "Current operational balance"},
        {"name": "ops", "definition": "Real-time balance"}
      ]
    },
    "request_id": "uuid"
  }
}
```

**How to fix it** — set context in your request:

```bash
# REST
curl -H "X-USF-Context: finance" http://localhost:8000/query ...

# Python SDK
result = await client.query("balance", context="finance")

# TypeScript SDK
const result = await client.query("balance", { context: "finance" });
```

Or catch the error and prompt the user:

```python
except ContextAmbiguousError as e:
    chosen = e.available_contexts[0]   # or prompt the user
    result = await client.query(metric, context=chosen)
```

---

## Complete Example: FIBO Banking

The following annotated SDL powers the USF banking pilot. Full file at
`packages/sdl-schema/usf_sdl/examples/fibo_banking.yaml`.

```yaml
sdl_version: "1.0"
tenant: acme-bank
ontology_module: fibo          # Load FIBO OWL module automatically

# ── 1. Contexts ───────────────────────────────────────────────────────────────
# Three orthogonal views of the same data.
contexts:
  - name: risk
    description: Credit risk context. EOD balances, all exposure types.
  - name: finance
    description: Finance reporting. Settled transactions. BCBS 239 aligned.
  - name: ops
    description: Operational. Real-time balances and pending transactions.

# ── 2. Access Policies ────────────────────────────────────────────────────────
access_policies:
  - name: public_read
    description: All authenticated users
    read: [role:admin, role:risk_analyst, role:finance_analyst, role:auditor, role:viewer]
    pii: false
    clearance: internal

  - name: risk_restricted
    description: Risk and Compliance only
    read: [role:admin, role:risk_analyst, role:auditor]
    pii: false
    clearance: confidential

  - name: pii_entity
    description: Contains PII — compliance officers only
    read: [role:admin, role:compliance_officer]
    pii: true
    clearance: restricted

# ── 3. Entities ───────────────────────────────────────────────────────────────
entities:
  - name: LegalEntity
    ontology_class: fibo:LegalEntity         # maps to FIBO OWL class
    description: A legal entity — bank, corporate, or individual counterparty.
    sql_table: legal_entities
    properties:
      - name: entity_id
        ontology_property: fibo:hasIdentifier
        sql_column: entity_id
        type: string
        nullable: false
      - name: legal_name
        ontology_property: fibo:hasLegalName
        sql_column: legal_name
        type: string
      - name: lei_code
        ontology_property: fibo:hasLEI
        sql_column: lei_code
        type: string
      - name: country
        ontology_property: lcc:hasCountry
        sql_column: country_code
        type: string
    access_policy: public_read

  - name: BankAccount
    ontology_class: fibo:Account
    description: A financial account. Balance definition depends on context.
    sql_table: accounts
    properties:
      - name: account_id
        ontology_property: fibo:hasIdentifier
        sql_column: account_id
        type: string
        nullable: false
      - name: balance
        ontology_property: fibo:hasBalance
        type: decimal
        # Context-specific columns — this is why "balance" triggers 409 without context
        contexts:
          risk:    { sql_column: eod_balance }
          finance: { sql_column: current_balance }
          ops:     { sql_column: realtime_balance }
    access_policy: public_read

  - name: FinancialTransaction
    ontology_class: fibo:FinancialTransaction
    description: A monetary transaction. Source: IBM AML dataset.
    sql_table: transactions
    properties:
      - name: transaction_id
        ontology_property: fibo:hasIdentifier
        sql_column: transaction_id
        type: string
        nullable: false
      - name: amount
        ontology_property: fibo:hasMonetaryAmount
        sql_column: amount
        type: decimal
        nullable: false
      - name: transaction_date
        ontology_property: fibo:hasTransactionDate
        sql_column: transaction_date
        type: date
        nullable: false
      - name: status
        ontology_property: fibo:hasStatus
        sql_column: status
        type: string
        allowed_values: [pending, settled, cancelled, failed]
    access_policy: risk_restricted

# ── 4. Metrics ────────────────────────────────────────────────────────────────
metrics:
  - name: total_exposure_by_counterparty
    ontology_class: fibo:FinancialExposure
    description: Total monetary exposure aggregated by counterparty.
    type: sum
    measure: amount
    measure_entity: FinancialTransaction
    dimensions:
      - name: counterparty_name
        entity: LegalEntity
        property: legal_name
        ontology_property: fibo:hasLegalName
      - name: counterparty_country
        entity: LegalEntity
        property: country
        ontology_property: lcc:hasCountry
    contexts:
      risk:
        description: Credit instruments only
        filter: "t.transaction_type IN ('loan', 'derivative', 'bond')"
      finance:
        description: Settled transactions (BCBS 239)
        filter: "t.status = 'settled'"
    default_filter: "t.status != 'cancelled'"
    time_grains: [day, week, month, quarter, year]
    time_column: "t.transaction_date"
    time_entity: FinancialTransaction
    access_policy:
      read: [role:risk_analyst, role:finance_analyst, role:auditor]
      pii: false
      clearance: confidential
```

---

## Compilation Targets

When you `POST /sdl/compile`, USF produces:

| Target | Format | Used By |
|--------|--------|---------|
| OWL 2 QL | Turtle (.ttl) | QLever SPARQL engine |
| SQL | 4 dialects via SQLGlot (postgres, snowflake, bigquery, duckdb) | usf-query |
| R2RML | RDF mapping | Ontop virtual KG |
| SHACL | Shapes graph (.ttl) | usf-kg validation |
| PROV-O | JSON-LD template | Provenance chain |

---

## Best Practices

1. **One ontology module per SDL file.** Mixing `fibo` and `fhir` in the same file creates cross-module IRI conflicts.
2. **Name contexts after business departments**, not tech components (`risk` not `eod_view`).
3. **Always provide `description` on every metric.** It surfaces in the MCP tool catalogue and SDK `.explain()`.
4. **Use `allowed_values` for all string status/type columns.** This drives OWL `owl:oneOf` axioms and SHACL `sh:in` constraints.
5. **Prefer named policies over inline blocks** for reuse across entities. Reserve inline for one-off overrides.
6. **Context-sensitive `sql_column` triggers 409.** This is intentional — inform API consumers explicitly rather than guessing.
7. **`time_grains` requires both `time_column` and `time_entity`.** The validator enforces this; failing silently would produce incorrect SQL.
8. **Keep metric names globally unique**, even across SDL files. The platform merges all published versions into one semantic layer.
9. **Use `measure_sql` only for `custom` type** metrics. For standard aggregations, let the compiler generate SQL to ensure dialect portability.
10. **Version your SDL with meaningful changelogs.** `POST /sdl/publish` records history; `GET /sdl/diff/{v1}/{v2}` detects breaking changes before promoting to production.
