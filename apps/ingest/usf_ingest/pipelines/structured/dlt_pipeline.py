from __future__ import annotations

"""dlt pipeline definitions for structured data sources (CSV, Parquet, PostgreSQL, REST API)."""

from pathlib import Path
from typing import Any, Iterator

import dlt
from loguru import logger


@dlt.source
def csv_parquet_source(file_path: str, table_name: str, incremental_column: str | None = None):
    path = Path(file_path)

    @dlt.resource(name=table_name, write_disposition="merge" if incremental_column else "replace")
    def _resource() -> Iterator[dict]:
        if path.suffix.lower() == ".csv":
            import csv
            with open(file_path, newline="", encoding="utf-8") as f:
                yield from csv.DictReader(f)
        elif path.suffix.lower() == ".parquet":
            import pyarrow.parquet as pq
            for batch in pq.read_table(file_path).to_batches(max_chunksize=1000):
                yield from batch.to_pylist()
        else:
            raise ValueError(f"Unsupported: {path.suffix}")

    return _resource()


@dlt.source
def postgres_source(
    connection_string: str,
    schema: str = "public",
    table_names: list[str] | None = None,
    incremental_column: str | None = None,
):
    from dlt.sources.sql_database import sql_database
    return sql_database(
        credentials=connection_string,
        schema=schema,
        table_names=table_names,
        incremental=dlt.sources.incremental(incremental_column) if incremental_column else None,
    )


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
):
    import httpx

    @dlt.resource(name=table_name, write_disposition="merge" if incremental_param else "replace")
    def _resource(
        last_value=dlt.sources.incremental(incremental_param, initial_value=incremental_start) if incremental_param else None,
    ) -> Iterator[dict]:
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        req_params = dict(params or {})
        if incremental_param and last_value and last_value.last_value:
            req_params[incremental_param] = last_value.last_value

        with httpx.Client(headers=headers or {}) as client:
            while url:
                r = client.get(url, params=req_params)
                r.raise_for_status()
                body = r.json()
                records = body.get(data_key, body) if isinstance(body, dict) else body
                if isinstance(records, list):
                    yield from records
                url = body.get(pagination_key) if isinstance(body, dict) else None
                req_params = {}

    return _resource()


def run_structured_pipeline(source: Any, pipeline_name: str, destination_url: str, dataset_name: str = "staging") -> dlt.Pipeline:
    pipeline = dlt.pipeline(
        pipeline_name=pipeline_name,
        destination=dlt.destinations.postgres(destination_url),
        dataset_name=dataset_name,
    )
    load_info = pipeline.run(source)
    logger.info("dlt pipeline complete", extra={"pipeline": pipeline_name, "load_info": str(load_info)})
    return pipeline
