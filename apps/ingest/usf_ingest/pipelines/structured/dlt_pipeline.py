from __future__ import annotations

"""dlt pipeline definitions for structured data sources.

Supports:
- CSV / Parquet files (local or S3)
- PostgreSQL tables
- Generic REST API (paginated)

All pipelines use incremental loading with dlt state tracking.
"""

from pathlib import Path
from typing import Any, Iterator

import dlt
from dlt.sources import DltResource
from dlt.sources.filesystem import filesystem, read_csv, read_parquet
from dlt.sources.sql_database import sql_database
from loguru import logger


# ── CSV / Parquet ─────────────────────────────────────────────────────────────

@dlt.source
def csv_parquet_source(
    file_path: str,
    table_name: str,
    incremental_column: str | None = None,
) -> DltResource:
    """Load CSV or Parquet files into a DLT pipeline with optional incremental."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        @dlt.resource(name=table_name, write_disposition="merge" if incremental_column else "replace")
        def _csv_resource() -> Iterator[dict]:
            import csv
            with open(file_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield dict(row)
        return _csv_resource()

    elif suffix == ".parquet":
        @dlt.resource(name=table_name, write_disposition="merge" if incremental_column else "replace")
        def _parquet_resource() -> Iterator[dict]:
            import pyarrow.parquet as pq
            table = pq.read_table(file_path)
            for batch in table.to_batches(max_chunksize=1000):
                for row in batch.to_pylist():
                    yield row
        return _parquet_resource()

    else:
        raise ValueError(f"Unsupported file type: {suffix}")


# ── PostgreSQL ────────────────────────────────────────────────────────────────

@dlt.source
def postgres_source(
    connection_string: str,
    schema: str = "public",
    table_names: list[str] | None = None,
    incremental_column: str | None = None,
) -> list[DltResource]:
    """Load PostgreSQL tables via dlt sql_database connector."""
    return sql_database(
        credentials=connection_string,
        schema=schema,
        table_names=table_names,
        incremental=dlt.sources.incremental(incremental_column) if incremental_column else None,
    )


# ── Generic REST API ──────────────────────────────────────────────────────────

@dlt.source
def rest_api_source(
    base_url: str,
    endpoint: str,
    table_name: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    pagination_key: str = "next",
    data_key: str = "data",
    incremental_param: str | None = None,
    incremental_start: str | None = None,
) -> DltResource:
    """Generic paginated REST API source."""
    import httpx

    @dlt.resource(
        name=table_name,
        write_disposition="merge" if incremental_param else "replace",
    )
    def _rest_resource(
        last_value=dlt.sources.incremental(incremental_param, initial_value=incremental_start)
        if incremental_param else None,
    ) -> Iterator[dict]:
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        req_params = dict(params or {})
        if incremental_param and last_value and last_value.last_value:
            req_params[incremental_param] = last_value.last_value

        with httpx.Client(headers=headers or {}) as client:
            while url:
                response = client.get(url, params=req_params)
                response.raise_for_status()
                body = response.json()

                records = body.get(data_key, body) if isinstance(body, dict) else body
                if isinstance(records, list):
                    yield from records

                # Follow pagination
                url = body.get(pagination_key) if isinstance(body, dict) else None
                req_params = {}  # pagination URL includes params

    return _rest_resource()


# ── Pipeline runner ───────────────────────────────────────────────────────────

def run_structured_pipeline(
    source: Any,
    pipeline_name: str,
    destination_url: str,
    dataset_name: str = "staging",
) -> dlt.Pipeline:
    """Execute a dlt pipeline and return the pipeline object."""
    pipeline = dlt.pipeline(
        pipeline_name=pipeline_name,
        destination=dlt.destinations.postgres(destination_url),
        dataset_name=dataset_name,
    )
    load_info = pipeline.run(source)
    logger.info(
        "dlt pipeline complete",
        extra={"pipeline": pipeline_name, "load_info": str(load_info)},
    )
    return pipeline
