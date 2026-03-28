# HL7 FHIR R4 Healthcare Ontology Module

**Module key**: `fhir` | **Standard**: HL7 FHIR R4 | **Authority**: HL7 International

---

## What is HL7 FHIR?

**Fast Healthcare Interoperability Resources (FHIR) R4** is the dominant standard for healthcare data
exchange. USF's FHIR module maps FHIR R4 resource types to OWL classes, enabling semantic queries
over clinical, administrative, and financial healthcare data.

---

## Key Classes Used in USF

| Class | CURIE | FHIR Resource | Description |
|-------|-------|---------------|-------------|
| Patient | `fhir:Patient` | Patient | Individual receiving care |
| Encounter | `fhir:Encounter` | Encounter | Clinical interaction (visit, admission) |
| Observation | `fhir:Observation` | Observation | Lab result, vital sign, clinical finding |
| Condition | `fhir:Condition` | Condition | Diagnosis or problem |
| Procedure | `fhir:Procedure` | Procedure | Clinical action performed |
| MedicationRequest | `fhir:MedicationRequest` | MedicationRequest | Drug prescription |
| Claim | `fhir:Claim` | Claim | Insurance / billing claim |
| Organization | `fhir:Organization` | Organization | Hospital, clinic, insurer |
| Practitioner | `fhir:Practitioner` | Practitioner | Clinician |

---

## Key Properties

| Property | CURIE | Description |
|----------|-------|-------------|
| `fhir:hasPatientId` | `fhir:Patient.id` | FHIR resource ID |
| `fhir:hasEncounterDate` | `fhir:Encounter.period.start` | Encounter start datetime |
| `fhir:hasEncounterClass` | `fhir:Encounter.class` | inpatient \| outpatient \| emergency |
| `fhir:hasObservationCode` | `fhir:Observation.code` | LOINC code |
| `fhir:hasObservationValue` | `fhir:Observation.valueQuantity` | Numeric value + unit |
| `fhir:hasDiagnosisCode` | `fhir:Condition.code` | ICD-10 code |
| `fhir:hasClaimAmount` | `fhir:Claim.total.value` | Total claim value |

---

## Quick Start

### 1. Schema Detection

USF detects FHIR data from tables or column names including `patient_id`, `encounter_id`,
`loinc_code`, `icd10_code`, or `npi_number`.

### 2. Column Mapping for Common Datasets

#### MIMIC-IV (MIT) Clinical Database

| MIMIC Table | FHIR Resource | SDL Entity |
|-------------|---------------|------------|
| `patients` | `fhir:Patient` | `Patient` |
| `admissions` | `fhir:Encounter` | `Encounter` |
| `labevents` | `fhir:Observation` | `LabObservation` |
| `diagnoses_icd` | `fhir:Condition` | `Diagnosis` |
| `prescriptions` | `fhir:MedicationRequest` | `Prescription` |

#### CMS Medicare Claims

| Field | FHIR Resource | Notes |
|-------|---------------|-------|
| `BENE_ID` | `fhir:Patient.id` | Beneficiary ID |
| `CLM_ID` | `fhir:Claim.id` | Claim ID |
| `CLM_FROM_DT` | `fhir:Claim.billablePeriod.start` | Service start date |
| `CLM_PMT_AMT` | `fhir:Claim.total.value` | Payment amount |
| `ICD_DGNS_CD` | `fhir:Condition.code` | ICD-10 diagnosis |

---

## Regulatory and Compliance Use Cases

### HIPAA / PHI

Mark PII fields explicitly — USF enforces clearance:

```yaml
access_policy:
  pii: true
  clearance: restricted
  read: [role:clinician, role:compliance_officer]
```

### CMS Quality Measures (HEDIS)

Map denominator/numerator populations as SDL metrics with `type: count` and
`access_policy.clearance: confidential`.

### HL7 CDA / C-CDA

USF can ingest CDA XML via the FHIR conversion pipeline.
Trigger with `POST /ingest/jobs` and `ontology_module: fhir`.

---

## FHIR Namespace Prefixes

```turtle
@prefix fhir: <http://hl7.org/fhir/> .
@prefix loinc: <http://loinc.org/rdf#> .
@prefix sct:  <http://snomed.info/id/> .
@prefix icd10: <http://hl7.org/fhir/sid/icd-10/> .
```
