-- USF PostgreSQL Database Schema
-- Version: 1.0.0
-- Status: FROZEN
-- Date: 2026-03-27
-- Author: usf-architect
--
-- This file is the canonical SQLModel-aligned schema definition.
-- Alembic migrations are generated from SQLModel class definitions in packages/core.
-- All tables use UUID primary keys and UTC timestamps.
-- Row-Level Security (RLS) is enabled on audit_log for append-only enforcement.
--
-- Migration notes:
--   alembic revision --autogenerate -m "initial_schema"
--   alembic upgrade head
--
-- Extensions required:
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─────────────────────────────────────────────────────────────────
-- SCHEMA SETUP
-- ─────────────────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS usf;
SET search_path TO usf, public;

-- ─────────────────────────────────────────────────────────────────
-- TABLE: tenant
-- Represents a tenant (organization) on the USF platform.
-- Slugs are globally unique and immutable after creation.
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE tenant (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT        NOT NULL,
    industry        TEXT        NOT NULL,                    -- banking | healthcare | energy | retail | ...
    slug            TEXT        NOT NULL UNIQUE,             -- URL-safe, globally unique, immutable
    ontology_module TEXT        NOT NULL,                    -- fibo | fhir | iec-cim | rami40 | ...
    kg_namespace    TEXT        NOT NULL UNIQUE,             -- usf://{slug}/ — base URI for all tenant graphs
    plan            TEXT        NOT NULL DEFAULT 'trial',    -- trial | starter | professional | enterprise
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Slug must be lowercase alphanumeric + hyphens, 3-63 chars
ALTER TABLE tenant ADD CONSTRAINT tenant_slug_format
    CHECK (slug ~ '^[a-z][a-z0-9-]{2,62}$');

ALTER TABLE tenant ADD CONSTRAINT tenant_industry_valid
    CHECK (industry IN ('banking', 'healthcare', 'energy', 'retail', 'telecom', 'manufacturing', 'public_sector', 'other'));

ALTER TABLE tenant ADD CONSTRAINT tenant_plan_valid
    CHECK (plan IN ('trial', 'starter', 'professional', 'enterprise'));

CREATE INDEX idx_tenant_slug ON tenant(slug);

-- SQLModel: class Tenant(SQLModel, table=True): __tablename__ = "tenant"

-- ─────────────────────────────────────────────────────────────────
-- TABLE: "user"
-- A user belonging to a tenant. Email is globally unique.
-- Roles are tenant-scoped (a user in tenant A cannot access tenant B).
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE "user" (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID        NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    email               TEXT        NOT NULL UNIQUE,
    hashed_password     TEXT        NOT NULL,
    role                TEXT        NOT NULL DEFAULT 'viewer',
    department          TEXT,                                -- optional org unit
    clearance_level     TEXT        NOT NULL DEFAULT 'internal',
    is_active           BOOLEAN     NOT NULL DEFAULT TRUE,
    last_login_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE "user" ADD CONSTRAINT user_role_valid
    CHECK (role IN ('admin', 'analyst', 'risk_analyst', 'finance_analyst', 'compliance_officer',
                    'auditor', 'viewer', 'ingestion_operator'));

ALTER TABLE "user" ADD CONSTRAINT user_clearance_valid
    CHECK (clearance_level IN ('public', 'internal', 'confidential', 'restricted', 'top_secret'));

CREATE INDEX idx_user_tenant_id ON "user"(tenant_id);
CREATE INDEX idx_user_email ON "user"(email);
CREATE INDEX idx_user_tenant_role ON "user"(tenant_id, role);

-- SQLModel: class User(SQLModel, table=True): __tablename__ = "user"

-- ─────────────────────────────────────────────────────────────────
-- TABLE: refresh_token
-- Opaque refresh tokens for JWT refresh flow.
-- HttpOnly cookie contains the token value. DB stores hash.
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE refresh_token (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    token_hash      TEXT        NOT NULL UNIQUE,             -- SHA-256 of the opaque token
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_token_user_id ON refresh_token(user_id);
CREATE INDEX idx_refresh_token_hash ON refresh_token(token_hash);

-- ─────────────────────────────────────────────────────────────────
-- TABLE: data_source
-- A registered data source for a tenant.
-- connection_config is encrypted at the application layer before storage.
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE data_source (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID        NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    name                TEXT        NOT NULL,
    type                TEXT        NOT NULL,                -- warehouse | file | api | stream
    subtype             TEXT        NOT NULL,                -- postgres | snowflake | bigquery | csv | pdf | fhir | ...
    connection_config   JSONB       NOT NULL DEFAULT '{}',   -- encrypted connection details
    schema_snapshot     JSONB,                               -- last introspected schema (column names + types)
    status              TEXT        NOT NULL DEFAULT 'pending',
    last_synced_at      TIMESTAMPTZ,
    last_error          TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE data_source ADD CONSTRAINT data_source_type_valid
    CHECK (type IN ('warehouse', 'file', 'api', 'stream'));

ALTER TABLE data_source ADD CONSTRAINT data_source_status_valid
    CHECK (status IN ('pending', 'connected', 'syncing', 'error', 'disconnected'));

-- Tenant + name must be unique (a tenant cannot have two sources with the same name)
ALTER TABLE data_source ADD CONSTRAINT data_source_tenant_name_unique
    UNIQUE (tenant_id, name);

CREATE INDEX idx_data_source_tenant_id ON data_source(tenant_id);
CREATE INDEX idx_data_source_type ON data_source(tenant_id, type);

-- SQLModel: class DataSource(SQLModel, table=True): __tablename__ = "data_source"

-- ─────────────────────────────────────────────────────────────────
-- TABLE: ingestion_job
-- Records each ingestion job triggered for a data source.
-- trace stores the full Layer 1 trace for the UI Layer Debug Panel.
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE ingestion_job (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID        NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    source_id               UUID        NOT NULL REFERENCES data_source(id),
    celery_task_id          TEXT,                            -- Celery async task ID
    status                  TEXT        NOT NULL DEFAULT 'pending',
    mode                    TEXT        NOT NULL DEFAULT 'full',  -- full | incremental
    triples_added           INTEGER     NOT NULL DEFAULT 0,
    triples_quarantined     INTEGER     NOT NULL DEFAULT 0,
    documents_processed     INTEGER     NOT NULL DEFAULT 0,
    extraction_model        TEXT,                            -- gemini-1.5-pro | gpt-4o | ...
    ontology_version        TEXT,                            -- fibo-2024-Q4 | fhir-r4 | ...
    openlineage_run_id      TEXT,                            -- OpenLineage RunEvent run.runId
    named_graph_uri         TEXT,                            -- usf://{tenant}/instance/{source}/{batch}
    trace                   JSONB       NOT NULL DEFAULT '{}',  -- full L1 trace for UI
    error_message           TEXT,
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ
);

ALTER TABLE ingestion_job ADD CONSTRAINT ingestion_job_status_valid
    CHECK (status IN ('pending', 'running', 'complete', 'failed', 'cancelled'));

ALTER TABLE ingestion_job ADD CONSTRAINT ingestion_job_mode_valid
    CHECK (mode IN ('full', 'incremental'));

CREATE INDEX idx_ingestion_job_tenant_id ON ingestion_job(tenant_id);
CREATE INDEX idx_ingestion_job_source_id ON ingestion_job(source_id);
CREATE INDEX idx_ingestion_job_status ON ingestion_job(tenant_id, status);
CREATE INDEX idx_ingestion_job_started_at ON ingestion_job(tenant_id, started_at DESC);

-- SQLModel: class IngestionJob(SQLModel, table=True): __tablename__ = "ingestion_job"

-- ─────────────────────────────────────────────────────────────────
-- TABLE: sdl_version
-- Each published SDL YAML file becomes a version record.
-- Only one version may be active (is_active=true) per tenant at a time.
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE sdl_version (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    version         TEXT        NOT NULL,                    -- v1, v2, v3, ...
    content_yaml    TEXT        NOT NULL,                    -- raw SDL YAML (immutable)
    compiled_owl    TEXT,                                    -- Turtle serialization of compiled OWL
    compiled_sql    JSONB,                                   -- {"postgres": "...", "snowflake": "..."}
    compiled_r2rml  TEXT,                                    -- R2RML Turtle serialization
    shacl_shapes    TEXT,                                    -- SHACL shapes Turtle
    named_graph_uri TEXT,                                    -- usf://{tenant}/schema/v{n}
    is_active       BOOLEAN     NOT NULL DEFAULT FALSE,
    changelog       TEXT,                                    -- human description of changes
    published_at    TIMESTAMPTZ,
    published_by    UUID        REFERENCES "user"(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tenant + version must be unique
ALTER TABLE sdl_version ADD CONSTRAINT sdl_version_tenant_version_unique
    UNIQUE (tenant_id, version);

-- Version format: v followed by one or more digits
ALTER TABLE sdl_version ADD CONSTRAINT sdl_version_format
    CHECK (version ~ '^v\d+$');

CREATE INDEX idx_sdl_version_tenant_id ON sdl_version(tenant_id);
CREATE INDEX idx_sdl_version_active ON sdl_version(tenant_id, is_active);

-- Ensure only one active version per tenant (partial unique index)
CREATE UNIQUE INDEX idx_sdl_version_one_active
    ON sdl_version(tenant_id) WHERE is_active = TRUE;

-- SQLModel: class SDLVersion(SQLModel, table=True): __tablename__ = "sdl_version"

-- ─────────────────────────────────────────────────────────────────
-- TABLE: audit_log
-- Append-only compliance log. Every query, ingestion, SDL publish, login.
-- RLS policy prevents UPDATE and DELETE for the app role.
-- Retention: 7 years minimum (BCBS 239).
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE audit_log (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID        NOT NULL REFERENCES tenant(id),
    user_id                 UUID        REFERENCES "user"(id),
    action                  TEXT        NOT NULL,            -- query | ingest | sdl_publish | login | logout | access_denied
    context                 TEXT,                            -- finance | risk | ops | null
    metric_or_entity        TEXT,                            -- metric name or entity IRI
    abac_decision           TEXT        NOT NULL DEFAULT 'permit',
    abac_policy_version     TEXT,
    abac_filter_applied     TEXT,                            -- SQL WHERE clause injected
    query_hash              TEXT,                            -- SHA-256 of the query
    query_type              TEXT,                            -- sql | sparql | nl | ograg | mcp
    prov_o_graph_uri        TEXT,                            -- usf://{tenant}/provenance/{date}
    named_graph_uri         TEXT,                            -- named graph accessed
    execution_ms            INTEGER,
    row_count               INTEGER,
    ip_address              INET,
    user_agent              TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE audit_log ADD CONSTRAINT audit_log_action_valid
    CHECK (action IN ('query', 'ingest', 'sdl_publish', 'sdl_validate', 'login', 'logout',
                      'access_denied', 'entity_view', 'audit_export', 'context_created',
                      'source_registered', 'job_triggered'));

ALTER TABLE audit_log ADD CONSTRAINT audit_log_abac_decision_valid
    CHECK (abac_decision IN ('permit', 'permit_with_filter', 'deny'));

-- Partitioning by month for performance at scale (Alembic: add via manual migration)
-- For initial deployment, a single table with indexes is sufficient.
CREATE INDEX idx_audit_log_tenant_id ON audit_log(tenant_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(tenant_id, created_at DESC);
CREATE INDEX idx_audit_log_user_id ON audit_log(tenant_id, user_id);
CREATE INDEX idx_audit_log_action ON audit_log(tenant_id, action);
CREATE INDEX idx_audit_log_query_hash ON audit_log(query_hash) WHERE query_hash IS NOT NULL;
CREATE INDEX idx_audit_log_context ON audit_log(tenant_id, context) WHERE context IS NOT NULL;

-- ROW LEVEL SECURITY — append-only enforcement
-- The app DB role (usf_app) can INSERT but not UPDATE or DELETE.
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- App role can only SELECT rows belonging to their tenant and INSERT new rows
CREATE POLICY audit_log_tenant_isolation ON audit_log
    FOR SELECT
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);

CREATE POLICY audit_log_insert_only ON audit_log
    FOR INSERT
    WITH CHECK (true);  -- App inserts anything; tenant filtering is at app layer

-- Revoke UPDATE and DELETE from app role (enforce at DB level)
-- Run as superuser:
-- REVOKE UPDATE, DELETE ON audit_log FROM usf_app;

-- SQLModel: class AuditLog(SQLModel, table=True): __tablename__ = "audit_log"

-- ─────────────────────────────────────────────────────────────────
-- TABLE: job_run
-- Celery task execution records (result backend).
-- Tracks all async tasks: ingestion, recompile, cache warm, export.
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE job_run (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    celery_task_id  TEXT        NOT NULL UNIQUE,
    task_name       TEXT        NOT NULL,                    -- ingest_structured_source | ingest_document | ...
    status          TEXT        NOT NULL DEFAULT 'pending',
    args            JSONB       NOT NULL DEFAULT '{}',       -- task arguments (no secrets)
    result          JSONB,                                   -- task result (on success)
    error           TEXT,                                    -- error message (on failure)
    retry_count     INTEGER     NOT NULL DEFAULT 0,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE job_run ADD CONSTRAINT job_run_status_valid
    CHECK (status IN ('pending', 'running', 'success', 'failure', 'retry', 'revoked'));

CREATE INDEX idx_job_run_tenant_id ON job_run(tenant_id);
CREATE INDEX idx_job_run_celery_task_id ON job_run(celery_task_id);
CREATE INDEX idx_job_run_status ON job_run(tenant_id, status);
CREATE INDEX idx_job_run_created_at ON job_run(tenant_id, created_at DESC);

-- SQLModel: class JobRun(SQLModel, table=True): __tablename__ = "job_run"

-- ─────────────────────────────────────────────────────────────────
-- TABLE: ontology_module
-- Registry of loaded industry ontology modules per tenant.
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE ontology_module (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    module          TEXT        NOT NULL,                    -- fibo | fhir | iec-cim | rami40 | ...
    version         TEXT        NOT NULL,                    -- 2024-Q4 | r4 | ...
    named_graph_uri TEXT        NOT NULL,                    -- usf://{tenant}/ontology/{module}/{version}
    classes_count   INTEGER     NOT NULL DEFAULT 0,
    properties_count INTEGER    NOT NULL DEFAULT 0,
    shapes_count    INTEGER     NOT NULL DEFAULT 0,
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE ontology_module ADD CONSTRAINT ontology_module_tenant_module_version_unique
    UNIQUE (tenant_id, module, version);

CREATE INDEX idx_ontology_module_tenant_id ON ontology_module(tenant_id);

-- SQLModel: class OntologyModule(SQLModel, table=True): __tablename__ = "ontology_module"

-- ─────────────────────────────────────────────────────────────────
-- TABLE: context_definition
-- Stores the SDL-declared context metadata (mirrors the SDL YAML context block).
-- The named graph URI is the pointer to the QLever graph.
-- ─────────────────────────────────────────────────────────────────

CREATE TABLE context_definition (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    sdl_version_id  UUID        REFERENCES sdl_version(id),
    name            TEXT        NOT NULL,                    -- slug: finance | risk | ops
    description     TEXT        NOT NULL,
    named_graph_uri TEXT        NOT NULL,                    -- usf://{tenant}/context/{name}/v{n}
    parent_context  TEXT,                                    -- parent context name, if any
    version         INTEGER     NOT NULL DEFAULT 1,
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE context_definition ADD CONSTRAINT context_definition_name_format
    CHECK (name ~ '^[a-z][a-z0-9_-]{0,63}$');

ALTER TABLE context_definition ADD CONSTRAINT context_definition_tenant_name_version_unique
    UNIQUE (tenant_id, name, version);

CREATE INDEX idx_context_definition_tenant_id ON context_definition(tenant_id);
CREATE INDEX idx_context_definition_name ON context_definition(tenant_id, name, is_active);

-- ─────────────────────────────────────────────────────────────────
-- ALEMBIC MIGRATION COMMENTS
-- ─────────────────────────────────────────────────────────────────
--
-- Initial migration (run once):
--   alembic revision --autogenerate -m "initial_schema_v1"
--   alembic upgrade head
--
-- To create the app DB role with restricted permissions:
--   CREATE ROLE usf_app LOGIN PASSWORD '${APP_DB_PASSWORD}';
--   GRANT CONNECT ON DATABASE usf TO usf_app;
--   GRANT USAGE ON SCHEMA usf TO usf_app;
--   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA usf TO usf_app;
--   REVOKE UPDATE, DELETE ON audit_log FROM usf_app;
--   GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA usf TO usf_app;
--
-- For partitioned audit_log (production, post-pilot):
--   alembic revision -m "partition_audit_log_by_month"
--   # Convert audit_log to PARTITION BY RANGE (created_at)
--   # Create monthly partition tables: audit_log_2026_03, audit_log_2026_04, ...
--   # Use pg_partman for automated partition management
--
-- Future migrations:
--   v1.1: Add pgvector extension + entity_embedding table for entity resolution
--   v1.2: Partition ingestion_job by tenant_id HASH (when >10 tenants)
--   v1.3: Add sdl_metric and sdl_entity denormalized tables for fast catalog queries
