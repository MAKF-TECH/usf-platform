# USF FIBO Banking Pilot — Demo Guide

> End-to-end demonstration: IBM AML dataset + FIBO ontology + USF Semantic Layer

## Prerequisites

| Requirement | Details |
|---|---|
| Docker Compose | `make up` — starts all services |
| Python 3.11+ | For running pilot scripts |
| Optional: Kaggle | For real AML dataset |

## Quick Start (2 minutes)

```bash
# 1. Start all services
make up && make health

# 2. Load synthetic pilot data (no Kaggle needed)
python pilot/fibo-banking/run_pilot.py --synthetic

# 3. Or with real Kaggle data
python pilot/fibo-banking/run_pilot.py --kaggle path/to/HI-Small_Trans.csv

# 4. Offline / dry-run mode (no Docker stack needed)
python pilot/fibo-banking/run_pilot.py --synthetic --dry-run
```

## What This Demonstrates

### 1. Structured Ingestion: CSV → dlt → PostgreSQL → FIBO-mapped KG

The AML dataset columns are mapped to FIBO ontology classes:

| CSV Column | FIBO Class | Notes |
|---|---|---|
| `From Bank` | `fibo:CommercialBank` | `fibo-fbc:CommercialBank` |
| `Account` | `fibo:Account` | Sender account |
| `Account.1` | `fibo:Account` | Receiver account |
| `Amount Paid` | `fibo:hasMonetaryAmount` | Payment amount |
| `Amount Received` | `fibo:hasMonetaryAmount` | Received amount |
| `Is Laundering` | `aml:isSuspicious` | AML flag |
| `Timestamp` | `fibo:transactionDate` | Transaction date |

```bash
# Load only (without full pilot)
python pilot/fibo-banking/load_aml_dataset.py --synthetic
```

### 2. Context Disambiguation: `balance` → 409

The SDL defines `balance` in two contexts: `risk` and `finance`.
Querying without context returns a **409 Disambiguation Required**:

```json
{
  "error": "disambiguation_required",
  "message": "Metric 'balance' exists in multiple contexts.",
  "available_contexts": [
    {"id": "risk", "description": "Risk management team"},
    {"id": "finance", "description": "Finance team"}
  ],
  "hint": "Add ?context=risk or ?context=finance"
}
```

### 3. SQL Semantic Query: Total Exposure by Counterparty

Via Wren Engine — FIBO SDL compiles to:

```sql
SELECT b.legal_name AS counterparty, SUM(t.amount_paid) AS total_exposure
FROM staging_fibo_banking.aml_transactions t
JOIN bank b ON t.from_bank = b.legal_name
WHERE t.payment_currency = 'EUR'
GROUP BY b.legal_name
ORDER BY total_exposure DESC
LIMIT 10;
```

### 4. Graph Traversal: SPARQL on QLever

Find all accounts connected to suspicious transactions:

```sparql
PREFIX usf: <https://usf.makf.tech/ontology/>

SELECT ?account ?connectedAccount ?suspiciousCount WHERE {
  ?tx a usf:FinancialTransaction ;
      usf:fromAccount ?account ;
      usf:toAccount ?connectedAccount ;
      usf:isSuspicious true .
  BIND(COUNT(?tx) AS ?suspiciousCount)
}
GROUP BY ?account ?connectedAccount
ORDER BY DESC(?suspiciousCount)
LIMIT 20
```

### 5. NL Query: Natural Language → SPARQL → Executed

```
Question: "Show suspicious transactions in EUR > 100000"
→ NL2SPARQL generates SPARQL
→ SHACL validates the generated query
→ QLever executes and returns results
→ PROV-O records full provenance chain
```

### 6. PROV-O: Full Provenance Chain

Every answer includes a PROV-O activity record:

```json
{
  "@type": "prov:Activity",
  "prov:wasAssociatedWith": "usf-platform",
  "usf:step": "nl_query",
  "usf:query": "Show suspicious transactions in EUR > 100000",
  "usf:durationMs": 42.7,
  "prov:generated": {
    "@type": "prov:Entity",
    "usf:resultSummary": "3 matching transactions found"
  }
}
```

## Expected Output

```
12:34:56 | USF FIBO Banking Pilot v1.0.0
12:34:56 |   Mode: SYNTHETIC | DRY-RUN | API: http://localhost:8000

12:34:56 | ━━━ STEP 1: Load Data ━━━
12:34:56 |   ✓ Generated 100 synthetic rows
12:34:56 |   Suspicious transactions: 5/100
12:34:56 |   FIBO mappings active: From Bank→fibo:CommercialBank, Account→fibo:Account, ...

12:34:56 | ━━━ STEP 2: SHACL Validation ━━━
12:34:56 |   ✓ VALID — 5 sample transactions validated

12:34:56 | ━━━ STEP 3: Structured Ingestion ━━━
12:34:56 |   [DRY RUN] Would POST 100 rows to http://localhost:8000/ingest

12:34:56 | ━━━ STEP 4: SQL Query — Total Exposure by Counterparty ━━━
12:34:56 |   ✓ Top counterparties by total exposure:
12:34:56 |     Deutsche Bank: 12,450,230.00
12:34:56 |     HSBC: 9,871,440.50
12:34:56 |     BNP Paribas: 8,234,120.75

12:34:56 | ━━━ STEP 5: SPARQL — Connected Accounts Graph Traversal ━━━
12:34:56 |   ✓ Found 5 suspicious transactions
12:34:56 |   ✓ Top connected account pairs (AML risk):
12:34:56 |     ACCABC12345 → ACCDEF67890 (2 suspicious txns)

12:34:56 | ━━━ STEP 6: NL Query ━━━
12:34:56 |   Question: "Show suspicious transactions in EUR > 100000"
12:34:56 |   [DRY RUN] In-memory result: 1 matching transactions

12:34:56 | ━━━ STEP 7: Context Disambiguation Test ━━━
12:34:56 |   Query: "balance" (no context specified)
12:34:56 |   [DRY RUN] Expected 409 response: {...}
12:34:56 |   ✓ Disambiguation working — 'balance' has 2 contexts (risk, finance)

12:34:57 | ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
12:34:57 |                 USF FIBO Banking Pilot — SUMMARY
12:34:57 | ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
12:34:57 |   ✓ Step 1 — Data load:        ok
12:34:57 |   ✓ Step 2 — SHACL valid:      valid
12:34:57 |   ✓ Step 3 — Ingest:           dry-run
12:34:57 |   ✓ Step 4 — SQL exposure:     5 counterparties
12:34:57 |   ✓ Step 5 — SPARQL graph:     5 suspicious txns
12:34:57 |   ✓ Step 6 — NL query:         1
12:34:57 |   ✓ Step 7 — Disambiguation:   simulated-409
```

## Loading Real Kaggle Data

```bash
# 1. Install Kaggle CLI
pip install kaggle

# 2. Set up credentials
# Download kaggle.json from https://www.kaggle.com/settings → API
mkdir -p ~/.kaggle && cp kaggle.json ~/.kaggle/

# 3. Download the dataset
kaggle datasets download -d ealtman2019/ibm-transactions-for-anti-money-laundering-aml \
  -p ./data --unzip

# 4. Run pilot with real data
python pilot/fibo-banking/run_pilot.py --kaggle ./data/HI-Small_Trans.csv
```

## Architecture

```
HI-Small_Trans.csv / synthetic data
         ↓
   load_aml_dataset.py
         ↓ (dlt pipeline)
   PostgreSQL staging_fibo_banking.aml_transactions
         ↓
   usf-ingest API → FIBO-mapped Knowledge Graph
         ↓
   ┌─────────────────────────────────┐
   │  QLever (SPARQL endpoint)       │
   │  Wren Engine (SQL semantic)     │
   │  NL2SPARQL service              │
   │  SHACL validator                │
   └─────────────────────────────────┘
         ↓
   PROV-O provenance records
```

## Files

```
pilot/fibo-banking/
├── DEMO.md                    # This guide
├── README.md                  # Overview
├── requirements.txt           # Standalone deps
├── load_aml_dataset.py        # Data loader + FIBO mapper
├── run_pilot.py               # End-to-end pilot runner
└── queries/
    ├── 01_total_exposure.sparql
    ├── 02_connected_accounts.sparql
    ├── 03_suspicious_transactions.sparql
    └── 04_nl_demo.txt
```

## SDL Reference

The FIBO SDL (`packages/ontologies/fibo/sdl/banking_starter.yaml`) defines:
- `BankAccount` → `fibo-fbc-ps:Account`
- `CommercialBank` → `fibo-be-le:LegalEntity`
- `FinancialTransaction` → FIBO transaction class
- `balance` metric (2 contexts: risk + finance → triggers 409)
- `total_exposure_by_counterparty` metric (2 contexts: risk + finance)
- Access policies: `risk_analyst` reads risk context, `finance_analyst` reads finance context
