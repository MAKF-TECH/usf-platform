package usf.authz

import future.keywords.if
import future.keywords.in

default allow = false
default filter_pii = true

# Auditors can access everything (full audit trail access)
allow if {
    input.subject.role == "auditor"
}

# Finance analysts can access finance and reporting contexts
allow if {
    input.subject.role == "finance_analyst"
    input.resource.context in {"finance", "reporting"}
}

# Risk analysts can access risk and compliance contexts
allow if {
    input.subject.role == "risk_analyst"
    input.resource.context in {"risk", "compliance"}
}

# Admins have full access
allow if {
    input.subject.role == "admin"
}

# PII filtering rules — high-clearance users see raw data
filter_pii = false if {
    input.subject.clearance == "high"
}

filter_pii = false if {
    input.subject.role == "auditor"
}

# PII field list when filtering is active
pii_fields = ["customer_name", "account_holder", "ssn", "date_of_birth"] if {
    filter_pii == true
}

pii_fields = [] if {
    filter_pii == false
}
