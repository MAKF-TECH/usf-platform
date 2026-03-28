package usf.data_governance

import future.keywords.if
import future.keywords.in

# Data retention policies
retention_years["audit_log"]      = 7  # BCBS 239 / GDPR Art.30
retention_years["query_log"]      = 2
retention_years["ingestion_log"]  = 5

# Sensitive data classification
sensitive_contexts = {"clinical", "pii", "restricted"}

requires_consent(context) if { context in sensitive_contexts }

# Regulatory reporting requirements
bcbs239_required_roles = {"risk_analyst", "cro", "auditor"}
gdpr_dpo_role = "data_protection_officer"
