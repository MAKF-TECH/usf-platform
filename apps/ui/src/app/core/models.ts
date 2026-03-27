// Core types shared across the app

export interface KgNode {
  iri: string;
  label: string;
  ontologyClass: 'Entity' | 'Metric' | 'Event' | 'Document' | 'Context' | 'Provenance';
  properties?: Record<string, string>;
  degree?: number;
}

export interface KgEdge {
  subject: string;
  predicate: string;
  predicateLabel: string;
  object: string;
}

export interface LayerTrace {
  layer1?: {
    parser: string;
    chunks: number;
    extractions: number;
    grounded: number;
    confidence_mean: number;
  };
  layer2?: {
    named_graph: string;
    ontology_version: string;
    triples_in_scope: number;
  };
  layer3?: {
    context: string;
    abac_decision: string;
    backend: string;
    sql_generated?: string;
    cache_hit: boolean;
    query_time_ms: number;
    provenance?: object;
  };
  layer4?: {
    format: string;
    response_size_bytes: number;
  };
}

export interface IngestionJob {
  id: string;
  source: string;
  type: 'csv' | 'pdf' | 'api' | 'stream';
  started: Date;
  duration?: number;
  triplesAdded: number;
  confidence: number;
  status: 'running' | 'completed' | 'failed' | 'pending';
  progress?: number;
  l1Trace?: LayerTrace['layer1'];
  openLineageFacets?: Record<string, unknown>;
}

export interface AuditEntry {
  id: string;
  timestamp: Date;
  action: string;
  user: string;
  context: string;
  resource: string;
  decision: 'allow' | 'deny';
  provenance?: object;
}

export interface TenantMetrics {
  totalTriples: number;
  activeContexts: number;
  dataSources: number;
  queriesToday: number;
}

export interface QueryResult {
  columns: string[];
  rows: Record<string, unknown>[];
  layerTrace: LayerTrace;
  executionTimeMs: number;
}
