/** TypeScript interfaces for USF API responses. */

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
}

// ── Metrics ───────────────────────────────────────────────────────────────────

export interface MetricSummary {
  name: string;
  description: string;
  ontology_class: string;
  type: string;
  contexts: string[];
  dimensions: string[];
  time_grains: string[];
}

export interface MetricExplanation {
  name: string;
  description: string;
  ontology_class: string;
  type: string;
  compiled_sql?: string;
  compiled_sparql?: string;
  source_tables: string[];
  sdl_version?: string;
  lineage: Record<string, unknown>;
}

// ── Query ─────────────────────────────────────────────────────────────────────

export interface QueryOptions {
  dimensions?: string[];
  filters?: Record<string, unknown>;
  timeRange?: { start: string; end: string; grain?: string };
  context?: string;
}

export interface QueryMeta {
  request_id?: string;
  tenant_id?: string;
  context?: string;
  named_graph?: string;
  query_hash?: string;
  prov_o_uri?: string;
  cached: boolean;
  execution_ms?: number;
}

export interface QueryResult {
  columns: string[];
  data: Record<string, unknown>[];
  row_count: number;
  meta: QueryMeta;
  /** Convenience PROV-O provenance block. */
  provenance: {
    "prov:wasGeneratedBy": {
      "usf:contextApplied"?: string;
      "usf:namedGraph"?: string;
      "usf:queryHash"?: string;
      "usf:provOUri"?: string;
    };
  };
}

// ── Knowledge Graph ───────────────────────────────────────────────────────────

export interface EntityResult {
  iri: string;
  label: string;
  ontology_class?: string;
  score?: number;
}

export interface EntityDetail {
  iri: string;
  label: string;
  ontology_class?: string;
  properties: Record<string, unknown>;
  neighbors: Record<string, unknown>[];
  prov_o: Record<string, unknown>;
}

export interface SearchOptions {
  entityType?: string;
  context?: string;
  limit?: number;
}

// ── Context ───────────────────────────────────────────────────────────────────

export interface ContextInfo {
  name: string;
  description?: string;
  named_graph_uri?: string;
  metric_count: number;
}
