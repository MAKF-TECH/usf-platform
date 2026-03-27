# USF OpenLineage Event Specification

**Version**: 1.0.0 | **Status**: FROZEN | **Date**: 2026-03-27

## Job Namespaces

| Namespace | Service | When Emitted |
|-----------|---------|-------------|
| usf.ingest.structured | usf-ingest | dlt structured ingestion |
| usf.ingest.unstructured | usf-ingest | Docling + LangExtract pipeline |
| usf.ingest.semi | usf-ingest | FHIR/CIM/JSON-LD ingestion |
| usf.sdl.compile | usf-sdl | SDL YAML compilation |
| usf.sdl.publish | usf-sdl | SDL version publish |
| usf.query.execute | usf-query | Query execution (audit) |
| usf.kg.validate | usf-kg | pySHACL validation batch |
| usf.kg.ontology_load | usf-kg | Ontology module load |

## Dataset Naming Convention

**Input datasets (sources)**:
- PostgreSQL: `postgres://{host}:{port}/{db}` + name `{schema}.{table}`
- CSV/PDF files: `file://{path_or_bucket}` + name `{filename}`
- FHIR: `fhir://{server_url}` + name `Bundle/{id}`

**Output datasets (KG named graphs)**:
- QLever graph: namespace `usf://qlever`, name `{tenant}/{graph_type}/...`

## Custom Facets

### usf:ExtractionModelFacet (run facet)
```json
{
  "_schemaURL": "https://usf.makf.tech/openlineage/facets/extraction-model/v1",
  "model_name": "gemini-1.5-pro",
  "prompt_template_version": "fibo-few-shot-v2"
}
```

### usf:OntologyVersionFacet (run facet)
```json
{
  "_schemaURL": "https://usf.makf.tech/openlineage/facets/ontology-version/v1",
  "module": "fibo",
  "version": "2024-Q4",
  "named_graph_uri": "usf://acme-bank/ontology/fibo/2024-Q4"
}
```

### usf:ConfidenceStatsFacet (run facet)
```json
{
  "_schemaURL": "https://usf.makf.tech/openlineage/facets/confidence-stats/v1",
  "total_extractions": 3421,
  "grounded": 3407,
  "ungrounded": 14,
  "mean_confidence": 0.963,
  "histogram": [{"bucket": "0.9-1.0", "count": 2800}]
}
```

### usf:NamedGraphFacet (dataset facet)
```json
{
  "_schemaURL": "https://usf.makf.tech/openlineage/facets/named-graph/v1",
  "named_graph_uri": "usf://acme-bank/instance/warehouse/batch-001",
  "graph_type": "instance",
  "triples_inserted": 3407
}
```

## Redpanda Topic Config
```
Topic: usf.lineage.events
Partitions: 12 (key = tenant_slug)
Retention: 7 years (BCBS 239)
Compression: lz4
```

*End of OpenLineage Events v1.0.0*
