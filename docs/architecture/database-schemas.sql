-- USF PostgreSQL Database Schema v1.0.0 — FROZEN — 2026-03-27
-- Author: usf-architect
-- SQLModel-aligned. Run: alembic upgrade head
-- Requires: CREATE EXTENSION "uuid-ossp"; CREATE EXTENSION "pgcrypto";

CREATE SCHEMA IF NOT EXISTS usf;
SET search_path TO usf, public;

CREATE TABLE tenant (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT        NOT NULL,
    industry        TEXT        NOT NULL CHECK (industry IN ('banking','healthcare','energy','retail','telecom','manufacturing','public_sector','other')),
    slug            TEXT        NOT NULL UNIQUE CHECK (slug ~ '^[a-z][a-z0-9-]{2,62}$'),
    ontology_module TEXT        NOT NULL,
    kg_namespace    TEXT        NOT NULL UNIQUE,
    plan            TEXT        NOT NULL DEFAULT 'trial' CHECK (plan IN ('trial','starter','professional','enterprise')),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE "user" (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    email           TEXT        NOT NULL UNIQUE,
    hashed_password TEXT        NOT NULL,
    role            TEXT        NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin','analyst','risk_analyst','finance_analyst','compliance_officer','auditor','viewer','ingestion_operator')),
    department      TEXT,
    clearance_level TEXT        NOT NULL DEFAULT 'internal' CHECK (clearance_level IN ('public','internal','confidential','restricted','top_secret')),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE refresh_token (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    token_hash  TEXT        NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE data_source (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID        NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    name                TEXT        NOT NULL,
    type                TEXT        NOT NULL CHECK (type IN ('warehouse','file','api','stream')),
    subtype             TEXT        NOT NULL,
    connection_config   JSONB       NOT NULL DEFAULT '{}',
    schema_snapshot     JSONB,
    status              TEXT        NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','connected','syncing','error','disconnected')),
    last_synced_at      TIMESTAMPTZ,
    last_error          TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, name)
);

CREATE TABLE ingestion_job (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID        NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    source_id               UUID        NOT NULL REFERENCES data_source(id),
    celery_task_id          TEXT,
    status                  TEXT        NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','complete','failed','cancelled')),
    mode                    TEXT        NOT NULL DEFAULT 'full' CHECK (mode IN ('full','incremental')),
    triples_added           INTEGER     NOT NULL DEFAULT 0,
    triples_quarantined     INTEGER     NOT NULL DEFAULT 0,
    documents_processed     INTEGER     NOT NULL DEFAULT 0,
    extraction_model        TEXT,
    ontology_version        TEXT,
    openlineage_run_id      TEXT,
    named_graph_uri         TEXT,
    trace                   JSONB       NOT NULL DEFAULT '{}',
    error_message           TEXT,
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ
);

CREATE TABLE sdl_version (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    version         TEXT        NOT NULL CHECK (version ~ '^v\d+$'),
    content_yaml    TEXT        NOT NULL,
    compiled_owl    TEXT,
    compiled_sql    JSONB,
    compiled_r2rml  TEXT,
    shacl_shapes    TEXT,
    named_graph_uri TEXT,
    is_active       BOOLEAN     NOT NULL DEFAULT FALSE,
    changelog       TEXT,
    published_at    TIMESTAMPTZ,
    published_by    UUID        REFERENCES "user"(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, version)
);

-- Only one active SDL version per tenant
CREATE UNIQUE INDEX idx_sdl_version_one_active ON sdl_version(tenant_id) WHERE is_active = TRUE;

CREATE TABLE audit_log (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID        NOT NULL REFERENCES tenant(id),
    user_id             UUID        REFERENCES "user"(id),
    action              TEXT        NOT NULL CHECK (action IN ('query','ingest','sdl_publish','sdl_validate','login','logout','access_denied','entity_view','audit_export','context_created','source_registered','job_triggered')),
    context             TEXT,
    metric_or_entity    TEXT,
    abac_decision       TEXT        NOT NULL DEFAULT 'permit' CHECK (abac_decision IN ('permit','permit_with_filter','deny')),
    abac_policy_version TEXT,
    abac_filter_applied TEXT,
    query_hash          TEXT,
    query_type          TEXT,
    prov_o_graph_uri    TEXT,
    named_graph_uri     TEXT,
    execution_ms        INTEGER,
    row_count           INTEGER,
    ip_address          INET,
    user_agent          TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS: append-only audit log
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_log_tenant_isolation ON audit_log FOR SELECT
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);
CREATE POLICY audit_log_insert_only ON audit_log FOR INSERT WITH CHECK (true);
-- REVOKE UPDATE, DELETE ON audit_log FROM usf_app;  -- run as superuser

CREATE TABLE job_run (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    celery_task_id  TEXT        NOT NULL UNIQUE,
    task_name       TEXT        NOT NULL,
    status          TEXT        NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','success','failure','retry','revoked')),
    args            JSONB       NOT NULL DEFAULT '{}',
    result          JSONB,
    error           TEXT,
    retry_count     INTEGER     NOT NULL DEFAULT 0,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ontology_module (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID        NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    module           TEXT        NOT NULL,
    version          TEXT        NOT NULL,
    named_graph_uri  TEXT        NOT NULL,
    classes_count    INTEGER     NOT NULL DEFAULT 0,
    properties_count INTEGER     NOT NULL DEFAULT 0,
    shapes_count     INTEGER     NOT NULL DEFAULT 0,
    is_active        BOOLEAN     NOT NULL DEFAULT TRUE,
    loaded_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, module, version)
);

CREATE TABLE context_definition (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    sdl_version_id  UUID        REFERENCES sdl_version(id),
    name            TEXT        NOT NULL CHECK (name ~ '^[a-z][a-z0-9_-]{0,63}$'),
    description     TEXT        NOT NULL,
    named_graph_uri TEXT        NOT NULL,
    parent_context  TEXT,
    version         INTEGER     NOT NULL DEFAULT 1,
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, name, version)
);

-- Key indexes
CREATE INDEX idx_user_tenant_id ON "user"(tenant_id);
CREATE INDEX idx_data_source_tenant_id ON data_source(tenant_id);
CREATE INDEX idx_ingestion_job_tenant_id ON ingestion_job(tenant_id);
CREATE INDEX idx_ingestion_job_status ON ingestion_job(tenant_id, status);
CREATE INDEX idx_audit_log_tenant_created ON audit_log(tenant_id, created_at DESC);
CREATE INDEX idx_audit_log_query_hash ON audit_log(query_hash) WHERE query_hash IS NOT NULL;
CREATE INDEX idx_job_run_celery_task_id ON job_run(celery_task_id);

-- Alembic: alembic revision --autogenerate -m "initial_schema_v1" && alembic upgrade head
