# FIBO Banking Ontology Module

**Module key**: `fibo` | **Standard**: FIBO OWL-DL | **Authority**: EDM Council + OMG

---

## What is FIBO?

The **Financial Industry Business Ontology (FIBO)** is an OWL-DL ontology suite maintained jointly by
the EDM Council and the Object Management Group (OMG). It provides a formal, machine-readable vocabulary
for financial instruments, legal entities, markets, and regulatory reporting.

FIBO consists of ~50 modules covering everything from basic legal entities to derivatives pricing.
USF loads the subset most relevant to commercial banking, AML, and regulatory reporting.

---

## Key Classes Used in USF

| Class | CURIE | FIBO IRI | Description |
|-------|-------|----------|-------------|
| Legal Entity | `fibo:LegalEntity` | `fibo-be-le-lp:LegalPerson` | Any legal person — bank, corporate, individual |
| Commercial Bank | `fibo:CommercialBank` | `fibo-be-fi-fi:CommercialBank` | Deposit-taking, loan-making institution |
| Account | `fibo:Account` | `fibo-fbc-pas-caa:Account` | Financial account held at an institution |
| Financial Transaction | `fibo:FinancialTransaction` | `fibo-fbc-fi-fi:FinancialInstrument` | Monetary exchange between parties |
| Financial Exposure | `fibo:FinancialExposure` | `fibo-fbc-dae-dbt:FinancialObligation` | Credit or market risk exposure |
| Suspicious Activity | `fibo:SuspiciousActivity` | USF extension | AML flag (pilot extension) |
| Currency | `fibo:Currency` | `fibo-fnd-acc-cur:Currency` | ISO 4217 currency |
| LEI | `fibo:hasLEI` | `fibo-be-le-lei:hasLEI` | Legal Entity Identifier |

---

## Key Properties

| Property | CURIE | Description |
|----------|-------|-------------|
| `fibo:hasIdentifier` | `fibo-fnd-rel-rel:hasIdentity` | Generic identifier |
| `fibo:hasLegalName` | `fibo-be-le-lp:hasLegalName` | Legal name of entity |
| `fibo:hasLEI` | `fibo-be-le-lei:hasLEI` | 20-char LEI code |
| `fibo:hasBalance` | `fibo-fbc-pas-caa:hasBalance` | Account balance |
| `fibo:hasMonetaryAmount` | `fibo-fnd-acc-cur:hasMonetaryAmount` | Transaction amount |
| `fibo:hasTransactionDate` | `fibo-fbc-fi-fi:hasTradeDate` | Date of transaction |
| `fibo:hasSWIFTCode` | `fibo-fbc-fct-bci:hasBICIdentifier` | SWIFT BIC code |
| `lcc:hasCountry` | `lcc-cr:usesAdHocName` | Country reference (LCC module) |

---

## Quick Start

### 1. Auto-detection

USF detects the banking industry from your schema if you have tables like `accounts`, `transactions`,
`legal_entities`, or `banks`. The FIBO module loads automatically.

### 2. Starter SDL Template

Start with the bundled template:

```bash
curl http://localhost:8003/ontology/fibo/templates/banking_starter.yaml \
  > my_bank_sdl.yaml
```

Or reference the complete pilot example at
`packages/sdl-schema/usf_sdl/examples/fibo_banking.yaml`.

### 3. Validate and Publish

```bash
curl -X POST http://localhost:8003/validate \
  -H "Content-Type: application/json" \
  -d "{\"yaml_content\": $(cat my_bank_sdl.yaml | jq -Rs .)}"

curl -X POST http://localhost:8003/publish \
  -H "Content-Type: application/json" \
  -d '{"yaml_content": "...", "version": "v1", "changelog": "Initial banking SDL"}'
```

---

## Column Mapping for Common Datasets

### IBM AML Transactions Dataset (HI-Small / LargeSim)

| CSV Column | FIBO Class / Property | SDL Entity.Property |
|------------|-----------------------|---------------------|
| `From Bank` | `fibo:CommercialBank` / `rdfs:label` | `CommercialBank.bank_name` |
| `Account` (from) | `fibo:Account` / `fibo:hasIdentifier` | `BankAccount.account_id` |
| `To Bank` | `fibo:CommercialBank` / `rdfs:label` | `CommercialBank.bank_name` |
| `Account` (to) | `fibo:Account` / `fibo:hasIdentifier` | `BankAccount.account_id` |
| `Amount Received` | `fibo:hasMonetaryAmount` | `FinancialTransaction.amount` |
| `Receiving Currency` | `fibo:hasCurrency` | `FinancialTransaction.currency` |
| `Payment Format` | `fibo:hasTransactionType` | `FinancialTransaction.transaction_type` |
| `Is Laundering` | USF `fibo:hasSuspiciousFlag` | `FinancialTransaction.is_laundering` |
| `Timestamp` | `fibo:hasTransactionDate` | `FinancialTransaction.transaction_date` |

### SWIFT MT103 Messages

| MT103 Field | FIBO Property | Notes |
|-------------|---------------|-------|
| Field 20 (TRN) | `fibo:hasIdentifier` | Transaction reference |
| Field 32A (Value Date / Amount) | `fibo:hasMonetaryAmount` + date | Split on ingest |
| Field 50K (Ordering Customer) | `fibo:LegalEntity.hasLegalName` | Sender |
| Field 57A (Account with Institution) | `fibo:CommercialBank.hasBICIdentifier` | SWIFT BIC |
| Field 59 (Beneficiary) | `fibo:LegalEntity` | Receiver |

---

## Regulatory Use Cases

### BCBS 239 — Risk Data Aggregation and Reporting

USF maps directly to BCBS 239 Principle 6 (Adaptability): the semantic layer separates
risk data definitions from physical schemas. The `risk` context in `fibo_banking.yaml`
provides EOD balances suitable for BCBS 239 reports.

Key metrics: `total_exposure_by_counterparty`, `suspicious_transaction_count`

### Basel III / CRR — Capital Requirements

| Basel III Concept | USF Mapping |
|-------------------|-------------|
| Counterparty Credit Risk (CCR) | `total_exposure_by_counterparty` context=risk |
| Large Exposure Limit (LEL) | `total_exposure_by_counterparty` filter by threshold |
| Liquidity Coverage Ratio (LCR) | `transaction_volume_by_type` type=liquid_assets |

### FINREP / COREP (EBA)

The `finance` context provides settled, GAAP-aligned figures suitable for FINREP templates.
The `risk` context provides regulatory capital figures for COREP.

Use `GET /query/explain/{metric}?context=finance` to see the exact SQL mapped to each FINREP row.

### AML / CFT (FATF Recommendation 16)

The `suspicious_transaction_count` metric with `is_laundering = true` filter surfaces
IBM AML-flagged transactions. In production, replace with your AML scoring model output.

---

## FIBO Namespace Prefixes

```turtle
@prefix fibo:     <https://spec.edmcouncil.org/fibo/ontology/> .
@prefix fibo-be:  <https://spec.edmcouncil.org/fibo/ontology/BE/> .
@prefix fibo-fbc: <https://spec.edmcouncil.org/fibo/ontology/FBC/> .
@prefix fibo-fnd: <https://spec.edmcouncil.org/fibo/ontology/FND/> .
@prefix lcc:      <https://www.omg.org/spec/LCC/> .
@prefix rdfs:     <http://www.w3.org/2000/01/rdf-schema#> .
```
