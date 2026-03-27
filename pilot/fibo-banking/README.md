# FIBO Banking Pilot — IBM AML Dataset

## Overview

This pilot demonstrates the full USF ingestion pipeline using the [IBM Anti-Money Laundering (AML) Transactions dataset](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml), mapped to FIBO ontology concepts.

## Dataset

**Source:** IBM Transactions for Anti-Money Laundering (AML) — Kaggle  
**File:** `HI-Small_Trans.csv` (high-illicit, small network variant)

### Columns

| Column | Type | FIBO Mapping |
|--------|------|--------------|
| Timestamp | datetime | `fibo:transactionDate` |
| From Bank | string | `fibo-fbc:CommercialBank` |
| Account | string | `fibo-fbc:Account` (sender) |
| To Bank | string | `fibo-fbc:CommercialBank` (receiver) |
| Account.1 | string | `fibo-fbc:Account` (receiver) |
| Amount Received | decimal | `fibo-fnd:hasMonetaryAmount` |
| Receiving Currency | string | `fibo-fnd:hasCurrency` |
| Amount Paid | decimal | `fibo-fnd:hasMonetaryAmount` |
| Payment Currency | string | `fibo-fnd:hasCurrency` |
| Payment Format | string | `usf:paymentFormat` |
| Is Laundering | boolean | `usf_aml:isSuspicious` |

## Pipeline Architecture

```
HI-Small_Trans.csv
    ↓ (load_aml_dataset.py)
dlt pipeline (aml_transactions_source)
    ↓
PostgreSQL staging (staging_fibo_banking.aml_transactions)
    ↓
usf-ingest POST /sources  → register data source
usf-ingest POST /jobs     → trigger structured pipeline
    ↓
schema_introspect.py → introspect PostgreSQL schema
r2rml_generator.py  → generate R2RML with FIBO hints
ontop_loader.py     → upload to Ontop sidecar → Virtual KG
    ↓
OpenLineage events (USFIngestionFacet) → Redpanda → usf-audit
```

## Running the Pilot

### Prerequisites

1. **Kaggle credentials** (for automatic download):
   ```bash
   pip install kaggle
   mkdir -p ~/.kaggle
   echo '{"username":"YOUR_USERNAME","key":"YOUR_KEY"}' > ~/.kaggle/kaggle.json
   chmod 600 ~/.kaggle/kaggle.json
   ```

2. **Manual download** (alternative):
   - Visit: https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml
   - Download and extract `HI-Small_Trans.csv` to `pilot/fibo-banking/data/`

### Run

```bash
# With docker compose (recommended)
docker compose up -d postgres usf-ingest usf-worker
export DATABASE_URL=postgresql://usf:usf@localhost:5432/usf
export INGEST_API_URL=http://localhost:8001  # check compose port
export TENANT_ID=pilot-fibo-banking

cd pilot/fibo-banking
python load_aml_dataset.py
```

### Verify

```bash
# Check staging table
psql $DATABASE_URL -c "SELECT COUNT(*) FROM staging_fibo_banking.aml_transactions;"

# Check ingestion jobs
curl http://localhost:8001/jobs | jq .

# Check audit log
curl http://localhost:8003/log?tenant_id=pilot-fibo-banking | jq .
```

## Demo Query

Once loaded, query the FIBO-aligned AML data via USF:

```sql
-- "What is the total suspicious transaction volume from EU banks?"
SELECT
  from_bank,
  SUM(amount_paid) as total_suspicious_amount,
  COUNT(*) as transaction_count
FROM staging_fibo_banking.aml_transactions
WHERE is_laundering = true
GROUP BY from_bank
ORDER BY total_suspicious_amount DESC
LIMIT 20;
```

Or via USF SDL (semantic query layer):
```
context: fibo-banking
metric: total_suspicious_exposure
filter: is_laundering = true, payment_currency = "USD"
```

## FIBO Namespace References

- `fibo-fbc`: https://spec.edmcouncil.org/fibo/ontology/FBC/
- `fibo-fnd`: https://spec.edmcouncil.org/fibo/ontology/FND/
- `usf`: https://usf.platform/ontology/
- `usf_aml`: https://usf.platform/ontology/aml/
