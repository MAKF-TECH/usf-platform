import { Injectable, signal } from '@angular/core';
import {
  KgNode, KgEdge, IngestionJob, AuditEntry, TenantMetrics, QueryResult, LayerTrace
} from '../models';

@Injectable({ providedIn: 'root' })
export class MockService {
  // FIBO Banking KG — 50 nodes
  readonly kgNodes: KgNode[] = [
    // Legal Entities
    { iri: 'fibo:acme-bank', label: 'Acme Bank', ontologyClass: 'Entity', degree: 12, properties: { type: 'fibo:CommercialBank', country: 'US' } },
    { iri: 'fibo:deutsche-bank', label: 'Deutsche Bank AG', ontologyClass: 'Entity', degree: 9, properties: { type: 'fibo:Bank', country: 'DE' } },
    { iri: 'fibo:bnp-paribas', label: 'BNP Paribas SA', ontologyClass: 'Entity', degree: 7, properties: { type: 'fibo:Bank', country: 'FR' } },
    { iri: 'fibo:hsbc', label: 'HSBC Holdings plc', ontologyClass: 'Entity', degree: 8, properties: { type: 'fibo:Bank', country: 'GB' } },
    { iri: 'fibo:jpmorgan', label: 'JPMorgan Chase & Co', ontologyClass: 'Entity', degree: 10, properties: { type: 'fibo:Bank', country: 'US' } },
    { iri: 'fibo:ing', label: 'ING Group NV', ontologyClass: 'Entity', degree: 5, properties: { type: 'fibo:Bank', country: 'NL' } },
    { iri: 'fibo:unicredit', label: 'UniCredit SpA', ontologyClass: 'Entity', degree: 6, properties: { type: 'fibo:Bank', country: 'IT' } },
    { iri: 'fibo:santander', label: 'Banco Santander SA', ontologyClass: 'Entity', degree: 7, properties: { type: 'fibo:Bank', country: 'ES' } },
    { iri: 'fibo:barclays', label: 'Barclays PLC', ontologyClass: 'Entity', degree: 6, properties: { type: 'fibo:Bank', country: 'GB' } },
    { iri: 'fibo:societe', label: 'Société Générale SA', ontologyClass: 'Entity', degree: 5, properties: { type: 'fibo:Bank', country: 'FR' } },
    // Accounts
    { iri: 'fibo:acct-001', label: 'Acct #001-DE-EUR', ontologyClass: 'Entity', degree: 3, properties: { type: 'fibo:BankAccount', currency: 'EUR' } },
    { iri: 'fibo:acct-002', label: 'Acct #002-FR-EUR', ontologyClass: 'Entity', degree: 2, properties: { type: 'fibo:BankAccount', currency: 'EUR' } },
    { iri: 'fibo:acct-003', label: 'Acct #003-US-USD', ontologyClass: 'Entity', degree: 4, properties: { type: 'fibo:BankAccount', currency: 'USD' } },
    { iri: 'fibo:acct-004', label: 'Acct #004-GB-GBP', ontologyClass: 'Entity', degree: 3, properties: { type: 'fibo:BankAccount', currency: 'GBP' } },
    { iri: 'fibo:acct-005', label: 'Acct #005-NL-EUR', ontologyClass: 'Entity', degree: 2, properties: { type: 'fibo:BankAccount', currency: 'EUR' } },
    // Transactions
    { iri: 'fibo:tx-001', label: 'TX-2024-0001 EUR 1.2M', ontologyClass: 'Event', degree: 2, properties: { amount: '1200000', currency: 'EUR', date: '2024-01-15' } },
    { iri: 'fibo:tx-002', label: 'TX-2024-0002 USD 850K', ontologyClass: 'Event', degree: 2, properties: { amount: '850000', currency: 'USD', date: '2024-01-16' } },
    { iri: 'fibo:tx-003', label: 'TX-2024-0003 EUR 3.5M', ontologyClass: 'Event', degree: 2, properties: { amount: '3500000', currency: 'EUR', date: '2024-01-17' } },
    { iri: 'fibo:tx-004', label: 'TX-2024-AML-FLAG', ontologyClass: 'Event', degree: 3, properties: { amount: '99900', currency: 'EUR', date: '2024-01-18', flag: 'AML_SUSPICIOUS' } },
    { iri: 'fibo:tx-005', label: 'TX-2024-0005 GBP 220K', ontologyClass: 'Event', degree: 2, properties: { amount: '220000', currency: 'GBP', date: '2024-01-19' } },
    // Metrics
    { iri: 'usf:metric-exposure', label: 'Total Exposure by Counterparty', ontologyClass: 'Metric', degree: 5, properties: { sql: 'SUM(exposure_amount) GROUP BY counterparty', context: 'risk' } },
    { iri: 'usf:metric-active-accounts', label: 'Active Accounts', ontologyClass: 'Metric', degree: 3, properties: { sql: 'COUNT(*) WHERE status=active', context: 'finance' } },
    { iri: 'usf:metric-tx-volume', label: 'Transaction Volume', ontologyClass: 'Metric', degree: 4, properties: { sql: 'SUM(amount) GROUP BY date', context: 'ops' } },
    { iri: 'usf:metric-aml-ratio', label: 'AML Flagged Ratio', ontologyClass: 'Metric', degree: 3, properties: { sql: 'COUNT(flag=AML) / COUNT(*)', context: 'risk' } },
    // Contexts
    { iri: 'usf:ctx-finance', label: 'Finance Context', ontologyClass: 'Context', degree: 8, properties: { owner: 'CFO Team' } },
    { iri: 'usf:ctx-risk', label: 'Risk Context', ontologyClass: 'Context', degree: 7, properties: { owner: 'Risk Team' } },
    { iri: 'usf:ctx-ops', label: 'Ops Context', ontologyClass: 'Context', degree: 5, properties: { owner: 'Operations' } },
    // Documents
    { iri: 'doc:annual-report-2023', label: 'Annual Report 2023', ontologyClass: 'Document', degree: 4, properties: { type: 'PDF', pages: '142' } },
    { iri: 'doc:risk-policy-v2', label: 'Risk Policy v2.1', ontologyClass: 'Document', degree: 3, properties: { type: 'PDF', pages: '38' } },
    { iri: 'doc:fibo-mapping', label: 'FIBO Mapping Sheet', ontologyClass: 'Document', degree: 5, properties: { type: 'XLSX', rows: '2847' } },
    // Provenance
    { iri: 'prov:ingest-run-001', label: 'Ingest Run 001', ontologyClass: 'Provenance', degree: 2, properties: { startedAt: '2024-01-15T10:00:00Z', endedAt: '2024-01-15T10:23:14Z' } },
    { iri: 'prov:ingest-run-002', label: 'Ingest Run 002', ontologyClass: 'Provenance', degree: 2, properties: { startedAt: '2024-01-16T14:00:00Z', endedAt: '2024-01-16T14:15:33Z' } },
    // Additional entities to reach 50
    { iri: 'fibo:subsidiary-de-01', label: 'DB Securities Ltd', ontologyClass: 'Entity', degree: 3, properties: { type: 'fibo:FinancialInstitution', country: 'GB' } },
    { iri: 'fibo:subsidiary-fr-01', label: 'BNP Securities Inc', ontologyClass: 'Entity', degree: 2 },
    { iri: 'fibo:exposure-sector-eu', label: 'EU Financial Sector Exposure', ontologyClass: 'Metric', degree: 4 },
    { iri: 'fibo:counterparty-001', label: 'Counterparty Alpha LLC', ontologyClass: 'Entity', degree: 3 },
    { iri: 'fibo:counterparty-002', label: 'Counterparty Beta GmbH', ontologyClass: 'Entity', degree: 3 },
    { iri: 'fibo:counterparty-003', label: 'Counterparty Gamma SA', ontologyClass: 'Entity', degree: 2 },
    { iri: 'fibo:fx-eur-usd', label: 'EUR/USD FX Rate', ontologyClass: 'Metric', degree: 2 },
    { iri: 'fibo:fx-eur-gbp', label: 'EUR/GBP FX Rate', ontologyClass: 'Metric', degree: 2 },
    { iri: 'fibo:credit-rating-acme', label: 'Acme Bank Credit Rating', ontologyClass: 'Metric', degree: 2 },
    { iri: 'fibo:acct-006', label: 'Acct #006-IT-EUR', ontologyClass: 'Entity', degree: 2 },
    { iri: 'fibo:acct-007', label: 'Acct #007-ES-EUR', ontologyClass: 'Entity', degree: 2 },
    { iri: 'fibo:tx-006', label: 'TX-2024-0006 EUR 500K', ontologyClass: 'Event', degree: 2 },
    { iri: 'fibo:tx-007', label: 'TX-2024-0007 EUR 2.1M', ontologyClass: 'Event', degree: 2 },
    { iri: 'doc:trade-confirmations', label: 'Trade Confirmations Q1', ontologyClass: 'Document', degree: 3 },
    { iri: 'doc:aml-report-q1', label: 'AML Report Q1 2024', ontologyClass: 'Document', degree: 2 },
    { iri: 'prov:query-run-001', label: 'Query Execution 001', ontologyClass: 'Provenance', degree: 2 },
    { iri: 'usf:sdl-finance-v1', label: 'SDL Finance v1.0', ontologyClass: 'Document', degree: 4 },
  ];

  readonly kgEdges: KgEdge[] = [
    { subject: 'fibo:acme-bank', predicate: 'fibo:hasCounterparty', predicateLabel: 'hasCounterparty', object: 'fibo:deutsche-bank' },
    { subject: 'fibo:acme-bank', predicate: 'fibo:hasCounterparty', predicateLabel: 'hasCounterparty', object: 'fibo:bnp-paribas' },
    { subject: 'fibo:acme-bank', predicate: 'fibo:hasCounterparty', predicateLabel: 'hasCounterparty', object: 'fibo:jpmorgan' },
    { subject: 'fibo:acme-bank', predicate: 'fibo:holdsAccount', predicateLabel: 'holdsAccount', object: 'fibo:acct-003' },
    { subject: 'fibo:deutsche-bank', predicate: 'fibo:holdsAccount', predicateLabel: 'holdsAccount', object: 'fibo:acct-001' },
    { subject: 'fibo:bnp-paribas', predicate: 'fibo:holdsAccount', predicateLabel: 'holdsAccount', object: 'fibo:acct-002' },
    { subject: 'fibo:hsbc', predicate: 'fibo:holdsAccount', predicateLabel: 'holdsAccount', object: 'fibo:acct-004' },
    { subject: 'fibo:ing', predicate: 'fibo:holdsAccount', predicateLabel: 'holdsAccount', object: 'fibo:acct-005' },
    { subject: 'fibo:acct-001', predicate: 'fibo:participatesIn', predicateLabel: 'participatesIn', object: 'fibo:tx-001' },
    { subject: 'fibo:acct-003', predicate: 'fibo:participatesIn', predicateLabel: 'participatesIn', object: 'fibo:tx-002' },
    { subject: 'fibo:acct-001', predicate: 'fibo:participatesIn', predicateLabel: 'participatesIn', object: 'fibo:tx-003' },
    { subject: 'fibo:acct-002', predicate: 'fibo:participatesIn', predicateLabel: 'participatesIn', object: 'fibo:tx-004' },
    { subject: 'fibo:deutsche-bank', predicate: 'fibo:hasSubsidiary', predicateLabel: 'hasSubsidiary', object: 'fibo:subsidiary-de-01' },
    { subject: 'fibo:bnp-paribas', predicate: 'fibo:hasSubsidiary', predicateLabel: 'hasSubsidiary', object: 'fibo:subsidiary-fr-01' },
    { subject: 'usf:ctx-finance', predicate: 'usf:defines', predicateLabel: 'defines', object: 'usf:metric-active-accounts' },
    { subject: 'usf:ctx-risk', predicate: 'usf:defines', predicateLabel: 'defines', object: 'usf:metric-exposure' },
    { subject: 'usf:ctx-risk', predicate: 'usf:defines', predicateLabel: 'defines', object: 'usf:metric-aml-ratio' },
    { subject: 'usf:ctx-ops', predicate: 'usf:defines', predicateLabel: 'defines', object: 'usf:metric-tx-volume' },
    { subject: 'doc:annual-report-2023', predicate: 'prov:wasGeneratedBy', predicateLabel: 'wasGeneratedBy', object: 'prov:ingest-run-001' },
    { subject: 'fibo:acme-bank', predicate: 'fibo:hasCounterparty', predicateLabel: 'hasCounterparty', object: 'fibo:counterparty-001' },
    { subject: 'fibo:acme-bank', predicate: 'fibo:hasCounterparty', predicateLabel: 'hasCounterparty', object: 'fibo:counterparty-002' },
    { subject: 'fibo:acme-bank', predicate: 'fibo:hasCounterparty', predicateLabel: 'hasCounterparty', object: 'fibo:counterparty-003' },
  ];

  readonly ingestionJobs: IngestionJob[] = [
    {
      id: 'job-001',
      source: 'Kaggle AML Dataset',
      type: 'csv',
      started: new Date(Date.now() - 3 * 60000),
      triplesAdded: 0,
      confidence: 0,
      status: 'running',
      progress: 67,
      l1Trace: { parser: 'dlt/csv', chunks: 847, extractions: 2284, grounded: 2271, confidence_mean: 0.94 },
    },
    {
      id: 'job-002',
      source: 'Annual Report 2023 PDF',
      type: 'pdf',
      started: new Date(Date.now() - 2 * 3600000),
      duration: 1394,
      triplesAdded: 3421,
      confidence: 0.962,
      status: 'completed',
      l1Trace: { parser: 'Docling v2.1', chunks: 847, extractions: 3421, grounded: 3407, confidence_mean: 0.962 },
      openLineageFacets: {
        model: 'neo4j-graphrag-python/SimpleKGPipeline',
        ontologyVersion: 'FIBO-v3.2.1',
        charInterval: '0-142847',
      },
    },
    {
      id: 'job-003',
      source: 'Postgres DWH (transactions)',
      type: 'api',
      started: new Date(Date.now() - 24 * 3600000),
      duration: 422,
      triplesAdded: 12847,
      confidence: 0.998,
      status: 'completed',
      l1Trace: { parser: 'dlt/postgres', chunks: 12847, extractions: 12847, grounded: 12847, confidence_mean: 0.998 },
    },
    {
      id: 'job-004',
      source: 'SWIFT Messages Stream',
      type: 'stream',
      started: new Date(Date.now() - 6 * 3600000),
      duration: 180,
      triplesAdded: 0,
      confidence: 0.71,
      status: 'failed',
      l1Trace: { parser: 'aiokafka/swift', chunks: 1422, extractions: 0, grounded: 0, confidence_mean: 0 },
    },
  ];

  readonly auditEntries: AuditEntry[] = Array.from({ length: 20 }, (_, i) => ({
    id: `audit-${String(i + 1).padStart(3, '0')}`,
    timestamp: new Date(Date.now() - i * 20 * 60000),
    action: ['query', 'query', 'ingest', 'schema_change', 'query', 'export', 'query'][i % 7],
    user: ['alice@acme-bank.com', 'bob@acme-bank.com', 'system', 'carol@acme-bank.com'][i % 4],
    context: ['finance', 'risk', 'ops'][i % 3],
    resource: ['metric:total_exposure', 'metric:active_accounts', 'kg:ingest', 'sdl:version', 'metric:aml_ratio'][i % 5],
    decision: i % 7 === 4 ? 'deny' : 'allow',
    provenance: {
      '@type': 'prov:Activity',
      'prov:startedAtTime': new Date(Date.now() - i * 20 * 60000).toISOString(),
      'prov:wasAssociatedWith': `user:${['alice', 'bob', 'system', 'carol'][i % 4]}`,
      'prov:used': `resource:${['exposure_table', 'accounts_view', 'kg_store', 'sdl_schema', 'aml_model'][i % 5]}`,
    },
  }));

  readonly tenantMetrics: TenantMetrics = {
    totalTriples: 128_473,
    activeContexts: 3,
    dataSources: 4,
    queriesToday: 247,
  };

  getMockQueryResult(query: string, type: 'sql' | 'sparql' | 'nl' | 'mcp'): QueryResult {
    const trace: LayerTrace = {
      layer1: { parser: 'dlt/postgres', chunks: 12847, extractions: 3421, grounded: 3407, confidence_mean: 0.96 },
      layer2: { named_graph: 'usf://tenant/acme-bank/context/risk', ontology_version: 'FIBO-v3.2.1', triples_in_scope: 48291 },
      layer3: {
        context: 'risk',
        abac_decision: 'allow',
        backend: type === 'sparql' ? 'QLever' : 'Wren+PostgreSQL',
        sql_generated: type !== 'sparql' ? 'SELECT counterparty_name, SUM(exposure_amount) as total_exposure FROM exposures WHERE sector = \'EU_FINANCIAL\' GROUP BY counterparty_name ORDER BY total_exposure DESC' : undefined,
        cache_hit: false,
        query_time_ms: 142,
        provenance: {
          '@type': 'prov:Activity',
          'prov:startedAtTime': new Date().toISOString(),
          'prov:wasAssociatedWith': 'user:alice',
        },
      },
      layer4: { format: 'application/json', response_size_bytes: 4821 },
    };

    return {
      columns: ['counterparty', 'sector', 'total_exposure_eur', 'currency'],
      rows: [
        { counterparty: 'Deutsche Bank AG', sector: 'EU Financial', total_exposure_eur: 4_200_000, currency: 'EUR' },
        { counterparty: 'BNP Paribas SA', sector: 'EU Financial', total_exposure_eur: 3_100_000, currency: 'EUR' },
        { counterparty: 'ING Group NV', sector: 'EU Financial', total_exposure_eur: 2_800_000, currency: 'EUR' },
        { counterparty: 'UniCredit SpA', sector: 'EU Financial', total_exposure_eur: 1_950_000, currency: 'EUR' },
        { counterparty: 'Société Générale SA', sector: 'EU Financial', total_exposure_eur: 1_200_000, currency: 'EUR' },
      ],
      layerTrace: trace,
      executionTimeMs: 142,
    };
  }
}
