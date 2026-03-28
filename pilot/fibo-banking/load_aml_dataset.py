#!/usr/bin/env python3
"""
IBM AML Dataset Loader — pilot/fibo-banking

Downloads the IBM Anti-Money Laundering (AML) dataset from Kaggle,
parses HI-Small_Trans.csv, maps columns to FIBO ontology concepts,
loads into PostgreSQL staging via dlt, and triggers the usf-ingest pipeline.

Dataset: https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml

Column → FIBO mapping:
  From Bank       → fibo:CommercialBank  (fibo-fbc:CommercialBank)
  Account         → fibo:Account         (sender account)
  Account.1       → fibo:Account         (receiver account)
  Amount Paid     → fibo:hasMonetaryAmount
  Amount Received → fibo:hasMonetaryAmount
  Is Laundering   → aml:isSuspicious
  Timestamp       → fibo:transactionDate
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Iterator

try:
    from loguru import logger
except ImportError:
    import logging as _logging
    import sys as _sys

    _logging.basicConfig(stream=_sys.stderr, level=_logging.INFO, format="%(asctime)s | %(message)s")
    _log = _logging.getLogger("loader")

    class _Logger:
        def info(self, msg, *a, **kw): _log.info(str(msg))
        def warning(self, msg, *a, **kw): _log.warning(str(msg))
        def remove(self, *a): pass
        def add(self, *a, **kw): pass

    logger = _Logger()

# ── Config ────────────────────────────────────────────────────────────────────

DATASET_DIR = Path(os.getenv("AML_DATASET_DIR", "./data"))
CSV_FILE = DATASET_DIR / "HI-Small_Trans.csv"
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://usf:usf@localhost:5432/usf")
INGEST_API = os.getenv("INGEST_API_URL", "http://localhost:8000")
TENANT_ID = os.getenv("TENANT_ID", "pilot-fibo-banking")

# ── FIBO / USF Namespace prefixes ─────────────────────────────────────────────
# Full mapping per packages/ontologies/fibo/mappings/aml_dataset.yaml

FIBO_MAPPINGS = {
    "From Bank":          "fibo:CommercialBank",     # fibo-fbc:CommercialBank
    "Account":            "fibo:Account",            # sender account
    "To Bank":            "fibo:CommercialBank",     # receiving institution
    "Account.1":          "fibo:Account",            # receiver account
    "Amount Paid":        "fibo:hasMonetaryAmount",  # fibo-fnd:hasMonetaryAmount (paid)
    "Payment Currency":   "fibo:hasCurrency",        # payment currency
    "Amount Received":    "fibo:hasMonetaryAmount",  # received amount
    "Receiving Currency": "fibo:hasCurrency",        # receiving currency
    "Payment Format":     "usf:paymentFormat",       # USF extension
    "Is Laundering":      "aml:isSuspicious",        # USF AML extension
    "Timestamp":          "fibo:transactionDate",    # date of transaction
}


# ── Synthetic data generator ──────────────────────────────────────────────────

def generate_synthetic_aml_data(n: int = 100) -> list[dict]:
    """Generate synthetic AML transaction data matching IBM AML schema.

    Use this when Kaggle dataset not available.
    No external dependencies required — stdlib only.
    """
    import random
    import uuid as _uuid

    banks = ["Deutsche Bank", "BNP Paribas", "HSBC", "Barclays", "Santander"]
    currencies = ["EUR", "USD", "GBP", "CHF"]
    formats = ["Wire", "Cheque", "Credit Card", "Cash", "ACH"]

    rows = []
    for i in range(n):
        rows.append({
            "Timestamp": (
                f"2023-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
                f"T{random.randint(0, 23):02d}:00:00"
            ),
            "From Bank":          random.choice(banks),
            "Account":            f"ACC{_uuid.uuid4().hex[:8].upper()}",
            "To Bank":            random.choice(banks),
            "Account.1":          f"ACC{_uuid.uuid4().hex[:8].upper()}",
            "Amount Received":    round(random.uniform(100, 1_000_000), 2),
            "Receiving Currency": random.choice(currencies),
            "Amount Paid":        round(random.uniform(100, 1_000_000), 2),
            "Payment Currency":   random.choice(currencies),
            "Payment Format":     random.choice(formats),
            "Is Laundering":      random.choices([0, 1], weights=[95, 5])[0],
        })
    return rows


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
        logger.info(f"Kaggle download complete: {result.stdout}")
    except (FileNotFoundError, Exception) as exc:
        logger.warning(
            f"Kaggle CLI download failed: {exc}\n"
            "Fallback options:\n"
            "  A) Run with --synthetic flag for 100 synthetic rows\n"
            "  B) Visit https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml\n"
            f"     Download HI-Small_Trans.csv to: {DATASET_DIR}"
        )
        raise

    if not CSV_FILE.exists():
        raise FileNotFoundError(f"Expected {CSV_FILE} after download")
    return CSV_FILE


# ── dlt Source ────────────────────────────────────────────────────────────────

def _float(val: str | None) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _make_row(row: dict, index: int) -> dict:
    """Map a raw CSV/synthetic row to a staging row with FIBO annotations."""
    return {
        "transaction_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"aml-{index}-{row.get('Timestamp', '')}")),
        # Mapped fields
        "timestamp":          row.get("Timestamp"),
        "from_bank":          row.get("From Bank"),          # → fibo:CommercialBank
        "from_account":       row.get("Account"),            # → fibo:Account
        "to_bank":            row.get("To Bank"),            # → fibo:CommercialBank
        "to_account":         row.get("Account.1"),          # → fibo:Account
        "amount_received":    _float(row.get("Amount Received")),  # → fibo:hasMonetaryAmount
        "receiving_currency": row.get("Receiving Currency"), # → fibo:hasCurrency
        "amount_paid":        _float(row.get("Amount Paid")),      # → fibo:hasMonetaryAmount
        "payment_currency":   row.get("Payment Currency"),  # → fibo:hasCurrency
        "payment_format":     row.get("Payment Format"),    # → usf:paymentFormat
        "is_suspicious":      str(row.get("Is Laundering", "0")) in ("1", 1, True),  # → aml:isSuspicious
        # FIBO annotation metadata
        "_fibo_from_bank":       FIBO_MAPPINGS["From Bank"],
        "_fibo_from_account":    FIBO_MAPPINGS["Account"],
        "_fibo_to_bank":         FIBO_MAPPINGS["To Bank"],
        "_fibo_to_account":      FIBO_MAPPINGS["Account.1"],
        "_fibo_amount_paid":     FIBO_MAPPINGS["Amount Paid"],
        "_fibo_is_suspicious":   FIBO_MAPPINGS["Is Laundering"],
    }


def _csv_rows(file_path: Path) -> Iterator[dict]:
    import csv
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            yield _make_row(row, i)


def _synthetic_rows(n: int = 100) -> Iterator[dict]:
    for i, row in enumerate(generate_synthetic_aml_data(n)):
        yield _make_row(row, i)


def build_dlt_source(rows: Iterator[dict]):
    """Build a dlt source from an iterator of rows."""
    try:
        import dlt

        @dlt.source
        def aml_source():
            @dlt.resource(
                name="aml_transactions",
                write_disposition="merge",
                primary_key="transaction_id",
            )
            def _transactions():
                yield from rows

            return _transactions()

        return aml_source()
    except ImportError:
        logger.warning("dlt not installed — skipping pipeline. pip install dlt")
        return None


# ── dlt Pipeline ──────────────────────────────────────────────────────────────

def run_dlt_pipeline(rows: Iterator[dict]) -> dict:
    """Load AML rows into PostgreSQL staging via dlt."""
    try:
        import dlt
    except ImportError:
        logger.warning("dlt not installed — skipping pipeline (install with: pip install dlt)")
        return {"status": "skipped", "reason": "dlt not installed"}

    pipeline = dlt.pipeline(
        pipeline_name="aml_transactions",
        destination=dlt.destinations.postgres(POSTGRES_URL),
        dataset_name="staging_fibo_banking",
    )
    source = build_dlt_source(rows)
    load_info = pipeline.run(source)
    logger.info(f"dlt pipeline complete: {load_info}")
    return {"status": "success", "load_info": str(load_info)}


# ── Trigger usf-ingest API ────────────────────────────────────────────────────

def register_and_trigger_ingest() -> dict:
    """Register the AML staging table as a data source and trigger ingestion."""
    try:
        import httpx
    except ImportError:
        logger.warning("httpx not installed — skipping API registration. pip install httpx")
        return {"status": "skipped", "reason": "httpx not installed"}

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
    source_id = response.json()["id"]
    logger.info(f"Registered data source: {source_id}")

    job_response = httpx.post(
        f"{INGEST_API}/jobs",
        json={"source_id": source_id, "tenant_id": TENANT_ID, "incremental": False},
        timeout=30,
    )
    job_response.raise_for_status()
    job_id = job_response.json()["id"]
    logger.info(f"Triggered ingestion job: {job_id}")

    return {"source_id": source_id, "job_id": job_id}


# ── Main ──────────────────────────────────────────────────────────────────────

def main(synthetic: bool = False, csv_path: Path | None = None) -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.info("=== USF FIBO Banking Pilot: AML Dataset Load ===")
    logger.info(f"FIBO mappings: {FIBO_MAPPINGS}")

    if synthetic:
        logger.info("Using synthetic AML data (100 rows)")
        rows = list(_synthetic_rows(100))
        logger.info(f"Generated {len(rows)} synthetic rows")
        logger.info(f"Sample row: {rows[0]}")
        dlt_result = run_dlt_pipeline(iter(rows))
    else:
        path = csv_path or download_dataset()
        logger.info(f"Loading from CSV: {path}")
        dlt_result = run_dlt_pipeline(_csv_rows(path))

    logger.info(f"dlt result: {dlt_result}")

    logger.info("Registering source and triggering usf-ingest pipeline...")
    try:
        ingest_result = register_and_trigger_ingest()
        logger.info(f"Pipeline triggered: {ingest_result}")
    except Exception as exc:
        logger.warning(
            f"Could not reach usf-ingest API ({INGEST_API}): {exc}\n"
            "Run 'make up' and re-trigger via POST /jobs"
        )

    logger.info("=== AML Dataset Load Complete ===")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="USF FIBO Banking AML Dataset Loader")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic data (no Kaggle needed)")
    parser.add_argument("--csv", type=Path, default=None, help="Path to HI-Small_Trans.csv")
    args = parser.parse_args()

    main(synthetic=args.synthetic, csv_path=args.csv)
