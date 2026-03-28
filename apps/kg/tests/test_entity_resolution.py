"""Tests for EntityResolutionService — canonical IRI assignment and matching."""
import pytest
from unittest.mock import AsyncMock

from usf_kg.services.entity_resolution import EntityResolutionService, ResolvedEntity


async def test_new_entity_gets_canonical_iri(mock_arcadedb_client, mock_qlever_service):
    """New entity (no ArcadeDB match, no vector match) gets a generated canonical IRI."""
    mock_arcadedb_client.get_node.return_value = None
    mock_arcadedb_client.vector_search.return_value = []

    service = EntityResolutionService(qlever=mock_qlever_service, arcadedb=mock_arcadedb_client)
    result = await service.resolve_entity(
        candidate_label="Deutsche Bank AG",
        ontology_class="fibo:LegalEntity",
        tenant_id="acme-bank",
    )

    assert result.canonical_iri.startswith("usf://acme-bank/entity/")
    assert result.is_new is True
    assert result.confidence == 1.0


async def test_existing_entity_returns_canonical_via_exact_iri(mock_arcadedb_client, mock_qlever_service):
    """Entity with exact IRI match returns canonical IRI from ArcadeDB."""
    existing_iri = "usf://acme/entity/LegalEntity/abc12345"
    mock_arcadedb_client.get_node.return_value = {"iri": existing_iri}

    service = EntityResolutionService(qlever=mock_qlever_service, arcadedb=mock_arcadedb_client)
    result = await service.resolve_entity(
        candidate_label="https://example.com/entity/DeutscheBank",  # starts with http → exact lookup
        ontology_class="fibo:LegalEntity",
        tenant_id="acme",
    )

    assert result.canonical_iri == existing_iri
    assert result.is_new is False
    assert result.confidence == 1.0


async def test_vector_match_returns_existing_iri(mock_arcadedb_client, mock_qlever_service):
    """Entity resolved via high-confidence vector search returns existing IRI."""
    matched_iri = "usf://acme/entity/LegalEntity/abc99999"
    mock_arcadedb_client.get_node.return_value = None  # not an exact IRI
    mock_arcadedb_client.vector_search.return_value = [
        {"iri": matched_iri, "score": 0.93},
    ]

    service = EntityResolutionService(qlever=mock_qlever_service, arcadedb=mock_arcadedb_client)
    result = await service.resolve_entity(
        candidate_label="Deutsche Bank",
        ontology_class="fibo:LegalEntity",
        tenant_id="acme",
        embedding=[0.1, 0.2, 0.3],  # provide embedding to trigger vector search
    )

    assert result.canonical_iri == matched_iri
    assert result.is_new is False
    assert result.confidence >= 0.85


async def test_low_score_vector_match_creates_new_entity(mock_arcadedb_client, mock_qlever_service):
    """Vector match below threshold (0.85) → new entity is created."""
    mock_arcadedb_client.get_node.return_value = None
    mock_arcadedb_client.vector_search.return_value = [
        {"iri": "usf://acme/entity/LegalEntity/xyz", "score": 0.60},  # below threshold
    ]

    service = EntityResolutionService(qlever=mock_qlever_service, arcadedb=mock_arcadedb_client)
    result = await service.resolve_entity(
        candidate_label="Some Other Bank",
        ontology_class="fibo:LegalEntity",
        tenant_id="acme",
        embedding=[0.9, 0.8, 0.7],
    )

    assert result.is_new is True
    assert result.canonical_iri.startswith("usf://acme/entity/")


async def test_canonical_iri_is_deterministic(mock_arcadedb_client, mock_qlever_service):
    """Same label + class + tenant always generates the same canonical IRI."""
    mock_arcadedb_client.get_node.return_value = None
    mock_arcadedb_client.vector_search.return_value = []

    service = EntityResolutionService(qlever=mock_qlever_service, arcadedb=mock_arcadedb_client)

    result_1 = await service.resolve_entity("ACME Corp", "fibo:Organization", "tenant-x")
    result_2 = await service.resolve_entity("ACME Corp", "fibo:Organization", "tenant-x")

    assert result_1.canonical_iri == result_2.canonical_iri
