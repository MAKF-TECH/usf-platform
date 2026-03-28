# USF Security Checklist

## Before Production Deployment

- [ ] Generate new JWT RSA keys (`make generate-keys`)
- [ ] Set strong POSTGRES_PASSWORD in .env
- [ ] Set strong ARCADEDB_ROOT_PASSWORD in .env
- [ ] Set JWT_SECRET to a 32-byte random value
- [ ] Enable TLS on all service endpoints
- [ ] Review OPA policies for your industry context
- [ ] Enable PostgreSQL SSL (`sslmode=require`)
- [ ] Configure Redpanda ACLs
- [ ] Enable ArcadeDB authentication
- [ ] Review rate limits in rate_limit.py
- [ ] Audit all CORS origins in usf-api main.py (remove `allow_origins=["*"]` in prod)
- [ ] Enable Grafana auth (disable anonymous access)
- [ ] Review and sign all ABAC policies

## Regulatory Compliance

- [ ] BCBS 239: audit_log retention set to 7 years
- [ ] GDPR Art.30: data processing registry populated
- [ ] Enable PROV-O export for audit trails
- [ ] Test 409 context disambiguation in prod

## Multi-Tenant Verification

- [ ] Verify named graph namespace isolation (no cross-tenant SPARQL)
- [ ] Test OPA tenant_filter enforcement
- [ ] Verify Alembic migrations run cleanly on fresh DB
