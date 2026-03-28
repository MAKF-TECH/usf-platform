/**
 * USF TypeScript SDK — main client.
 * Uses native fetch (Node ≥18, browser). Zero production dependencies.
 */
import {
  USFSDKError,
  AuthError,
  ContextAmbiguousError,
  NotFoundError,
  AccessDeniedError,
  ValidationError,
} from "./errors.js";
import type {
  TokenResponse,
  MetricSummary,
  MetricExplanation,
  QueryOptions,
  QueryResult,
  EntityResult,
  EntityDetail,
  SearchOptions,
  ContextInfo,
} from "./models.js";

interface TokenStore {
  accessToken: string;
  refreshToken: string;
  expiresAt: number; // epoch ms
}

async function parseErrorBody(
  res: Response,
): Promise<{ message: string; detail: Record<string, unknown> }> {
  try {
    const body = (await res.json()) as {
      error?: { message?: string; detail?: Record<string, unknown> };
    };
    return {
      message: body.error?.message ?? `HTTP ${res.status}`,
      detail: body.error?.detail ?? {},
    };
  } catch {
    return { message: `HTTP ${res.status}`, detail: {} };
  }
}

async function throwForStatus(res: Response): Promise<void> {
  if (res.ok) return;

  const { message, detail } = await parseErrorBody(res);

  if (res.status === 409) {
    const metric = (detail["metric"] as string | undefined) ?? "unknown";
    const contexts = ((detail["contexts"] as Array<{ name: string }>) ?? []).map((c) => c.name);
    throw new ContextAmbiguousError(metric, contexts, message);
  }
  if (res.status === 401) throw new AuthError(message);
  if (res.status === 403) throw new AccessDeniedError(message);
  if (res.status === 404) throw new NotFoundError(message);
  if (res.status === 400 || res.status === 422)
    throw new ValidationError(message, res.status, detail);
  throw new USFSDKError(message, res.status, detail);
}

export class USFClient {
  private tokens: TokenStore = { accessToken: "", refreshToken: "", expiresAt: 0 };

  constructor(
    private readonly baseUrl: string,
    private readonly options: {
      context?: string;
      apiKey?: string;
      tenant?: string;
    } = {},
  ) {
    if (options.apiKey) {
      this.tokens.accessToken = options.apiKey;
      this.tokens.expiresAt = Infinity;
    }
  }

  // ── Internal helpers ────────────────────────────────────────────────────────

  private buildHeaders(context?: string): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "User-Agent": "usf-sdk-typescript/0.1.0",
    };
    if (this.tokens.accessToken) {
      headers["Authorization"] = `Bearer ${this.tokens.accessToken}`;
    }
    if (this.options.tenant) {
      headers["X-USF-Tenant-ID"] = this.options.tenant;
    }
    const ctx = context ?? this.options.context;
    if (ctx) headers["X-USF-Context"] = ctx;
    return headers;
  }

  private url(path: string): string {
    return `${this.baseUrl.replace(/\/$/, "")}${path}`;
  }

  private async get<T>(path: string, params?: Record<string, string>, context?: string): Promise<T> {
    const u = new URL(this.url(path));
    if (params) {
      for (const [k, v] of Object.entries(params)) u.searchParams.set(k, v);
    }
    const res = await fetch(u.toString(), { headers: this.buildHeaders(context) });
    await throwForStatus(res);
    return res.json() as Promise<T>;
  }

  private async post<T>(path: string, body: unknown, context?: string): Promise<T> {
    const res = await fetch(this.url(path), {
      method: "POST",
      headers: this.buildHeaders(context),
      body: JSON.stringify(body),
    });
    await throwForStatus(res);
    return res.json() as Promise<T>;
  }

  // ── Auth ────────────────────────────────────────────────────────────────────

  async login(email: string, password: string): Promise<this> {
    const body = await this.post<{ access_token: string; expires_in: number; refresh_token?: string }>(
      "/auth/login",
      { email, password },
    );
    this.tokens.accessToken = body.access_token;
    this.tokens.refreshToken = body.refresh_token ?? "";
    this.tokens.expiresAt = Date.now() + body.expires_in * 1000;
    return this;
  }

  // ── Contexts ────────────────────────────────────────────────────────────────

  async listContexts(): Promise<string[]> {
    const body = await this.get<{ data: ContextInfo[] }>("/contexts");
    return (body.data ?? []).map((c) => c.name);
  }

  // ── Metrics ─────────────────────────────────────────────────────────────────

  async listMetrics(context?: string): Promise<MetricSummary[]> {
    const params: Record<string, string> = {};
    const ctx = context ?? this.options.context;
    if (ctx) params["context"] = ctx;
    const body = await this.get<{ data: MetricSummary[] }>("/metrics", params, context);
    return body.data ?? [];
  }

  async explain(metric: string, context?: string): Promise<MetricExplanation> {
    const body = await this.get<{ data: MetricExplanation }>(
      `/metrics/${encodeURIComponent(metric)}/explain`,
      undefined,
      context,
    );
    return body.data;
  }

  // ── Query ───────────────────────────────────────────────────────────────────

  async query(metric: string, options: QueryOptions = {}): Promise<QueryResult> {
    const { dimensions, filters, timeRange, context } = options;
    const payload: Record<string, unknown> = {
      type: "sql",
      metric,
      options: { include_provenance: true },
    };
    if (dimensions?.length) payload["dimensions"] = dimensions;
    if (filters && Object.keys(filters).length) payload["filters"] = filters;
    if (timeRange) payload["time_range"] = timeRange;

    const ctx = context ?? this.options.context;
    const body = await this.post<{
      data: { columns: string[]; rows: unknown[][]; row_count: number };
      meta: QueryResult["meta"];
    }>("/query", payload, ctx);

    const { columns = [], rows = [], row_count } = body.data;
    const data = rows.map((row) =>
      Array.isArray(row)
        ? Object.fromEntries(columns.map((col, i) => [col, row[i]]))
        : (row as Record<string, unknown>),
    );

    return {
      columns,
      data,
      row_count: row_count ?? data.length,
      meta: body.meta,
      provenance: {
        "prov:wasGeneratedBy": {
          "usf:contextApplied": body.meta?.context,
          "usf:namedGraph": body.meta?.named_graph,
          "usf:queryHash": body.meta?.query_hash,
          "usf:provOUri": body.meta?.prov_o_uri,
        },
      },
    };
  }

  // ── Knowledge Graph ─────────────────────────────────────────────────────────

  async searchEntities(query: string, options: SearchOptions = {}): Promise<EntityResult[]> {
    const params: Record<string, string> = { q: query };
    if (options.entityType) params["entity_type"] = options.entityType;
    if (options.limit) params["limit"] = String(options.limit);
    const body = await this.get<{ data: EntityResult[] }>(
      "/entities/search",
      params,
      options.context,
    );
    return body.data ?? [];
  }

  async getEntity(iri: string, depth = 1): Promise<EntityDetail> {
    const body = await this.get<{ data: EntityDetail }>(
      `/entities/${encodeURIComponent(iri)}`,
      { depth: String(depth) },
    );
    return body.data;
  }

  // ── SPARQL ──────────────────────────────────────────────────────────────────

  async sparql(query: string, context?: string): Promise<Record<string, unknown>[]> {
    const ctx = context ?? this.options.context;
    const body = await this.post<{ data: { rows: Record<string, unknown>[] } }>(
      "/query",
      { type: "sparql", query },
      ctx,
    );
    return body.data?.rows ?? [];
  }
}
