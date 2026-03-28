"""Tests for ProvOBuilder — PROV-O JSON-LD block generation."""
import pytest

from usf_rdf.prov import ProvOBuilder


def test_build_query_prov_has_required_fields():
    """PROV-O query block must have @type, prov:wasAssociatedWith, @context."""
    builder = ProvOBuilder()
    doc = builder.query_activity(
        query_hash="deadbeef",
        context="finance/v1",
        user_iri="https://usf.makf.tech/user/u-001",
        sparql_text="SELECT ?s ?p ?o WHERE { ?s ?p ?o }",
    )

    assert "@type" in doc, "Missing @type"
    assert "prov:wasAssociatedWith" in doc, "Missing prov:wasAssociatedWith"
    assert doc["prov:wasAssociatedWith"]["@id"] == "https://usf.makf.tech/user/u-001"
    assert "prov:startedAtTime" in doc
    assert "prov:endedAtTime" in doc


def test_prov_json_ld_is_valid_structure():
    """JSON-LD block is a valid dict with @context and @type keys."""
    builder = ProvOBuilder()
    doc = builder.query_activity(query_hash="abc123")

    assert isinstance(doc, dict)
    assert "@context" in doc
    assert "@type" in doc
    assert doc["@type"] == "prov:Activity"
    assert isinstance(doc["@context"], dict)
    assert "prov" in doc["@context"]


def test_ingestion_prov_has_triples_added():
    """Ingestion PROV-O block includes usf:triplesAdded and prov:used."""
    builder = ProvOBuilder()
    doc = builder.ingestion_activity(
        job_id="job-999",
        source_iri="https://usf.makf.tech/source/erp-v2",
        tenant_iri="https://usf.makf.tech/tenant/acme",
        triples_added=4321,
    )

    assert doc["usf:triplesAdded"] == 4321
    assert "prov:used" in doc
    assert doc["prov:used"]["@id"] == "https://usf.makf.tech/source/erp-v2"


def test_entity_derivation_has_was_derived_from():
    """entity_derivation block includes prov:wasDerivedFrom for each source."""
    builder = ProvOBuilder()
    doc = builder.entity_derivation(
        entity_iri="usf://acme/entity/Account/abc123",
        derived_from_iris=[
            "https://source1.example.com/acc",
            "https://source2.example.com/acc",
        ],
    )

    assert "@type" in doc
    assert doc["@type"] == "prov:Entity"
    assert "prov:wasDerivedFrom" in doc
    assert len(doc["prov:wasDerivedFrom"]) == 2


def test_query_activity_iri_contains_query_hash():
    """Activity IRI is stable and contains the query hash."""
    builder = ProvOBuilder()
    doc = builder.query_activity(query_hash="myhash")

    assert "myhash" in doc["@id"]


def test_ingestion_activity_optional_fields():
    """Optional fields (ontology_version, extraction_model) appear when provided."""
    builder = ProvOBuilder()
    doc = builder.ingestion_activity(
        job_id="job-100",
        source_iri="https://usf.makf.tech/source/s1",
        tenant_iri="https://usf.makf.tech/tenant/t1",
        triples_added=10,
        ontology_version="fibo-2024-q1",
        extraction_model="langextract-v2",
        named_graph_iri="usf://acme/context/finance/v1",
    )

    assert doc["usf:ontologyVersion"] == "fibo-2024-q1"
    assert doc["usf:extractionModel"] == "langextract-v2"
    assert "prov:generated" in doc
    assert doc["prov:generated"]["@id"] == "usf://acme/context/finance/v1"
