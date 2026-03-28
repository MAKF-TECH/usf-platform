package usf.tenancy

import future.keywords.if

# Tenant isolation — named graph namespace check
# Every query must be scoped to the requesting tenant's namespace
namespace_allowed(tenant_id, graph_uri) if {
    startswith(graph_uri, concat("", ["usf://", tenant_id, "/"]))
}

# Global (shared) ontology graphs are readable by all authenticated tenants
namespace_allowed(_, graph_uri) if {
    startswith(graph_uri, "usf://global/")
}

# Cross-tenant query is never allowed (no exception)
cross_tenant_allowed = false
