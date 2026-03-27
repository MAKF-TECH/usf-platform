#!/usr/bin/env python3
"""
IBM AML Dataset Loader — pilot/fibo-banking

Downloads the IBM Anti-Money Laundering dataset from Kaggle, maps columns to FIBO,
loads into PostgreSQL staging via dlt, and triggers usf-ingest.

Dataset: https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml
CSV: HI-Small_Trans.csv
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

# ── FIBO column mappings ──────────────────────────────────────────────────────
FIBO_MAPPINGS = {
    "From Bank":          "fibo-fbc:CommercialBank",
    "Account":            "fibo-fbc:Account",           # sender account
    "To Bank":            "fibo-fbc:CommercialBank",
    "Account.1":          "fibo-fbc:Account",           # receiver account
    "Amount Paid":        "fibo-fnd:hasMonetaryAmount",
    "Payment Currency":   "fibo-fnd:hasCurrency",
    "Amount Received":    "fibo-fnd:hasMonetaryAmount",
    "Receiving Currency": "fibo-fnd:hasCurrency",
    "Payment Format":     "usf:paymentFormat",
    "Is Laundering":      "usf_aml:isSuspicious",
    "Timestamp":          "fibo-fnd:transactionDate",
}


# ── Download ──────────────────────────────────────────────────────────────────
def download_dataset() -> Path:
    """Download via kaggle CLI or provide instructions for manual download."""
    if CSV_FILE.exists():
        logger.info(f"Dataset already at {CSV_FILE}")
        return CSV_FILE

    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    try:
        import subprocess
        subprocess.run(
            ["kaggle", "datasets", "download",
             "-d", "ealtman2019/ibm-transactions-for-anti-money-laundering-aml",
             "-p", str(DATASET_DIR), "--unzip"],
            check=True,
        )
    except (FileNotFoundError, Exception) as exc:
        logger.error(
            f"Kaggle download failed: {exc}\n"
            "Manual download:\n"
            "  1. https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml\n"
            f"  2. Extract HI-Small_Trans.csv to {DATASET_DIR}/\n"
            "  3. Re-run this script."
        )
        sys.exit(1)

    return CSV_FILE


# ── dlt source ────────────────────────────────────────────────────────────────
@dlt.source
def aml_transactions_source(file_path: Path):
    @dlt.resource(name="aml_transactions", write_disposition="merge", primary_key="transaction_id")
    def _transactions() -> Iterator[dict]:
        import csv
        with open(file_path, newline="", encoding="utf-8") as f:
            for i, row in enumerate(csv.DictReader(f)):
                yield {
                    "transaction_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"aml-{i}-{row.get('Timestamp','')}")),
                    "timestamp":           row.get("Timestamp"),
                    "from_bank":           row.get("From Bank"),
                    "from_account":        row.get("Account"),
                    "to_bank":             row.get("To Bank"),
                    "to_account":          row.get("Account.1"),
                    "amount_received":     _to_float(row.get("Amount Received")),
                    "receiving_currency":  row.get("Receiving Currency"),
                    "amount_paid":         _to_float(row.get("Amount Paid")),
                    "payment_currency":    row.get("Payment Currency"),
                    "payment_format":      row.get("Payment Format"),
                    "is_laundering":       row.get("Is Laundering", "0") == "1",
                    # FIBO annotation hints (metadata columns)
                    "_fibo_from_bank":     FIBO_MAPPINGS["From Bank"],
                    "_fibo_from_account":  FIBO_MAPPINGS["Account"],
                    "_fibo_amount_paid":   FIBO_MAPPINGS["Amount Paid"],
                    "_fibo_is_suspicious": FIBO_MAPPINGS["Is Laundering"],
                }
    return _transactions()


def _to_float(val: str | None) -> float | None:
    try:
        return float(val) if val else None
    except ValueError:
        return None


# ── dlt pipeline ──────────────────────────────────────────────────────────────
def run_dlt_pipeline(file_path: Path) -> None:
    pipeline = dlt.pipeline(
        pipeline_name="aml_transactions",
        destination=dlt.destinations.postgres(POSTGRES_URL),
        dataset_name="staging_fibo_banking",
    )
    load_info = pipeline.run(aml_transactions_source(file_path))
    logger.info("dlt load complete", extra={"load_info": str(load_info)})


# ── Trigger usf-ingest ────────────────────────────────────────────────────────
def register_and_trigger() -> dict:
    source_r = httpx.post(f"{INGEST_API}/sources", json={
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
    }, timeout=30)
    source_r.raise_for_status()
    source_id = source_r.json()["id"]
    logger.info(f"Registered source: {source_id}")

    job_r = httpx.post(f"{INGEST_API}/jobs", json={
        "source_id": source_id,
        "tenant_id": TENANT_ID,
        "incremental": False,
    }, timeout=30)
    job_r.raise_for_status()
    job_id = job_r.json()["id"]
    logger.info(f"Triggered job: {job_id}")
    return {"source_id": source_id, "job_id": job_id}


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.info("=== USF FIBO Banking Pilot: IBM AML Dataset ===")

    csv_path = download_dataset()
    logger.info(f"Loading {csv_path} into staging...")
    run_dlt_pipeline(csv_path)

    logger.info("Triggering usf-ingest pipeline...")
    try:
        result = register_and_trigger()
        logger.info("Pipeline triggered", extra=result)
    except httpx.HTTPError as exc:
        logger.warning(f"usf-ingest API unreachable: {exc}\nRun: docker compose up usf-ingest")

    logger.info("=== Done ===")
