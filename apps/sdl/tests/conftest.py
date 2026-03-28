"""Shared fixtures for usf-sdl tests."""
from __future__ import annotations
import pytest


@pytest.fixture
def sample_sdl():
    return {
        "namespace": "https://usf.makf.tech/ontology/",
        "entities": [
            {
                "name": "Transaction",
                "description": "A financial transaction",
                "fibo_class": "https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/Transaction",
                "fields": [
                    {"name": "amount", "type": "decimal", "required": True, "description": "Amount"},
                    {"name": "currency", "type": "string", "required": True},
                    {"name": "counterparty", "type": "ref(Bank)", "description": "Target bank"},
                ],
            },
            {
                "name": "Bank",
                "description": "A financial institution",
                "fields": [
                    {"name": "name", "type": "string", "required": True},
                    {"name": "swift_code", "type": "string"},
                ],
            },
        ],
        "metrics": [
            {
                "name": "total_exposure",
                "entity": "Transaction",
                "aggregation": "SUM",
                "field": "amount",
                "group_by": ["counterparty.name"],
                "filters": [],
            }
        ],
    }


@pytest.fixture
def sample_table_map():
    return {"Transaction": "transactions", "Bank": "banks"}
