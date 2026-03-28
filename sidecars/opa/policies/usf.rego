package usf.authz

default allow = false

# Allow all by default in dev — tighten with real policies
allow {
    input.token != ""
}
