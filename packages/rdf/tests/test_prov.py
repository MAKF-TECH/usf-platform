"""Tests for ProvOBuilder."""
from usf_rdf.prov import ProvOBuilder


def test_query_activity():
    p = ProvOBuilder()
    doc = p.query_activity(
        query_hash="abc123",
        context="risk/v1",
        user_iri="https://usf.makf.tech/user/u1",
    )
    assert doc["usf:queryHash"] == "abc123"
    assert doc["prov:wasAssociatedWith"]["@id"] == "https://usf.makf.tech/user/u1"
    assert "prov:startedAtTime" in doc


def test_ingestion_activity():
    p = ProvOBuilder()
    doc = p.ingestion_activity(
        job_id="job-001",
        source_iri="https://usf.makf.tech/source/s1",
        tenant_iri="https://usf.makf.tech/tenant/acme",
        triples_added=1234,
        extraction_model="langextract-fibo-v1",
    )
    assert doc["usf:triplesAdded"] == 1234
    assert doc["usf:extractionModel"] == "langextract-fibo-v1"
