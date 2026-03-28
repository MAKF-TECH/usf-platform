# USF SDL Schema Definition

**Version**: 1.0.0 | **Status**: FROZEN | **Date**: 2026-03-27

The Semantic Definition Language (SDL) is tenant-authored YAML that describes entities, metrics, and contexts.
The SDL compiler transforms SDL into OWL 2 QL axioms, SQL views, R2RML mappings, and SHACL shapes.

## Top-Level Structure

```yaml
sdl_version: "1.0"
tenant: acme-bank
ontology_module: fibo  # fibo | fhir | iec-cim | rami40

contexts:
  - name: finance
    description: Finance reporting context

access_policies:
  - name: internal_read
    read: [role:analyst]
    pii: false
    clearance: internal

entities:
  - name: BankAccount
    ontology_class: fibo:Account
    sql_table: accounts
    properties:
      - name: balance
        ontology_property: fibo:hasBalance
        contexts:
          risk: { sql_column: eod_balance }
          finance: { sql_column: current_balance }

metrics:
  - name: total_exposure_by_counterparty
    ontology_class: fibo:FinancialExposure
    type: sum
    measure: amount
    measure_entity: FinancialTransaction
    dimensions:
      - name: counterparty_name
        entity: LegalEntity
        property: legal_name
        ontology_property: fibo:hasLegalName
    time_grains: [day, month, quarter]
    time_column: "t.transaction_date"
    time_entity: FinancialTransaction
```

## Context Definition Fields
| Field | Required | Description |
|-------|----------|-------------|
| name | ✅ | Unique slug. Pattern: ^[a-z][a-z0-9_-]{0,63}$ |
| description | ✅ | Human description for UI and MCP |
| parent_context | ❌ | Inherits metrics from parent |
| ontology_scope | ❌ | Restrict visible OWL classes |

## Entity Definition Fields
| Field | Required | Description |
|-------|----------|-------------|
| name | ✅ | PascalCase, unique |
| ontology_class | ✅ | CURIE: prefix:LocalName |
| description | ✅ | Human description |
| sql_table | ✅* | Default SQL table (*unless all contexts define it) |
| properties | ✅ | Min 1 property required |
| access_policy | ❌ | Named policy reference or inline |

## Property Fields
| Field | Required | Description |
|-------|----------|-------------|
| name | ✅ | snake_case, unique within entity |
| ontology_property | ✅ | CURIE |
| sql_column | ✅* | *Required unless contexts each define it |
| type | ❌ | XSD: string, integer, decimal, date, datetime, boolean |
| contexts | ❌ | Per-context sql_column overrides |
| references | ❌ | FK to another SDL entity |

## Metric Definition Fields
| Field | Required | Description |
|-------|----------|-------------|
| name | ✅ | snake_case, unique across tenant |
| ontology_class | ✅ | CURIE |
| type | ✅ | sum, count, avg, min, max, count_distinct, custom |
| measure | ✅ | Column name or expression |
| measure_entity | ✅ | SDL entity containing the measure |
| dimensions | ✅ | Min 1 dimension |
| time_grains | ❌ | day, week, month, quarter, year |
| time_column | ✅* | *Required when time_grains non-empty |

## Access Policy Fields
| Field | Required | Description |
|-------|----------|-------------|
| name | ✅ | Unique slug |
| read | ✅ | Role CURIEs: role:slug |
| pii | ✅ | bool — triggers PII masking if true |
| clearance | ✅ | public, internal, confidential, restricted, top_secret |
| row_filter | ❌ | Per-role SQL WHERE injection |

## Validation Rules
1. Every ontology_class and ontology_property CURIE must exist in loaded ontology module
2. Entity names unique within SDL; metric names unique across tenant
3. Context references must be declared in contexts block
4. Access policy references must be declared in access_policies block
5. If time_grains non-empty, time_column and time_entity required
6. Context-ambiguous property (different sql_column per context) returns HTTP 409 without X-USF-Context

*See packages/sdl-schema for Pydantic v2 model implementation.*
*See packages/sdl-schema/usf_sdl/examples/fibo_banking.yaml for complete example.*

---

## Worked Example 1: Banking (FIBO)

See `packages/sdl-schema/usf_sdl/examples/fibo_banking.yaml` for the complete annotated example.

Key patterns:
- **3 contexts** (`risk`, `finance`, `ops`) — each with different `balance` definitions
- **Context disambiguation**: querying `balance` without `X-USF-Context` → HTTP 409
- **Pilot metric**: `total_exposure_by_counterparty` with context-specific SQL filters

```yaml
entities:
  - name: BankAccount
    ontology_class: fibo:Account
    sql_table: accounts
    properties:
      - name: balance
        ontology_property: fibo:hasBalance
        type: decimal
        contexts:
          risk:    { sql_column: eod_balance }      # Risk: end-of-day balance
          finance: { sql_column: current_balance }  # Finance: operating balance
          ops:     { sql_column: realtime_balance } # Ops: real-time balance
        # ↑ HTTP 409 CONTEXT_AMBIGUOUS without X-USF-Context header
```

---

## Worked Example 2: Healthcare (HL7 FHIR)

See `packages/sdl-schema/usf_sdl/examples/fhir_healthcare.yaml` for the complete example.

Key patterns:
- **3 contexts** (`clinical`, `billing`, `research`) with FHIR R4 ontology module
- **PII enforcement**: `pii: true` triggers column masking in PROV-O
- **Consent-scoped research**: `row_filter` ensures only consented patients appear in research queries
- **Context-specific LOS**: `length_of_stay_days` maps to `actual_los_days` (clinical) vs `billed_los_days` (billing)

```yaml
entities:
  - name: Encounter
    ontology_class: fhir:Encounter
    sql_table: encounters
    properties:
      - name: length_of_stay_days
        ontology_property: fhir:Encounter.length
        type: integer
        contexts:
          clinical: { sql_column: actual_los_days }  # Real admission duration
          billing:  { sql_column: billed_los_days }  # Billed duration (may differ)
        # ↑ HTTP 409 CONTEXT_AMBIGUOUS without X-USF-Context header

metrics:
  - name: active_condition_count_by_icd10
    type: count
    contexts:
      research:
        filter: "patient_id IN (SELECT patient_id FROM patients WHERE consent_research = true)"
    access_policy:
      read: [role:researcher, role:data_scientist]
      pii: false   # Aggregates only — no patient PII exposed
