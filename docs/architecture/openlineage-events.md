# USF OpenLineage Event Specification

**Version**: 1.0.0  
**Status**: FROZEN  
**Date**: 2026-03-27  
**Author**: usf-architect

> USF emits OpenLineage events to Redpanda topic `usf.lineage.events`.
> These events are consumed by `usf-audit` and persisted to PostgreSQL.
> They are also the basis for regulatory lineage export.

---

## Overview

USF uses [OpenLineage](https://openlineage.io/) 1.x with custom facets.
Events are emitted via `aiokafka` producer to Redpanda, then consumed by `usf-audit`.

All events follow the OpenLineage `RunEvent` structure:
```json
{
  "eventType": "START | COMPLETE | FAIL | ABORT",
  "eventTime": "2026-03-27T10:00:00.000Z",
  "run": { "runId": "uuid", "facets": { ... } },
  "job": { "namespace": "usf.ingest.structured", "name": "acme-bank.warehouse.batch-001", "facets": { ... } },
  "inputs": [ { "namespace": "...", "name": "...", "facets": { ... } } ],
  "outputs": [ { "namespace": "...", "name": "...", "facets": { ... } } ],
  "producer": "https://github.com/MAKF-TECH/usf-platform",
  "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json"
}
```

---

## Job Namespaces

| Namespace | Description | Service |
|-----------|-------------|---------|
| `usf.ingest.structured` | dlt-based structured ingestion (Postgres, CSV, Snowflake) | usf-ingest |
| `usf.ingest.unstructured` | Document ingestion (PDF, DOCX, HTML via Docling + LangExtract) | usf-ingest |
| `usf.ingest.semi` | Semi-structured ingestion (FHIR, CIM, JSON-LD) | usf-ingest |
| `usf.sdl.compile` | SDL YAML → OWL + SQL compilation events | usf-sdl |
| `usf.sdl.publish` | SDL version publish events | usf-sdl |
| `usf.query.execute` | Query execution lineage (for audit trail) | usf-query |
| `usf.kg.validate` | pySHACL validation batch events | usf-kg |
| `usf.kg.ontology_load` | Ontology module load events | usf-kg |

---

## Dataset Naming Convention

Datasets represent inputs and outputs in the lineage graph.

### Input Datasets (sources)

| Source Type | Namespace | Name Pattern | Example |
|------------|-----------|-------------|---------|
| PostgreSQL table | `postgres://{host}:{port}/{db}` | `{schema}.{table}` | `postgres://db.acme.internal:5432/warehouse.public.transactions` |
| CSV file | `file://{path_or_bucket}` | `{filename}` | `file://s3://acme-data/kaggle-aml.csv` |
| PDF document | `file://{path_or_bucket}` | `{filename}` | `file://s3://acme-docs/basel-iii-annex-4.pdf` |
| FHIR Bundle | `fhir://{server_url}` | `Bundle/{id}` | `fhir://fhir.acme.internal/Bundle/12345` |
| API endpoint | `api://{host}` | `{path}` | `api://bloomberg.acme.internal/entities/bank` |

### Output Datasets (KG named graphs)

| Output Type | Namespace | Name Pattern | Example |
|------------|-----------|-------------|---------|
| QLever named graph | `usf://qlever` | `{named_graph_uri}` | `usf://qlever/acme-bank/instance/warehouse/batch-001` |
| Quarantine graph | `usf://qlever` | `{quarantine_uri}` | `usf://qlever/acme-bank/quarantine/2026-03-27` |
| Schema graph | `usf://qlever` | `{schema_uri}` | `usf://qlever/acme-bank/schema/v2` |

---

## Custom Facets

### Run Facets

#### `usf:ExtractionModelFacet`
Attached to runs that use an LLM for extraction (unstructured path).

```json
{
  "_producer": "https://github.com/MAKF-TECH/usf-platform",
  "_schemaURL": "https://usf.makf.tech/openlineage/facets/extraction-model/v1",
  "model_name": "gemini-1.5-pro",
  "model_version": "1.5-001",
  "provider": "google",
  "temperature": 0.0,
  "prompt_template_version": "fibo-few-shot-v2",
  "max_tokens": 4096
}
```

#### `usf:OntologyVersionFacet`
Attached to all runs. Records which ontology module version was active.

```json
{
  "_producer": "https://github.com/MAKF-TECH/usf-platform",
  "_schemaURL": "https://usf.makf.tech/openlineage/facets/ontology-version/v1",
  "module": "fibo",
  "version": "2024-Q4",
  "named_graph_uri": "usf://acme-bank/ontology/fibo/2024-Q4",
  "classes_count": 8147,
  "shapes_count": 342
}
```

#### `usf:ConfidenceStatsFacet`
Attached to runs that include a confidence-scored extraction step.

```json
{
  "_producer": "https://github.com/MAKF-TECH/usf-platform",
  "_schemaURL": "https://usf.makf.tech/openlineage/facets/confidence-stats/v1",
  "total_extractions": 3421,
  "grounded": 3407,
  "ungrounded": 14,
  "mean_confidence": 0.963,
  "min_confidence": 0.41,
  "p50_confidence": 0.97,
  "p90_confidence": 0.99,
  "histogram": [
    {"bucket": "0.0-0.5", "count": 2},
    {"bucket": "0.5-0.7", "count": 12},
    {"bucket": "0.7-0.9", "count": 607},
    {"bucket": "0.9-1.0", "count": 2800}
  ]
}
```

#### `usf:SHACLValidationFacet`
Attached to runs that include pySHACL validation.

```json
{
  "_producer": "https://github.com/MAKF-TECH/usf-platform",
  "_schemaURL": "https://usf.makf.tech/openlineage/facets/shacl-validation/v1",
  "shapes_graph_uri": "usf://acme-bank/ontology/fibo/2024-Q4",
  "triples_validated": 3421,
  "violations": 14,
  "warnings": 3,
  "quarantine_graph_uri": "usf://acme-bank/quarantine/2026-03-27",
  "violation_summary": [
    {
      "shape": "fibo:BankIdentifierShape",
      "count": 8,
      "severity": "Violation"
    },
    {
      "shape": "fibo:TransactionAmountShape",
      "count": 6,
      "severity": "Violation"
    }
  ]
}
```

### Dataset Facets (Output)

#### `usf:NamedGraphFacet`
Attached to output datasets representing QLever named graphs.

```json
{
  "_producer": "https://github.com/MAKF-TECH/usf-platform",
  "_schemaURL": "https://usf.makf.tech/openlineage/facets/named-graph/v1",
  "named_graph_uri": "usf://acme-bank/instance/warehouse/batch-001",
  "graph_type": "instance",
  "tenant_slug": "acme-bank",
  "triples_inserted": 3407,
  "entity_types": [
    {"ontology_class": "fibo:CommercialBank", "count": 1204},
    {"ontology_class": "fibo:Account", "count": 892},
    {"ontology_class": "fibo:FinancialTransaction", "count": 661}
  ]
}
```

---

## Event Templates by Job Namespace

### `usf.ingest.structured` — Structured Ingestion (dlt)

**Job name pattern**: `{tenant_slug}.{source_name}.{batch_id}`

**START event**
```json
{
  "eventType": "START",
  "eventTime": "2026-03-27T10:00:00.000Z",
  "run": {
    "runId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "facets": {
      "usf:ontologyVersion": {
        "_producer": "https://github.com/MAKF-TECH/usf-platform",
        "_schemaURL": "https://usf.makf.tech/openlineage/facets/ontology-version/v1",
        "module": "fibo",
        "version": "2024-Q4",
        "named_graph_uri": "usf://acme-bank/ontology/fibo/2024-Q4"
      }
    }
  },
  "job": {
    "namespace": "usf.ingest.structured",
    "name": "acme-bank.warehouse.batch-a1b2c3d4",
    "facets": {
      "sourceCode": {
        "_producer": "https://github.com/MAKF-TECH/usf-platform",
        "_schemaURL": "https://openlineage.io/spec/facets/1-0-1/SourceCodeJobFacet.json",
        "language": "python",
        "sourceCode": "dlt.pipeline(source=sql_source(...))"
      }
    }
  },
  "inputs": [
    {
      "namespace": "postgres://db.acme.internal:5432/warehouse",
      "name": "public.transactions",
      "facets": {
        "schema": {
          "_producer": "https://github.com/MAKF-TECH/usf-platform",
          "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SchemaDatasetFacet.json",
          "fields": [
            {"name": "transaction_id", "type": "VARCHAR"},
            {"name": "account_from_id", "type": "VARCHAR"},
            {"name": "amount", "type": "NUMERIC"}
          ]
        }
      }
    }
  ],
  "outputs": [],
  "producer": "https://github.com/MAKF-TECH/usf-platform",
  "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json"
}
```

**COMPLETE event**
```json
{
  "eventType": "COMPLETE",
  "eventTime": "2026-03-27T10:05:33.000Z",
  "run": {
    "runId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "facets": {
      "usf:ontologyVersion": { "...": "..." },
      "usf:confidenceStats": {
        "total_extractions": 3421,
        "grounded": 3421,
        "ungrounded": 0,
        "mean_confidence": 1.0
      },
      "usf:shaclValidation": {
        "triples_validated": 3421,
        "violations": 14,
        "quarantine_graph_uri": "usf://acme-bank/quarantine/2026-03-27"
      }
    }
  },
  "job": {
    "namespace": "usf.ingest.structured",
    "name": "acme-bank.warehouse.batch-a1b2c3d4"
  },
  "inputs": [
    {
      "namespace": "postgres://db.acme.internal:5432/warehouse",
      "name": "public.transactions"
    }
  ],
  "outputs": [
    {
      "namespace": "usf://qlever",
      "name": "acme-bank/instance/warehouse/batch-a1b2c3d4",
      "facets": {
        "usf:namedGraph": {
          "named_graph_uri": "usf://acme-bank/instance/warehouse/batch-a1b2c3d4",
          "graph_type": "instance",
          "tenant_slug": "acme-bank",
          "triples_inserted": 3407,
          "entity_types": [
            {"ontology_class": "fibo:CommercialBank", "count": 1204}
          ]
        }
      }
    }
  ],
  "producer": "https://github.com/MAKF-TECH/usf-platform",
  "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json"
}
```

---

### `usf.ingest.unstructured` — Document Ingestion

**Job name pattern**: `{tenant_slug}.docs.{batch_id}`

**COMPLETE event (additional facets for unstructured)**
```json
{
  "eventType": "COMPLETE",
  "eventTime": "2026-03-27T11:30:00.000Z",
  "run": {
    "runId": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
    "facets": {
      "usf:extractionModel": {
        "model_name": "gemini-1.5-pro",
        "model_version": "1.5-001",
        "provider": "google",
        "temperature": 0.0,
        "prompt_template_version": "fibo-few-shot-v2"
      },
      "usf:ontologyVersion": {
        "module": "fibo",
        "version": "2024-Q4"
      },
      "usf:confidenceStats": {
        "total_extractions": 847,
        "grounded": 831,
        "ungrounded": 16,
        "mean_confidence": 0.91,
        "p50_confidence": 0.94,
        "histogram": [
          {"bucket": "0.0-0.5", "count": 4},
          {"bucket": "0.5-0.7", "count": 12},
          {"bucket": "0.7-0.9", "count": 180},
          {"bucket": "0.9-1.0", "count": 651}
        ]
      }
    }
  },
  "job": {
    "namespace": "usf.ingest.unstructured",
    "name": "acme-bank.docs.batch-b2c3d4e5"
  },
  "inputs": [
    {
      "namespace": "file://s3://acme-docs",
      "name": "basel-iii-annex-4.pdf",
      "facets": {
        "fileSize": {
          "_producer": "https://github.com/MAKF-TECH/usf-platform",
          "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/FileSizeDatasetFacet.json",
          "size": 2847392
        }
      }
    }
  ],
  "outputs": [
    {
      "namespace": "usf://qlever",
      "name": "acme-bank/instance/docs/batch-b2c3d4e5",
      "facets": {
        "usf:namedGraph": {
          "named_graph_uri": "usf://acme-bank/instance/docs/batch-b2c3d4e5",
          "graph_type": "instance",
          "triples_inserted": 831
        }
      }
    }
  ],
  "producer": "https://github.com/MAKF-TECH/usf-platform",
  "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json"
}
```

---

### `usf.sdl.publish` — SDL Version Publish

**Job name pattern**: `{tenant_slug}.sdl.{version}`

```json
{
  "eventType": "COMPLETE",
  "eventTime": "2026-03-27T12:00:00.000Z",
  "run": {
    "runId": "c3d4e5f6-a7b8-9012-cdef-345678901234"
  },
  "job": {
    "namespace": "usf.sdl.publish",
    "name": "acme-bank.sdl.v2"
  },
  "inputs": [
    {
      "namespace": "usf://sdl",
      "name": "acme-bank.sdl.v1",
      "facets": {}
    }
  ],
  "outputs": [
    {
      "namespace": "usf://qlever",
      "name": "acme-bank/schema/v2",
      "facets": {
        "usf:namedGraph": {
          "named_graph_uri": "usf://acme-bank/schema/v2",
          "graph_type": "schema"
        }
      }
    }
  ],
  "producer": "https://github.com/MAKF-TECH/usf-platform",
  "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json"
}
```

---

### `usf.query.execute` — Query Execution Audit

**Job name pattern**: `{tenant_slug}.query.{query_type}.{query_hash_prefix}`

Note: Query lineage events are written for audit purposes, not performance tracing.
Only `COMPLETE` and `FAIL` events are emitted (no `START` to avoid latency overhead).

```json
{
  "eventType": "COMPLETE",
  "eventTime": "2026-03-27T14:22:00.000Z",
  "run": {
    "runId": "d4e5f6a7-b8c9-0123-def0-456789012345",
    "facets": {
      "usf:ontologyVersion": {
        "module": "fibo",
        "version": "2024-Q4"
      }
    }
  },
  "job": {
    "namespace": "usf.query.execute",
    "name": "acme-bank.query.sql.abc12345",
    "facets": {
      "jobType": {
        "_producer": "https://github.com/MAKF-TECH/usf-platform",
        "_schemaURL": "https://openlineage.io/spec/facets/2-0-2/JobTypeJobFacet.json",
        "processingType": "BATCH",
        "integration": "USF",
        "jobType": "QUERY"
      }
    }
  },
  "inputs": [
    {
      "namespace": "usf://qlever",
      "name": "acme-bank/context/finance/v1"
    }
  ],
  "outputs": [
    {
      "namespace": "usf://qlever",
      "name": "acme-bank/provenance/2026-03-27"
    }
  ],
  "producer": "https://github.com/MAKF-TECH/usf-platform",
  "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json"
}
```

---

## Redpanda Topic Configuration

```
Topic: usf.lineage.events
Partitions: 12 (partitioned by tenant_slug hash)
Replication: 3
Retention: 7 years (604800000 ms → configure retention.ms = 220752000000)
Cleanup policy: delete (append-only)
Compression: lz4
```

**Producer config** (aiokafka):
```python
producer = AIOKafkaProducer(
    bootstrap_servers="redpanda:9092",
    key_serializer=lambda k: k.encode("utf-8"),  # key = tenant_slug
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    compression_type="lz4",
    acks="all",
    enable_idempotence=True,
)
```

**Consumer config** (usf-audit):
```python
consumer = AIOKafkaConsumer(
    "usf.lineage.events",
    bootstrap_servers="redpanda:9092",
    group_id="usf-audit-lineage-consumer",
    auto_offset_reset="earliest",
    enable_auto_commit=False,  # manual commit after DB write
)
```

---

*End of OpenLineage Events Specification v1.0.0*
