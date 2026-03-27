# FIBO Banking Pilot — IBM AML Dataset

## Overview

This pilot demonstrates the full USF ingestion pipeline using the [IBM Anti-Money Laundering (AML) Transactions dataset](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml), mapped to FIBO ontology concepts.

## Dataset

**File:** `HI-Small_Trans.csv` — high-illicit, small network variant

| Column | FIBO Mapping |
|--------|-------------|
| Timestamp | `fibo-fnd:transactionDate` |
| From Bank | `fibo-fbc:CommercialBank` |
| Account (sender) | `fibo-fbc:Account` |
| To Bank | `fibo-fbc:CommercialBank` |
| Account.1 (receiver) | `fibo-fbc:Account` |
| Amount Paid | `fibo-fnd:hasMonetaryAmount` |
| Payment Currency | `fibo-fnd:hasCurrency` |
| Amount Received | `fibo-fnd:hasMonetaryAmount` |
| Receiving Currency | `fibo-fnd:hasCurrency` |
| Payment Format | `usf:paymentFormat` |
| Is Laundering | `usf_aml:isSuspicious` |

## Pipeline

```
HI-Small_Trans.csv
    ↓ dlt (aml_transactions_source)
PostgreSQL staging_fibo_banking.aml_transactions
    ↓ usf-ingest POST /sources + POST /jobs
schema_introspect → r2rml_generator → ontop_loader → Virtual KG
    ↓ OpenLineage events → Redpanda → usf-audit
```

## Quickstart

```bash
# 1. Get Kaggle credentials
pip install kaggle
echo '{"username":"...","key":"..."}' > ~/.kaggle/kaggle.json

# OR manually download HI-Small_Trans.csv to ./data/

# 2. Run
cd pilot/fibo-banking
export DATABASE_URL=postgresql://usf:usf@localhost:5432/usf
export INGEST_API_URL=http://localhost:8001
python load_aml_dataset.py

# 3. Verify
psql $DATABASE_URL -c "SELECT COUNT(*) FROM staging_fibo_banking.aml_transactions;"
curl $INGEST_API_URL/jobs | jq .
```

## Namespaces

- `fibo-fbc`: `https://spec.edmcouncil.org/fibo/ontology/FBC/`
- `fibo-fnd`: `https://spec.edmcouncil.org/fibo/ontology/FND/`
- `usf`: `https://usf.platform/ontology/`
- `usf_aml`: `https://usf.platform/ontology/aml/`
