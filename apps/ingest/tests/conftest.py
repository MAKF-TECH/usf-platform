"""Shared fixtures for usf-ingest tests."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass
from typing import Any


@pytest.fixture
def mock_usf_kg_client():
    client = AsyncMock()
    client.post_triples.return_value = {"triples_added": 5}
    return client


@pytest.fixture
def sample_csv_rows():
    return [
        {
            "From Bank": "Deutsche Bank",
            "Account": "ACC001",
            "To Bank": "BNP Paribas",
            "Account.1": "ACC002",
            "Amount Paid": 50000.0,
            "Payment Currency": "EUR",
            "Amount Received": 50000.0,
            "Receiving Currency": "EUR",
            "Payment Format": "Wire",
            "Is Laundering": 0,
            "Timestamp": "2024-01-15T10:00:00",
        }
    ]


@pytest.fixture
def sample_schema_info():
    """Schema info matching r2rml_generator.generate_r2rml expectations."""
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
    """Factory for ExtractionResult-like objects."""

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
