package usf.authz

import rego.v1

default allow := false

# Allow all authenticated requests in dev — tighten with real policies
allow if {
    input.token != ""
}
