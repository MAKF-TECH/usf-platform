package usf.authz

import future.keywords.if
import future.keywords.in

default allow = false
default pii_filter_enabled = true

# ── Allow rules ──────────────────────────────────────────────────

# Admin can do anything
allow if { input.subject.role == "admin" }

# Auditor can read all (read-only)
allow if {
    input.subject.role == "auditor"
    input.action == "read"
}

# Finance analyst — finance + reporting contexts
allow if {
    input.subject.role == "finance_analyst"
    input.action == "read"
    input.resource.context in {"finance", "reporting", "consolidation"}
}

# Risk analyst — risk + compliance contexts
allow if {
    input.subject.role == "risk_analyst"
    input.action == "read"
    input.resource.context in {"risk", "compliance", "stress_testing"}
}

# Clinical role (healthcare) — clinical context
allow if {
    input.subject.role == "clinician"
    input.action == "read"
    input.resource.context == "clinical"
}

# Researcher — research context (de-identified only)
allow if {
    input.subject.role == "researcher"
    input.action == "read"
    input.resource.context == "research"
}

# Data steward — can write SDL definitions
allow if {
    input.subject.role == "data_steward"
    input.action in {"read", "write"}
}

# ── PII filtering ────────────────────────────────────────────────

# High clearance = no PII filtering
pii_filter_enabled = false if { input.subject.clearance == "high" }
pii_filter_enabled = false if { input.subject.role in {"auditor", "admin"} }
pii_filter_enabled = true   if {
    not input.subject.clearance == "high"
    not input.subject.role in {"auditor", "admin"}
}

pii_fields = ["customer_name","account_holder","ssn","date_of_birth","email","phone"] if { pii_filter_enabled }
pii_fields = [] if { not pii_filter_enabled }

# ── Row-level security ───────────────────────────────────────────

# Tenant isolation — users can only query their own tenant's data
tenant_filter = input.subject.tenant_id

# Regional restriction
region_filter = input.subject.region if { input.subject.region != null }
region_filter = null if { not input.subject.region }

# ── Audit ────────────────────────────────────────────────────────

# Always log — decision metadata attached to response
audit_required = true
