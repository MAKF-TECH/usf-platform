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

```yaml
sdl_version: "1.0"
tenant: acme-bank
ontology_module: fibo

contexts:
  - name: risk
    description: Credit risk context. EOD balances, exposure instruments.
  - name: finance
    description: Finance reporting. Settled transactions, BCBS 239 aligned.

access_policies:
  - name: risk_restricted
    description: Risk and compliance teams only
    read: [role:risk_analyst, role:auditor, role:admin]
    pii: false
    clearance: confidential

entities:
  - name: BankAccount
    ontology_class: fibo:Account
    description: Financial account at a commercial bank
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
        description: Balance definition differs by context (HTTP 409 without X-USF-Context)
        contexts:
          risk:
            sql_column: eod_balance       # Risk uses end-of-day balance
          finance:
            sql_column: current_balance   # Finance uses current operating balance
      - name: currency
        ontology_property: fibo:hasCurrency
        sql_column: currency_code
        type: string
    access_policy: risk_restricted

  - name: FinancialTransaction
    ontology_class: fibo:FinancialTransaction
    description: Monetary movement between two accounts
    sql_table: transactions
    properties:
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
      - name: transaction_type
        ontology_property: fibo:hasTransactionType
        sql_column: type
        type: string
        allowed_values: [loan, derivative, bond, transfer, payment]
    access_policy: risk_restricted

metrics:
  - name: total_exposure_by_counterparty
    ontology_class: fibo:FinancialExposure
    description: Total exposure aggregated by counterparty legal entity
    type: sum
    measure: amount
    measure_entity: FinancialTransaction
    dimensions:
      - name: counterparty_name
        entity: FinancialTransaction
        property: transaction_type
        ontology_property: fibo:hasTransactionType
    contexts:
      risk:
        filter: "type IN ('loan','derivative','bond')"
      finance:
        filter: "status = 'settled'"
    time_grains: [day, month, quarter]
    time_column: "t.transaction_date"
    time_entity: FinancialTransaction
    access_policy: risk_restricted
```

**Context disambiguation in action**: Querying `balance` without `X-USF-Context` returns HTTP 409:
```json
{"error": {"code": "CONTEXT_AMBIGUOUS", "message": "Property 'balance' has different sql_column in contexts risk (eod_balance) and finance (current_balance). Specify X-USF-Context header."}}
```

---

## Worked Example 2: Healthcare (HL7 FHIR)

```yaml
sdl_version: "1.0"
tenant: general-hospital
ontology_module: fhir

contexts:
  - name: clinical
    description: Clinical care context. Active patients, current episodes.
  - name: billing
    description: Billing and reimbursement context. Coded diagnoses, procedures.
  - name: research
    description: De-identified research context. Aggregates only, no PII.

access_policies:
  - name: clinician_read
    description: Treating clinical staff
    read: [role:physician, role:nurse, role:clinical_analyst]
    pii: true
    clearance: confidential
  - name: billing_read
    description: Billing and coding staff
    read: [role:billing_analyst, role:admin]
    pii: true
    clearance: confidential
  - name: research_read
    description: Researchers — no PII, aggregates only
    read: [role:researcher, role:data_scientist]
    pii: false
    clearance: internal
    row_filter:
      role:researcher: "patient_age >= 18 AND consent_research = true"

entities:
  - name: Patient
    ontology_class: fhir:Patient
    description: A FHIR R4 Patient resource
    sql_table: patients
    properties:
      - name: patient_id
        ontology_property: fhir:Patient.id
        sql_column: patient_id
        type: string
        nullable: false
      - name: birth_date
        ontology_property: fhir:Patient.birthDate
        sql_column: birth_date
        type: date
      - name: gender
        ontology_property: fhir:Patient.gender
        sql_column: gender
        type: string
        allowed_values: [male, female, other, unknown]
      - name: primary_language
        ontology_property: fhir:Patient.communication.language
        sql_column: primary_language
        type: string
      - name: consent_research
        ontology_property: fhir:Consent.status
        sql_column: consent_research
        type: boolean
    access_policy: clinician_read

  - name: Encounter
    ontology_class: fhir:Encounter
    description: A clinical encounter (admission, visit, procedure)
    sql_table: encounters
    contexts:
      clinical:
        description: Active and completed encounters for care coordination
      billing:
        description: Encounters with billing codes attached
    properties:
      - name: encounter_id
        ontology_property: fhir:Encounter.id
        sql_column: encounter_id
        type: string
        nullable: false
      - name: patient_id
        ontology_property: fhir:Encounter.subject
        sql_column: patient_id
        type: string
        references:
          entity: Patient
          property: patient_id
      - name: encounter_class
        ontology_property: fhir:Encounter.class
        sql_column: encounter_class
        type: string
        allowed_values: [inpatient, outpatient, emergency, ambulatory, virtual]
      - name: start_date
        ontology_property: fhir:Encounter.period.start
        sql_column: start_date
        type: datetime
      - name: end_date
        ontology_property: fhir:Encounter.period.end
        sql_column: end_date
        type: datetime
      - name: length_of_stay_days
        ontology_property: fhir:Encounter.length
        type: integer
        description: Computed — differs by context
        contexts:
          clinical:
            sql_column: "EXTRACT(EPOCH FROM (COALESCE(end_date, NOW()) - start_date))/86400"
          billing:
            sql_column: billed_los_days    # Billed LOS (may differ from actual)
      - name: drg_code
        ontology_property: fhir:Encounter.diagnosis.use
        sql_column: drg_code
        type: string
    access_policy: clinician_read

  - name: Condition
    ontology_class: fhir:Condition
    description: A FHIR Condition — diagnosis or problem list item
    sql_table: conditions
    properties:
      - name: condition_id
        ontology_property: fhir:Condition.id
        sql_column: condition_id
        type: string
        nullable: false
      - name: patient_id
        ontology_property: fhir:Condition.subject
        sql_column: patient_id
        type: string
        references:
          entity: Patient
          property: patient_id
      - name: icd10_code
        ontology_property: fhir:Condition.code
        sql_column: icd10_code
        type: string
        description: ICD-10-CM diagnosis code
      - name: clinical_status
        ontology_property: fhir:Condition.clinicalStatus
        sql_column: clinical_status
        type: string
        allowed_values: [active, recurrence, relapse, inactive, remission, resolved]
      - name: onset_date
        ontology_property: fhir:Condition.onsetDateTime
        sql_column: onset_date
        type: date
      - name: severity
        ontology_property: fhir:Condition.severity
        sql_column: severity_code
        type: string
        allowed_values: [mild, moderate, severe, critical]
    access_policy: clinician_read

metrics:
  - name: avg_length_of_stay_by_drg
    ontology_class: fhir:Encounter
    description: >
      Average length of stay grouped by DRG code and encounter class.
      Used for capacity planning and billing benchmarks.
    type: avg
    measure: length_of_stay_days
    measure_entity: Encounter
    dimensions:
      - name: drg_code
        entity: Encounter
        property: drg_code
        ontology_property: fhir:Encounter.diagnosis.use
      - name: encounter_class
        entity: Encounter
        property: encounter_class
        ontology_property: fhir:Encounter.class
    contexts:
      clinical:
        description: Actual LOS for care operations
      billing:
        description: Billed LOS for reimbursement analysis
    time_grains: [month, quarter, year]
    time_column: "e.start_date"
    time_entity: Encounter
    access_policy:
      read: [role:physician, role:clinical_analyst, role:billing_analyst, role:admin]
      pii: false
      clearance: internal

  - name: readmission_count_30day
    ontology_class: fhir:Encounter
    description: >
      Count of patients readmitted within 30 days of discharge.
      Key HCAHPS quality metric.
    type: count_distinct
    measure: patient_id
    measure_entity: Encounter
    dimensions:
      - name: drg_code
        entity: Encounter
        property: drg_code
        ontology_property: fhir:Encounter.diagnosis.use
      - name: encounter_class
        entity: Encounter
        property: encounter_class
        ontology_property: fhir:Encounter.class
    default_filter: >
      e.encounter_id IN (
        SELECT e2.encounter_id FROM encounters e2
        WHERE e2.patient_id = e.patient_id
          AND e2.start_date BETWEEN e.end_date AND e.end_date + INTERVAL '30 days'
          AND e2.encounter_id != e.encounter_id
      )
    time_grains: [month, quarter, year]
    time_column: "e.start_date"
    time_entity: Encounter
    access_policy:
      read: [role:physician, role:clinical_analyst, role:admin]
      pii: false
      clearance: internal

  - name: active_condition_count_by_icd10
    ontology_class: fhir:Condition
    description: >
      Count of active diagnoses grouped by ICD-10 chapter.
      Used for population health and research analytics.
    type: count
    measure: condition_id
    measure_entity: Condition
    dimensions:
      - name: icd10_code
        entity: Condition
        property: icd10_code
        ontology_property: fhir:Condition.code
      - name: severity
        entity: Condition
        property: severity
        ontology_property: fhir:Condition.severity
    default_filter: "clinical_status = 'active'"
    contexts:
      research:
        description: Research cohort — consented, de-identified aggregation
        filter: >
          patient_id IN (
            SELECT patient_id FROM patients WHERE consent_research = true
          )
    time_grains: [month, quarter, year]
    time_column: "c.onset_date"
    time_entity: Condition
    access_policy:
      read: [role:researcher, role:data_scientist, role:clinical_analyst]
      pii: false
      clearance: internal
```

**Key healthcare SDL patterns:**
1. **PII enforcement**: `pii: true` policies trigger column masking in PROV-O output
2. **Consent-scoped research context**: row_filter enforces consent_research flag before any research query
3. **Computed column contexts**: `length_of_stay_days` uses raw SQL expression in clinical context vs stored `billed_los_days` column in billing
4. **ICD-10 / FHIR vocabulary**: All ontology_property CURIEs reference `fhir:` namespace loaded from the FHIR R4 industry module

