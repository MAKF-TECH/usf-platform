# USF Named Graph URI Convention

**Version**: 1.0.0 | **Status**: FROZEN | **Date**: 2026-03-27

## URI Pattern

```
usf://{tenant_slug}/{graph_type}/{name}/{version}
```

| Segment | Rules | Example |
|---------|-------|---------|
| tenant_slug | lowercase alphanumeric + hyphens, 3-63 chars | acme-bank |
| graph_type | one of 7 defined types | ontology, context, instance |
| name | lowercase alphanumeric + hyphens + slashes | fibo, finance, warehouse/batch-001 |
| version | ISO date or semver | 2024-Q4, v1, 2026-03-27 |

## Graph Types

| Type | Purpose | Example |
|------|---------|---------|
| `ontology` | OWL axioms for industry module. Immutable. | `usf://acme-bank/ontology/fibo/2024-Q4` |
| `context` | SDL-compiled context view. Versioned. | `usf://acme-bank/context/finance/v1` |
| `instance` | Actual RDF instance triples. Per-batch. | `usf://acme-bank/instance/warehouse/batch-001` |
| `provenance` | PROV-O triples. Append-only, daily. | `usf://acme-bank/provenance/2026-03-27` |
| `access` | OPA-aligned ABAC policy triples. | `usf://acme-bank/access/v1` |
| `schema` | SDL-compiled OWL for tenant entities/metrics. | `usf://acme-bank/schema/v2` |
| `quarantine` | SHACL-failed triples. Daily, admin-only. | `usf://acme-bank/quarantine/2026-03-27` |

## Tenant Isolation

**Rule 1**: OPA policy enforces that every graph URI accessed MUST start with `usf://{requesting_tenant_slug}/`. Cross-tenant access returns HTTP 403.

**Rule 2**: Tenant slugs are globally unique and immutable after creation.

**Rule 3**: JWT claims include `tenant_slug` used to construct OPA input for every request.

**Rule 4**: QLever stores all tenant data in one dataset; isolation enforced at query time via `FROM NAMED` wrapping.

## Version Format

| Format | When to Use |
|--------|------------|
| `vN` (v1, v2) | SDL, context, schema, access versions |
| `YYYY-MM-DD` | Daily provenance and quarantine graphs |
| `YYYY-QN` | Ontology module quarterly releases |
| `rN` | FHIR ontology versions (r4, r5) |

*End of Named Graph Convention v1.0.0*
