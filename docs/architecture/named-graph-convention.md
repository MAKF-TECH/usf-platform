# USF Named Graph URI Convention

**Version**: 1.0.0  
**Status**: FROZEN  
**Date**: 2026-03-27  
**Author**: usf-architect

> Named graph URIs are the primary isolation mechanism in USF.
> Every triple in the KG belongs to exactly one named graph.
> No query can span named graphs belonging to different tenants.

---

## URI Pattern

```
usf://{tenant_slug}/{graph_type}/{name}/{version}
```

| Segment | Rules | Examples |
|---------|-------|---------|
| `tenant_slug` | lowercase alphanumeric + hyphens, 3–63 chars | `acme-bank`, `healthco`, `energy-grid-plc` |
| `graph_type` | one of the defined types below | `ontology`, `context`, `instance` |
| `name` | lowercase alphanumeric + hyphens + slashes for sub-paths | `fibo`, `finance`, `warehouse/batch-001` |
| `version` | ISO date (`YYYY-MM-DD`) OR semver (`vN`) | `2024-Q4`, `v1`, `v2`, `2026-03-27` |

### Pattern Regex

```
^usf://[a-z][a-z0-9-]{2,62}/(?:ontology|context|instance|provenance|access|schema|quarantine)/[a-z0-9][a-z0-9/_-]{0,127}/(?:v\d+|\d{4}-\d{2}-\d{2}|\d{4}-Q[1-4])$
```

---

## Graph Types

### `ontology`
Holds OWL axioms for an industry module or derived ontology.
**Immutable after publish.** New version = new graph.

```
usf://{tenant}/ontology/{module}/{version}

Examples:
  usf://acme-bank/ontology/fibo/2024-Q4
  usf://acme-bank/ontology/fibo/2025-Q1
  usf://acme-bank/ontology/derived/v1
  usf://healthco/ontology/fhir/r4
```

Rules:
- One per tenant per module version
- Read-only for all application users; write only via `usf-kg /ontology/load`
- SDL compiler reads this graph for OWL class resolution
- pySHACL reads SHACL shapes from this graph

---

### `context`
Holds the SDL-compiled view of the tenant's business context. Contains the class hierarchy,
property definitions, and SKOS alignment triples for a specific named context.

```
usf://{tenant}/context/{context_name}/{version}

Examples:
  usf://acme-bank/context/finance/v1
  usf://acme-bank/context/risk/v1
  usf://acme-bank/context/risk/v2
  usf://acme-bank/context/ops/v1
```

Rules:
- New SDL publish = new version = new context graph
- The active context is the highest version number
- Old versions are retained for audit (never deleted, only superseded)
- Query routing always uses the active version unless `X-USF-Context-Version` is set

---

### `instance`
Holds the actual instance triples (the data). Partitioned by source batch.

```
usf://{tenant}/instance/{source_slug}/{batch_id}

Examples:
  usf://acme-bank/instance/warehouse/batch-001
  usf://acme-bank/instance/warehouse/batch-002
  usf://acme-bank/instance/docs/kyc-batch-2026-03-27
  usf://acme-bank/instance/api/bloomberg/2026-03-27
```

Rules:
- One graph per ingestion batch (never merge batches into the same graph)
- `batch_id` is the ingestion job UUID or a semantic identifier
- Instance graphs are mutable during an active job; immutable once job completes
- For structured data: corresponds to one dlt load ID
- For unstructured: corresponds to one Docling/LangExtract extraction run
- Deletion policy: instance graphs are retained for 7 years (BCBS 239) unless tenant explicitly purges

---

### `provenance`
Holds PROV-O triples. Partitioned by date (one graph per day).

```
usf://{tenant}/provenance/{date}

Examples:
  usf://acme-bank/provenance/2026-03-27
  usf://acme-bank/provenance/2026-03-28
```

Rules:
- One graph per calendar day (UTC)
- All PROV-O triples for all activities on that date go here
- Append-only (no deletions or updates)
- Queried by `usf-audit` for lineage chains and regulatory export
- Retention: 7 years minimum

---

### `access`
Holds OPA-aligned access control triples. Maps roles to contexts to permissions.

```
usf://{tenant}/access/{policy_version}

Examples:
  usf://acme-bank/access/v1
  usf://acme-bank/access/v2
```

Rules:
- One per tenant per policy version
- Written by `usf-api` when SDL access policies are published
- Read by OPA sidecar for ABAC decisions (OPA may cache this)
- Tenant isolation is absolute: OPA policy enforces that queries can only reference graphs matching the requesting tenant's slug

---

### `schema`
Holds SDL metadata and compiled OWL axioms for the tenant's own entity/metric definitions.
(Distinct from `ontology` which holds the industry-standard OWL.)

```
usf://{tenant}/schema/{version}

Examples:
  usf://acme-bank/schema/v1
  usf://acme-bank/schema/v2
```

Rules:
- One per SDL published version
- Written by `usf-sdl /publish`
- Read by SDL compiler and query router to resolve entity-to-table mappings
- Immutable after publish

---

### `quarantine`
Holds triples that failed pySHACL validation during ingestion.
These triples exist in the KG but are excluded from all non-admin queries.

```
usf://{tenant}/quarantine/{date}

Examples:
  usf://acme-bank/quarantine/2026-03-27
```

Rules:
- One graph per calendar day
- Populated by `usf-kg /triples` when `validate=true` and a triple fails SHACL
- Excluded from all named graph resolution by the context router (unless role=admin)
- UI Quarantine Review tab allows analysts to: fix → re-insert, or discard → delete
- After fix/discard, triples are moved or removed and the quarantine graph is updated
- Retention: same as instance graphs (7 years)

---

## Tenant Isolation Rules

### Rule 1: No Cross-Tenant Graph Access
The OPA policy enforces that every graph URI accessed in a SPARQL query or triple insert
MUST match the prefix `usf://{requesting_tenant_slug}/`.
Any query attempting to reference a different tenant's graph returns HTTP 403.

```rego
# opa/policies/usf/authz.rego
deny[msg] {
    graph_uri := input.named_graphs[_]
    not startswith(graph_uri, concat("", ["usf://", input.tenant_slug, "/"]))
    msg := sprintf("Cross-tenant graph access denied: %v", [graph_uri])
}
```

### Rule 2: Tenant Slug Uniqueness
Tenant slugs are globally unique in the USF platform (enforced at tenant creation).
No two tenants may share a slug. Slug changes are not permitted after creation.

### Rule 3: Graph URI in JWT Claims
The JWT issued by `usf-api /auth/login` contains:
```json
{
  "sub": "user@acme-bank.com",
  "tenant_id": "uuid",
  "tenant_slug": "acme-bank",
  "roles": ["risk_analyst"],
  "exp": 1234567890
}
```
The `tenant_slug` claim is extracted and used to construct the OPA input for every request.

### Rule 4: QLever Named Graph Partitioning
QLever stores all tenant data in a single RDF dataset. Tenant isolation is enforced
**at query time** by the USF context router (not at QLever level). The context router
wraps every SPARQL query with a `FROM NAMED` clause restricted to the tenant's graphs.

For production multi-tenant deployments, consider separate QLever instances per tenant
(stronger isolation, higher operational cost). The current design uses query-time isolation.

---

## Version Format Reference

| Format | Pattern | When to Use |
|--------|---------|------------|
| Semver `vN` | `v1`, `v2`, `v3` | SDL versions, context versions, schema versions |
| ISO date | `YYYY-MM-DD` | Daily partitioned graphs: provenance, quarantine |
| Quarter | `YYYY-QN` | Ontology module releases (e.g., FIBO quarterly releases) |
| FHIR version | `r4`, `r5` | FHIR ontology graphs |
| Batch ID | `batch-{uuid-short}` | Instance batch graphs |

---

## Full URI Examples

```
# Industry ontology (FIBO Q4 2024 release)
usf://acme-bank/ontology/fibo/2024-Q4

# Active business context for the Finance department
usf://acme-bank/context/finance/v1

# Instance triples from warehouse ingestion batch
usf://acme-bank/instance/warehouse/batch-4a3f2b1c

# Provenance for today's activities
usf://acme-bank/provenance/2026-03-27

# ABAC policy v1
usf://acme-bank/access/v1

# SDL schema v2 (compiled OWL from SDL YAML)
usf://acme-bank/schema/v2

# Quarantine for today's violations
usf://acme-bank/quarantine/2026-03-27

# Healthcare tenant, FHIR ontology
usf://healthco/ontology/fhir/r4

# Healthcare tenant, clinical context
usf://healthco/context/clinical/v1
```

---

*End of Named Graph Convention v1.0.0*
