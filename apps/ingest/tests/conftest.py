"""Shared fixtures for usf-ingest tests."""
from __future__ import annotations
import pytest
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock


@pytest.fixture
def mock_usf_kg_client():
    client = AsyncMock()
    client.post_triples.return_value = {"triples_added": 5}
    return client


@pytest.fixture
def sample_schema_info():
    return {
        "primary_keys": ["id"],
        "columns": [
            {"name": "id", "type": "serial"},
            {"name": "bank_name", "type": "varchar"},
            {"name": "amount", "type": "decimal"},
            {"name": "is_suspicious", "type": "boolean"},
            {"name": "created_at", "type": "timestamp"},
        ],
    }


@pytest.fixture
def mock_extraction_result():
    @dataclass
    class FakeExtraction:
        extraction_type: str = "LegalEntity"
        text_span: str = "Deutsche Bank"
        ontology_class: str = "fibo:CommercialBank"
        attributes: dict = None
        char_interval: tuple[int, int] | None = (0, 14)
        confidence_score: float = 0.9
        model_id: str = "test-model"
        chunk_index: int | None = None
        raw: Any = None

        def __post_init__(self):
            if self.attributes is None:
                self.attributes = {}

    return FakeExtraction
