#!/usr/bin/env python3
"""
IBM AML Dataset Loader — pilot/fibo-banking

Downloads the IBM Anti-Money Laundering (AML) dataset from Kaggle,
parses HI-Small_Trans.csv, maps columns to FIBO ontology concepts,
loads into PostgreSQL staging via dlt, and triggers the usf-ingest pipeline.

Dataset: https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Iterator

import dlt
import httpx
from loguru import logger

# ── Config ────────────────────────────────────────────────────────────────────

DATASET_DIR = Path(os.getenv("AML_DATASET_DIR", "./data"))
CSV_FILE = DATASET_DIR / "HI-Small_Trans.csv"
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://usf:usf@localhost:5432/usf")
INGEST_API = os.getenv("INGEST_API_URL", "http://localhost:8000")
TENANT_ID = os.getenv("TENANT_ID", "pilot-fibo-banking")

# ── FIBO / USF Namespace prefixes (informational mapping) ─────────────────────

FIBO_MAPPINGS = {
    "From Bank":            "fibo:CommercialBank",          # fibo-fbc:CommercialBank
    "Account":              "fibo:Account",                 # fibo-fbc:Account (sender)
    "To Bank":              "fibo:CommercialBank",          # receiving institution
    "Account.1":            "fibo:Account",                 # receiver account
    "Amount Paid":          "fibo:hasMonetaryAmount",       # fibo-fnd:hasMonetaryAmount
    "Payment Currency":     "fibo:hasCurrency",             # fibo-fnd:hasCurrency
    "Amount Received":      "fibo:hasMonetaryAmount",       # received amount
    "Receiving Currency":   "fibo:hasCurrency",             # receiving currency
    "Payment Format":       "usf:paymentFormat",            # USF extension
    "Is Laundering":        "usf_aml:isSuspicious",         # USF AML extension
    "Timestamp":            "fibo:transactionDate",         # date of transaction
}

# ── Download helper ───────────────────────────────────────────────────────────

def download_dataset() -> Path:
    """
    Download IBM AML dataset from Kaggle.

    Requirements:
      - kaggle CLI installed: pip install kaggle
      - Kaggle API credentials in ~/.kaggle/kaggle.json

    Manual fallback:
      1. Go to: https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml
      2. Click "Download" and extract to: ./data/HI-Small_Trans.csv
    """
    if CSV_FILE.exists():
        logger.info(f"Dataset already present at {CSV_FILE}")
        return CSV_FILE

    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    try:
        import subprocess
        result = subprocess.run(
            [
                "kaggle", "datasets", "download",
                "-d", "ealtman2019/ibm-transactions-for-anti-money-laundering-aml",
                "-p", str(DATASET_DIR),
                "--unzip",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Kaggle download complete", extra={"stdout": result.stdout})
    except (FileNotFoundError, Exception) as exc:
        logger.warning(
            f"Kaggle CLI download failed: {exc}\n"
            "Manual fallback:\n"
            "  1. Visit https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml\n"
            "  2. Download and extract HI-Small_Trans.csv to ./data/\n"
            f"  3. Re-run this script once {CSV_FILE} is present."
        )
        sys.exit(1)

    if not CSV_FILE.exists():
        raise FileNotFoundError(f"Expected {CSV_FILE} after download; check DATASET_DIR.")
    return CSV_FILE


# ── dlt Source ────────────────────────────────────────────────────────────────

@dlt.source
def aml_transactions_source(file_path: Path) -> dlt.sources.DltResource:
    """dlt source: parse HI-Small_Trans.csv → staging rows with FIBO annotations."""

    @dlt.resource(
        name="aml_transactions",
        write_disposition="merge",
        primary_key="transaction_id",
    )
    def _transactions() -> Iterator[dict]:
        import csv
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                yield {
                    "transaction_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"aml-{i}-{row.get('Timestamp','')}")),
                    # Raw columns
                    "timestamp": row.get("Timestamp"),
                    "from_bank": row.get("From Bank"),
                    "from_account": row.get("Account"),
                    "to_bank": row.get("To Bank"),
                    "to_account": row.get("Account.1"),
                    "amount_received": _float(row.get("Amount Received")),
                    "receiving_currency": row.get("Receiving Currency"),
                    "amount_paid": _float(row.get("Amount Paid")),
                    "payment_currency": row.get("Payment Currency"),
                    "payment_format": row.get("Payment Format"),
                    "is_laundering": row.get("Is Laundering", "0") == "1",
                    # FIBO annotation metadata
                    "_fibo_from_bank": FIBO_MAPPINGS["From Bank"],
                    "_fibo_from_account": FIBO_MAPPINGS["Account"],
                    "_fibo_to_bank": FIBO_MAPPINGS["To Bank"],
                    "_fibo_to_account": FIBO_MAPPINGS["Account.1"],
                    "_fibo_amount_paid": FIBO_MAPPINGS["Amount Paid"],
                    "_fibo_is_suspicious": FIBO_MAPPINGS["Is Laundering"],
                }

    return _transactions()


def _float(val: str | None) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except ValueError:
        return None


# ── dlt Pipeline ──────────────────────────────────────────────────────────────

def run_dlt_pipeline(file_path: Path) -> dict:
    """Load AML CSV into PostgreSQL staging via dlt."""
    pipeline = dlt.pipeline(
        pipeline_name="aml_transactions",
        destination=dlt.destinations.postgres(POSTGRES_URL),
        dataset_name="staging_fibo_banking",
    )
    source = aml_transactions_source(file_path)
    load_info = pipeline.run(source)
    logger.info("dlt pipeline complete", extra={"load_info": str(load_info)})
    return {"status": "success", "load_info": str(load_info)}


# ── Trigger usf-ingest API ────────────────────────────────────────────────────

def register_and_trigger_ingest() -> dict:
    """Register the AML staging table as a data source and trigger ingestion."""
    # 1. Register data source
    register_payload = {
        "tenant_id": TENANT_ID,
        "name": "IBM AML Transactions (HI-Small)",
        "source_type": "postgres",
        "connection_config": {
            "connection_string": POSTGRES_URL,
            "schema": "staging_fibo_banking",
            "table_names": ["aml_transactions"],
            "incremental_column": "timestamp",
        },
        "metadata": {
            "dataset": "IBM AML HI-Small",
            "kaggle_url": "https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml",
            "fibo_mappings": FIBO_MAPPINGS,
        },
    }

    response = httpx.post(f"{INGEST_API}/sources", json=register_payload, timeout=30)
    response.raise_for_status()
    source = response.json()
    source_id = source["id"]
    logger.info(f"Registered data source: {source_id}")

    # 2. Trigger ingestion job
    job_payload = {
        "source_id": source_id,
        "tenant_id": TENANT_ID,
        "incremental": False,  # First load: full
    }
    job_response = httpx.post(f"{INGEST_API}/jobs", json=job_payload, timeout=30)
    job_response.raise_for_status()
    job = job_response.json()
    logger.info(f"Triggered ingestion job: {job['id']}")

    return {"source_id": source_id, "job_id": job["id"]}


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    logger.info("=== USF FIBO Banking Pilot: AML Dataset Load ===")

    # Step 1: Download
    csv_path = download_dataset()

    # Step 2: Load into staging via dlt
    logger.info("Loading AML transactions into PostgreSQL staging...")
    dlt_result = run_dlt_pipeline(csv_path)
    logger.info("dlt load complete", extra=dlt_result)

    # Step 3: Register source + trigger usf-ingest pipeline
    logger.info("Registering source and triggering usf-ingest pipeline...")
    try:
        ingest_result = register_and_trigger_ingest()
        logger.info("Pipeline triggered", extra=ingest_result)
    except httpx.HTTPError as exc:
        logger.warning(
            f"Could not reach usf-ingest API ({INGEST_API}): {exc}\n"
            "Run 'docker compose up usf-ingest' and re-trigger via POST /jobs"
        )

    logger.info("=== AML Dataset Load Complete ===")
