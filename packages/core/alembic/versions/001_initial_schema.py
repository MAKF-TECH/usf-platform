"""001_initial_schema

Initial schema for USF Platform.  Creates all core tables in the `usf` schema.
Tables match the SQLModel definitions in usf_core/db_models.py and the
database-schemas.sql reference document.

Revision ID: 001
Revises:
Create Date: 2026-03-28
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, INET, UUID

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enable extensions ────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ── Schema ───────────────────────────────────────────────────────────────
    op.execute("CREATE SCHEMA IF NOT EXISTS usf")
    op.execute("SET search_path TO usf, public")

    # ── tenant ───────────────────────────────────────────────────────────────
    op.create_table(
        "tenant",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("industry", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("ontology_module", sa.Text(), nullable=False),
        sa.Column("kg_namespace", sa.Text(), nullable=False, unique=True),
        sa.Column("plan", sa.Text(), nullable=False, server_default="trial"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="usf",
    )
    op.create_check_constraint(
        "ck_tenant_slug",
        "tenant",
        "slug ~ '^[a-z][a-z0-9-]{2,62}$'",
        schema="usf",
    )
    op.create_check_constraint(
        "ck_tenant_plan",
        "tenant",
        "plan IN ('trial','starter','professional','enterprise')",
        schema="usf",
    )

    # ── user ─────────────────────────────────────────────────────────────────
    op.create_table(
        "user",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("usf.tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="viewer"),
        sa.Column("department", sa.Text(), nullable=True),
        sa.Column("clearance_level", sa.Text(), nullable=False, server_default="internal"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="usf",
    )
    op.create_check_constraint(
        "ck_user_role",
        "user",
        "role IN ('admin','analyst','risk_analyst','finance_analyst','compliance_officer','auditor','viewer','ingestion_operator')",
        schema="usf",
    )
    op.create_check_constraint(
        "ck_user_clearance",
        "user",
        "clearance_level IN ('public','internal','confidential','restricted','top_secret')",
        schema="usf",
    )
    op.create_index("idx_user_tenant_id", "user", ["tenant_id"], schema="usf")

    # ── refresh_token ─────────────────────────────────────────────────────────
    op.create_table(
        "refresh_token",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("usf.user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="usf",
    )

    # ── data_source ───────────────────────────────────────────────────────────
    op.create_table(
        "data_source",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("usf.tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("subtype", sa.Text(), nullable=False),
        sa.Column("connection_config", JSONB(), nullable=False, server_default="{}"),
        sa.Column("schema_snapshot", JSONB(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "name", name="uq_data_source_tenant_name"),
        schema="usf",
    )
    op.create_check_constraint(
        "ck_data_source_type",
        "data_source",
        "type IN ('warehouse','file','api','stream')",
        schema="usf",
    )
    op.create_check_constraint(
        "ck_data_source_status",
        "data_source",
        "status IN ('pending','connected','syncing','error','disconnected')",
        schema="usf",
    )
    op.create_index("idx_data_source_tenant_id", "data_source", ["tenant_id"], schema="usf")

    # ── ingestion_job ─────────────────────────────────────────────────────────
    op.create_table(
        "ingestion_job",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("usf.tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("usf.data_source.id"), nullable=False),
        sa.Column("celery_task_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("mode", sa.Text(), nullable=False, server_default="full"),
        sa.Column("triples_added", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("triples_quarantined", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("documents_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extraction_model", sa.Text(), nullable=True),
        sa.Column("ontology_version", sa.Text(), nullable=True),
        sa.Column("openlineage_run_id", sa.Text(), nullable=True),
        sa.Column("named_graph_uri", sa.Text(), nullable=True),
        sa.Column("trace", JSONB(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        schema="usf",
    )
    op.create_check_constraint(
        "ck_ingestion_job_status",
        "ingestion_job",
        "status IN ('pending','running','complete','failed','cancelled')",
        schema="usf",
    )
    op.create_check_constraint(
        "ck_ingestion_job_mode",
        "ingestion_job",
        "mode IN ('full','incremental')",
        schema="usf",
    )
    op.create_index("idx_ingestion_job_tenant_id", "ingestion_job", ["tenant_id"], schema="usf")
    op.create_index("idx_ingestion_job_status", "ingestion_job", ["tenant_id", "status"], schema="usf")

    # ── sdl_version ───────────────────────────────────────────────────────────
    op.create_table(
        "sdl_version",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("usf.tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("content_yaml", sa.Text(), nullable=False),
        sa.Column("compiled_owl", sa.Text(), nullable=True),
        sa.Column("compiled_sql", JSONB(), nullable=True),
        sa.Column("compiled_r2rml", sa.Text(), nullable=True),
        sa.Column("shacl_shapes", sa.Text(), nullable=True),
        sa.Column("named_graph_uri", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", UUID(as_uuid=True), sa.ForeignKey("usf.user.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "version", name="uq_sdl_version_tenant_version"),
        schema="usf",
    )
    op.create_check_constraint(
        "ck_sdl_version_format",
        "sdl_version",
        "version ~ '^v\\d+$'",
        schema="usf",
    )
    # Only one active SDL version per tenant
    op.execute(
        "CREATE UNIQUE INDEX idx_sdl_version_one_active ON usf.sdl_version(tenant_id) WHERE is_active = TRUE"
    )

    # ── audit_log ─────────────────────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("usf.tenant.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("usf.user.id"), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("metric_or_entity", sa.Text(), nullable=True),
        sa.Column("abac_decision", sa.Text(), nullable=False, server_default="permit"),
        sa.Column("abac_policy_version", sa.Text(), nullable=True),
        sa.Column("abac_filter_applied", sa.Text(), nullable=True),
        sa.Column("query_hash", sa.Text(), nullable=True),
        sa.Column("query_type", sa.Text(), nullable=True),
        sa.Column("prov_o_graph_uri", sa.Text(), nullable=True),
        sa.Column("named_graph_uri", sa.Text(), nullable=True),
        sa.Column("execution_ms", sa.Integer(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("ip_address", INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="usf",
    )
    op.create_check_constraint(
        "ck_audit_log_action",
        "audit_log",
        "action IN ('query','ingest','sdl_publish','sdl_validate','login','logout','access_denied','entity_view','audit_export','context_created','source_registered','job_triggered')",
        schema="usf",
    )
    op.create_check_constraint(
        "ck_audit_log_abac",
        "audit_log",
        "abac_decision IN ('permit','permit_with_filter','deny')",
        schema="usf",
    )
    # RLS policies
    op.execute("ALTER TABLE usf.audit_log ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY audit_log_tenant_isolation ON usf.audit_log FOR SELECT "
        "USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID)"
    )
    op.execute(
        "CREATE POLICY audit_log_insert_only ON usf.audit_log FOR INSERT WITH CHECK (true)"
    )
    op.create_index("idx_audit_log_tenant_created", "audit_log", ["tenant_id", "created_at"], schema="usf")
    op.create_index(
        "idx_audit_log_query_hash", "audit_log", ["query_hash"],
        schema="usf",
        postgresql_where=sa.text("query_hash IS NOT NULL"),
    )

    # ── job_run ───────────────────────────────────────────────────────────────
    op.create_table(
        "job_run",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("usf.tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("celery_task_id", sa.Text(), nullable=False, unique=True),
        sa.Column("task_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("args", JSONB(), nullable=False, server_default="{}"),
        sa.Column("result", JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="usf",
    )
    op.create_check_constraint(
        "ck_job_run_status",
        "job_run",
        "status IN ('pending','running','success','failure','retry','revoked')",
        schema="usf",
    )
    op.create_index("idx_job_run_celery_task_id", "job_run", ["celery_task_id"], schema="usf")

    # ── ontology_module ───────────────────────────────────────────────────────
    op.create_table(
        "ontology_module",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("usf.tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("named_graph_uri", sa.Text(), nullable=False),
        sa.Column("classes_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("properties_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shapes_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "module", "version", name="uq_ontology_module_tenant_module_version"),
        schema="usf",
    )

    # ── context_definition ────────────────────────────────────────────────────
    op.create_table(
        "context_definition",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("usf.tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sdl_version_id", UUID(as_uuid=True), sa.ForeignKey("usf.sdl_version.id"), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("named_graph_uri", sa.Text(), nullable=False),
        sa.Column("parent_context", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "name", "version", name="uq_context_definition_tenant_name_version"),
        schema="usf",
    )
    op.create_check_constraint(
        "ck_context_definition_name",
        "context_definition",
        "name ~ '^[a-z][a-z0-9_-]{0,63}$'",
        schema="usf",
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("context_definition", schema="usf")
    op.drop_table("ontology_module", schema="usf")
    op.drop_table("job_run", schema="usf")
    op.drop_table("audit_log", schema="usf")
    op.drop_table("sdl_version", schema="usf")
    op.drop_table("ingestion_job", schema="usf")
    op.drop_table("data_source", schema="usf")
    op.drop_table("refresh_token", schema="usf")
    op.drop_table("user", schema="usf")
    op.drop_table("tenant", schema="usf")
    op.execute("DROP SCHEMA IF EXISTS usf CASCADE")
