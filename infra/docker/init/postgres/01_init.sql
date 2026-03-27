-- USF Platform — PostgreSQL Initialization
-- Runs automatically on first container start via /docker-entrypoint-initdb.d/
-- In production, schema is managed by Alembic migrations.

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ─── TENANTS ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    industry VARCHAR(100) NOT NULL,
    ontology_module VARCHAR(100) NOT NULL,
    kg_namespace VARCHAR(500) NOT NULL,
    plan VARCHAR(50) DEFAULT 'trial',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── USERS ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'viewer',
    department VARCHAR(100),
    clearance_level VARCHAR(50) DEFAULT 'internal',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── AUDIT LOG ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID,
    action VARCHAR(100) NOT NULL,
    context VARCHAR(100),
    metric_or_entity TEXT,
    abac_decision VARCHAR(50) NOT NULL,
    abac_policy_version VARCHAR(50),
    query_hash VARCHAR(64),
    prov_o_graph TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Append-only enforcement on audit_log (immutable audit trail)
CREATE RULE audit_log_no_update AS ON UPDATE TO audit_log DO INSTEAD NOTHING;
CREATE RULE audit_log_no_delete AS ON DELETE TO audit_log DO INSTEAD NOTHING;

-- ─── SEED DATA ───────────────────────────────────────────────
-- Demo tenant for pilot/local development
INSERT INTO tenants (name, slug, industry, ontology_module, kg_namespace, plan)
VALUES ('Acme Bank (Demo)', 'acme-bank', 'banking', 'fibo', 'usf://acme-bank/', 'pilot')
ON CONFLICT DO NOTHING;
