# USF SDL Schema Definition

**Version**: 1.0.0  
**Status**: FROZEN  
**Date**: 2026-03-27  
**Author**: usf-architect

> The Semantic Definition Language (SDL) is the human-authored YAML contract
> that describes entities, metrics, and contexts. The SDL compiler transforms
> SDL into OWL 2 QL axioms, SQL views, R2RML mappings, and SHACL shapes.

---

## Overview

SDL files are tenant-scoped YAML documents. A single SDL file may contain:
- One or more `entity` definitions
- One or more `metric` definitions
- One or more `context` definitions
- One or more `access_policy` definitions

SDL files are versioned and immutable once published. Breaking changes require a new version.

---

## Top-Level Structure

```yaml
# usf-sdl version declaration
sdl_version: "1.0"

# Optional: tenant-level metadata
tenant: acme-bank
ontology_module: fibo  # fibo | fhir | iec-cim | rami40 | obo | dcat | gs1 | sid

# One or more context definitions
contexts:
  - <context-definition>

# One or more entity definitions
entities:
  - <entity-definition>

# One or more metric definitions
metrics:
  - <metric-definition>

# One or more access policy definitions
access_policies:
  - <access-policy-definition>
```

---

## Context Definition

A context represents a named perspective or department's view of the data.
Each context maps to a named graph in the KG: `usf://{tenant}/{context_name}/v{version}`.

```yaml
context:
  name: finance                      # [required] slug identifier, snake_case
  description: "Finance reporting context for monthly P&L"  # [required]
  named_graph_uri: "usf://acme-bank/context/finance/v1"     # [computed, do not set manually]
  parent_context: null               # [optional] inherits metric definitions from parent
  ontology_scope:                    # [optional] restrict ontology classes visible in this context
    - fibo:Account
    - fibo:FinancialTransaction
    - fibo:CommercialBank
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Unique slug. Pattern: `^[a-z][a-z0-9_-]{0,63}$` |
| `description` | string | ✅ | Human description for UI and MCP tool catalog |
| `named_graph_uri` | string | ❌ | Computed. Pattern: `usf://{tenant}/context/{name}/v{n}` |
| `parent_context` | string\|null | ❌ | Name of parent context. Inherits metrics but may override. |
| `ontology_scope` | list[string] | ❌ | List of OWL class CURIEs. If set, only these classes are visible. |

---

## Entity Definition

An entity describes a business concept backed by an ontology class.
It defines: which SQL columns map to ontology properties, and how those mappings differ per context.

```yaml
entity:
  name: BankAccount                  # [required] PascalCase
  ontology_class: fibo:Account       # [required] CURIE from loaded ontology module
  description: "A financial account held at a commercial bank"

  # Context-specific overrides (at entity level, optional)
  contexts:
    risk:
      description: "Account as credit risk exposure unit"
      sql_table: "risk_schema.accounts"
    finance:
      description: "Account as operational financial entity"
      sql_table: "finance_schema.accounts"

  # Default SQL table (used when no context-specific override)
  sql_table: "public.accounts"       # [required if no per-context sql_table]
  sql_schema: "public"               # [optional, default: public]

  # Properties: each maps an ontology property to a SQL column
  properties:
    - name: account_id               # [required] snake_case field name
      ontology_property: fibo:hasIdentifier   # [required] CURIE
      sql_column: account_id         # [required] column name in sql_table
      type: string                   # [optional] xsd type: string | integer | decimal | date | datetime | boolean
      nullable: false                # [optional, default: true]
      description: "Unique account identifier"

    - name: balance
      ontology_property: fibo:hasBalance
      type: decimal
      description: "Account monetary balance"
      # Context-specific SQL column overrides
      contexts:
        risk:
          sql_column: eod_balance    # End-of-day ledger balance for risk
        finance:
          sql_column: current_balance  # Current operational balance for finance

    - name: account_type
      ontology_property: fibo:AccountType
      sql_column: account_type
      type: string
      allowed_values:               # [optional] OWL oneOf restriction
        - checking
        - savings
        - loan
        - derivative

    - name: holder
      ontology_property: fibo:hasAccountHolder
      sql_column: legal_entity_id
      type: string
      references:                   # [optional] foreign key → another SDL entity
        entity: LegalEntity
        property: entity_id

  # Entity-level access policy (applied to all properties unless overridden)
  access_policy: internal_read      # [optional] name of access_policy definition
```

### Entity Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Unique identifier. PascalCase. Used as OWL class local name. |
| `ontology_class` | string | ✅ | CURIE: `{prefix}:{LocalName}`. Must exist in loaded ontology module. |
| `description` | string | ✅ | Human-readable description. Used in MCP tool catalog. |
| `sql_table` | string | ✅* | Default source SQL table. *Required unless overridden in all contexts. |
| `sql_schema` | string | ❌ | PostgreSQL schema name. Default: `public`. |
| `contexts` | map | ❌ | Per-context overrides (description, sql_table). |
| `properties` | list | ✅ | At least one property required. |
| `access_policy` | string | ❌ | References an `access_policy.name`. Default: no restriction. |

### Property Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Snake_case. Unique within entity. |
| `ontology_property` | string | ✅ | CURIE from ontology. |
| `sql_column` | string | ✅* | SQL column name. *Required unless contexts each define it. |
| `type` | string | ❌ | XSD type hint: `string`, `integer`, `decimal`, `date`, `datetime`, `boolean`. |
| `nullable` | bool | ❌ | Default `true`. |
| `description` | string | ❌ | Shown in UI and MCP tool docs. |
| `contexts` | map | ❌ | Per-context SQL column overrides. |
| `allowed_values` | list | ❌ | Generates OWL `oneOf` restriction + SHACL `sh:in`. |
| `references` | object | ❌ | FK reference to another SDL entity. Generates OWL object property axiom + R2RML join. |

---

## Metric Definition

A metric is a business measure defined in terms of SQL aggregation logic.
The SDL compiler generates executable SQL and SPARQL from this definition.

```yaml
metric:
  name: total_exposure_by_counterparty   # [required] snake_case
  ontology_class: fibo:FinancialExposure # [required] CURIE
  description: "Total monetary exposure aggregated by counterparty legal entity"

  type: sum                            # [required] sum | count | avg | min | max | count_distinct | custom
  measure: transaction_amount          # [required] source column or expression
  measure_entity: FinancialTransaction # [required] SDL entity containing the measure column
  measure_sql: "SUM(t.amount)"         # [optional] override compiled SQL expression

  dimensions:                          # [required] list of grouping dimensions
    - name: counterparty_name
      entity: LegalEntity
      property: legal_name
      ontology_property: fibo:hasLegalName
    - name: counterparty_country
      entity: LegalEntity
      property: country
      ontology_property: lcc:hasCountry
    - name: transaction_type
      entity: FinancialTransaction
      property: transaction_type
      ontology_property: fibo:hasTransactionType

  # Context-specific filters (ANDed with base query)
  contexts:
    risk:
      description: "Exposure from loan, derivative, and bond transactions"
      filter: "t.transaction_type IN ('loan', 'derivative', 'bond')"
      additional_dimensions: []
    finance:
      description: "Settled transactions only for finance reporting"
      filter: "t.status = 'settled'"

  # Default filter (applied in all contexts unless overridden)
  default_filter: "t.status != 'cancelled'"

  # Time intelligence
  time_grains:                         # [required] available time aggregations
    - day
    - week
    - month
    - quarter
    - year
  time_column: "t.transaction_date"    # [required if time_grains non-empty]
  time_entity: FinancialTransaction    # [required if time_grains non-empty]

  # Access policy
  access_policy:
    read:
      - role:risk_analyst
      - role:finance_analyst
      - role:auditor
    pii: false
    clearance: internal

  # Optional: example values for MCP tool catalog
  examples:
    - description: "Total EU exposure for Q1 2024"
      parameters:
        dimensions: [counterparty_name, counterparty_country]
        filters: {counterparty_country: EU}
        time_range: {start: "2024-01-01", end: "2024-03-31", grain: quarter}
```

### Metric Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Snake_case. Unique across tenant. Used as OWL property name and SQL view name. |
| `ontology_class` | string | ✅ | CURIE. Ontology class this metric is an instance of. |
| `description` | string | ✅ | Human description for UI and MCP tool catalog. |
| `type` | string | ✅ | Aggregation type: `sum`, `count`, `avg`, `min`, `max`, `count_distinct`, `custom`. |
| `measure` | string | ✅ | Column name or SQL expression for the measured quantity. |
| `measure_entity` | string | ✅ | Name of the SDL entity that contains the measure column. |
| `measure_sql` | string | ❌ | Override the compiled SQL expression. Overrides `type` + `measure`. |
| `dimensions` | list | ✅ | List of dimension objects (name, entity, property). Min 1. |
| `contexts` | map | ❌ | Per-context filter and description overrides. |
| `default_filter` | string | ❌ | SQL WHERE clause applied before context filter. |
| `time_grains` | list | ❌ | Allowed grain values: `day`, `week`, `month`, `quarter`, `year`. |
| `time_column` | string | ✅* | *Required when `time_grains` is non-empty. |
| `time_entity` | string | ✅* | *Required when `time_grains` is non-empty. |
| `access_policy` | object\|string | ❌ | Inline policy OR name reference. |
| `examples` | list | ❌ | Example queries for MCP tool documentation. |

### Metric Type Semantics

| Type | Compiled SQL | Use Case |
|------|-------------|---------|
| `sum` | `SUM(column)` | Financial totals, amounts |
| `count` | `COUNT(*)` | Transaction volumes, entity counts |
| `avg` | `AVG(column)` | Average balance, risk score |
| `min` / `max` | `MIN/MAX(column)` | Date ranges, extremes |
| `count_distinct` | `COUNT(DISTINCT column)` | Unique counterparties, accounts |
| `custom` | Uses `measure_sql` verbatim | Complex expressions, window functions |

---

## Access Policy Definition

Access policies are named and reusable across entities and metrics.

```yaml
access_policy:
  name: internal_read                # [required] unique slug
  description: "Read access for all internal employees"

  read:                              # [required] list of role CURIEs
    - role:admin
    - role:risk_analyst
    - role:finance_analyst
    - role:auditor

  write: []                          # [optional] empty = no programmatic write via USF

  pii: false                         # [required] true = triggers PII masking rules
  clearance: internal                # [required] internal | confidential | restricted | top_secret

  # Optional: row-level filter for fine-grained ABAC
  row_filter:
    role:risk_analyst: "dept = 'risk'"
    role:finance_analyst: "dept IN ('finance', 'treasury')"
```

### Access Policy Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Unique slug. Pattern: `^[a-z][a-z0-9_-]{0,63}$` |
| `description` | string | ✅ | Human description. |
| `read` | list[string] | ✅ | Role CURIEs. Pattern: `role:{slug}`. |
| `write` | list[string] | ❌ | Default empty. USF API is read-optimized. |
| `pii` | bool | ✅ | If `true`, PII masking applied at query time. |
| `clearance` | string | ✅ | One of: `public`, `internal`, `confidential`, `restricted`, `top_secret`. |
| `row_filter` | map | ❌ | Per-role SQL filter injected at query execution. |

---

## Complete Annotated Example — FIBO Banking Pilot

```yaml
# usf-platform/packages/sdl-schema/usf_sdl/examples/fibo_banking.yaml
# USF FIBO Banking Pilot — Complete SDL Example
# Covers: Account, Transaction, LegalEntity, and the total_exposure metric.

sdl_version: "1.0"
tenant: acme-bank
ontology_module: fibo

# ─────────────────────────────────────────────────────────────────
# CONTEXTS
# ─────────────────────────────────────────────────────────────────

contexts:
  - name: risk
    description: >
      Credit risk context. Measures and entities are defined
      from the perspective of the Risk Management department.
      Uses end-of-day (EOD) balances and includes all exposure types.

  - name: finance
    description: >
      Finance reporting context. Metrics reflect settled transactions
      only, using current operational balances. Aligned with BCBS 239
      reporting requirements.

  - name: ops
    description: >
      Operational context. Real-time current balances and pending transactions.
      Used by Operations and Treasury teams.

# ─────────────────────────────────────────────────────────────────
# ACCESS POLICIES
# ─────────────────────────────────────────────────────────────────

access_policies:
  - name: public_read
    description: "Readable by all authenticated users"
    read: [role:admin, role:risk_analyst, role:finance_analyst, role:auditor, role:viewer]
    pii: false
    clearance: internal

  - name: risk_restricted
    description: "Restricted to Risk and Compliance roles"
    read: [role:admin, role:risk_analyst, role:auditor]
    pii: false
    clearance: confidential
    row_filter:
      role:risk_analyst: "risk_department = true"

  - name: pii_entity
    description: "Contains PII — masked except for privileged roles"
    read: [role:admin, role:compliance_officer]
    pii: true
    clearance: restricted

# ─────────────────────────────────────────────────────────────────
# ENTITIES
# ─────────────────────────────────────────────────────────────────

entities:
  - name: LegalEntity
    ontology_class: fibo:LegalEntity
    description: >
      A legal entity: bank, corporate, or individual. In the FIBO pilot
      this is the primary counterparty type for exposure analysis.
    sql_table: legal_entities
    properties:
      - name: entity_id
        ontology_property: fibo:hasIdentifier
        sql_column: entity_id
        type: string
        nullable: false
        description: "Internal unique identifier"

      - name: legal_name
        ontology_property: fibo:hasLegalName
        sql_column: legal_name
        type: string
        nullable: false
        description: "Registered legal name (e.g., Deutsche Bank AG)"

      - name: lei_code
        ontology_property: fibo:hasLEI
        sql_column: lei_code
        type: string
        description: "Legal Entity Identifier (20-char ISO 17442)"

      - name: country
        ontology_property: lcc:hasCountry
        sql_column: country_code
        type: string
        description: "ISO 3166-1 alpha-2 country code"

      - name: entity_type
        ontology_property: fibo:EntityType
        sql_column: entity_type
        type: string
        allowed_values: [bank, corporate, sovereign, fund, individual]

    access_policy: public_read

  - name: CommercialBank
    ontology_class: fibo:CommercialBank
    description: >
      A commercial bank that accepts deposits and makes loans.
      Subtype of LegalEntity in FIBO.
    sql_table: banks
    properties:
      - name: bank_id
        ontology_property: fibo:hasIdentifier
        sql_column: bank_id
        type: string
        nullable: false

      - name: bank_name
        ontology_property: fibo:hasLegalName
        sql_column: bank_name
        type: string
        nullable: false

      - name: swift_code
        ontology_property: fibo:hasSWIFTCode
        sql_column: swift_code
        type: string

      - name: country
        ontology_property: lcc:hasCountry
        sql_column: country_code
        type: string

    access_policy: public_read

  - name: BankAccount
    ontology_class: fibo:Account
    description: >
      A financial account held at a commercial bank.
      Balance definition varies by context (EOD vs current).
    sql_table: accounts
    contexts:
      risk:
        description: "Account as credit risk exposure unit (EOD balance)"
      finance:
        description: "Account as finance reporting entity (current balance)"
      ops:
        description: "Account as operational entity (real-time balance)"
    properties:
      - name: account_id
        ontology_property: fibo:hasIdentifier
        sql_column: account_id
        type: string
        nullable: false

      - name: account_number
        ontology_property: fibo:hasAccountNumber
        sql_column: account_number
        type: string
        nullable: false

      - name: balance
        ontology_property: fibo:hasBalance
        type: decimal
        description: "Monetary balance — definition differs by context"
        contexts:
          risk:
            sql_column: eod_balance      # End-of-day ledger balance
          finance:
            sql_column: current_balance  # Current operational balance
          ops:
            sql_column: realtime_balance # Real-time balance (may be unconfirmed)

      - name: account_type
        ontology_property: fibo:AccountType
        sql_column: account_type
        type: string
        allowed_values: [checking, savings, loan, derivative, bond, custody]

      - name: holder
        ontology_property: fibo:hasAccountHolder
        sql_column: legal_entity_id
        type: string
        references:
          entity: LegalEntity
          property: entity_id

      - name: currency
        ontology_property: fibo:hasCurrency
        sql_column: currency_code
        type: string
        description: "ISO 4217 currency code"

    access_policy: public_read

  - name: FinancialTransaction
    ontology_class: fibo:FinancialTransaction
    description: >
      A monetary transaction between two parties. Source: IBM AML dataset.
      Used to compute exposure metrics.
    sql_table: transactions
    properties:
      - name: transaction_id
        ontology_property: fibo:hasIdentifier
        sql_column: transaction_id
        type: string
        nullable: false

      - name: party_a
        ontology_property: fibo:hasPartyA
        sql_column: account_from_id
        type: string
        references:
          entity: BankAccount
          property: account_id

      - name: party_b
        ontology_property: fibo:hasPartyB
        sql_column: account_to_id
        type: string
        references:
          entity: BankAccount
          property: account_id

      - name: amount
        ontology_property: fibo:hasMonetaryAmount
        sql_column: amount
        type: decimal
        nullable: false

      - name: currency
        ontology_property: fibo:hasCurrency
        sql_column: currency
        type: string

      - name: transaction_type
        ontology_property: fibo:hasTransactionType
        sql_column: type
        type: string
        allowed_values: [loan, derivative, bond, transfer, payment, deposit, withdrawal]

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

      - name: is_laundering
        ontology_property: fibo:hasSuspiciousFlag
        sql_column: is_laundering
        type: boolean
        description: "AML flag from IBM dataset (pilot only)"

    access_policy: risk_restricted

# ─────────────────────────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────────────────────────

metrics:
  - name: total_exposure_by_counterparty
    ontology_class: fibo:FinancialExposure
    description: >
      Total monetary exposure aggregated by counterparty legal entity.
      The 'balance' in context 'risk' means EOD balance; in 'finance' means current balance.
      This is the primary pilot query metric.
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
      - name: transaction_type
        entity: FinancialTransaction
        property: transaction_type
        ontology_property: fibo:hasTransactionType
    contexts:
      risk:
        description: "Exposure from credit risk instruments only"
        filter: "t.transaction_type IN ('loan', 'derivative', 'bond')"
      finance:
        description: "Settled transactions only for finance reporting"
        filter: "t.status = 'settled'"
    default_filter: "t.status != 'cancelled'"
    time_grains: [day, week, month, quarter, year]
    time_column: "t.transaction_date"
    time_entity: FinancialTransaction
    access_policy:
      read: [role:risk_analyst, role:finance_analyst, role:auditor]
      pii: false
      clearance: confidential
    examples:
      - description: "Total EU counterparty exposure for Q1 2024"
        parameters:
          dimensions: [counterparty_name, counterparty_country]
          filters: {counterparty_country: EU}
          time_range: {start: "2024-01-01", end: "2024-03-31", grain: quarter}
          context: risk

  - name: transaction_volume_by_type
    ontology_class: fibo:FinancialTransaction
    description: "Count of transactions grouped by type and time period"
    type: count
    measure: transaction_id
    measure_entity: FinancialTransaction
    dimensions:
      - name: transaction_type
        entity: FinancialTransaction
        property: transaction_type
        ontology_property: fibo:hasTransactionType
      - name: status
        entity: FinancialTransaction
        property: status
        ontology_property: fibo:hasStatus
    time_grains: [day, month, quarter]
    time_column: "t.transaction_date"
    time_entity: FinancialTransaction
    access_policy: public_read

  - name: suspicious_transaction_count
    ontology_class: fibo:SuspiciousActivity
    description: "Count of flagged AML suspicious transactions (pilot only)"
    type: count
    measure: transaction_id
    measure_entity: FinancialTransaction
    dimensions:
      - name: counterparty_name
        entity: LegalEntity
        property: legal_name
        ontology_property: fibo:hasLegalName
      - name: transaction_type
        entity: FinancialTransaction
        property: transaction_type
        ontology_property: fibo:hasTransactionType
    default_filter: "t.is_laundering = true"
    time_grains: [day, week, month, quarter]
    time_column: "t.transaction_date"
    time_entity: FinancialTransaction
    access_policy:
      read: [role:admin, role:compliance_officer, role:risk_analyst]
      pii: false
      clearance: restricted
```

---

## SDL Validation Rules

The SDL compiler enforces these rules at validation time:

1. **Ontology class existence**: Every `ontology_class` and `ontology_property` CURIE must exist in the loaded ontology module (or a registered namespace).
2. **Entity uniqueness**: Entity names must be unique within the SDL file.
3. **Metric uniqueness**: Metric names must be unique within the tenant across all SDL versions.
4. **Context reference**: Context names in `entity.contexts` and `metric.contexts` must be declared in the `contexts:` block.
5. **Access policy reference**: String `access_policy` values must reference a declared `access_policy.name`.
6. **Property uniqueness**: Property names must be unique within an entity.
7. **Dimension entity reference**: Dimension `entity` values must match an entity `name` in the same SDL.
8. **Time grain requirement**: If `time_grains` is non-empty, `time_column` and `time_entity` are required.
9. **SQL column mutual exclusion**: If a property has `contexts` with `sql_column`, then the top-level `sql_column` may be omitted. But every context must define `sql_column` or the top-level must exist.
10. **Context disambiguation**: A property referenced in a query without a context header returns HTTP 409 if it has different `sql_column` values per context.

---

*End of SDL Schema v1.0.0*
