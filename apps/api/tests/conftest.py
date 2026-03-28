"""Shared fixtures for apps/api tests."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_settings():
    """Mock settings to avoid requiring real infrastructure."""
    settings = MagicMock()
    settings.service_name = "usf-api"
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    settings.opa_url = "http://mock-opa:8181"
    settings.valkey_url = "redis://mock-valkey:6379"
    settings.usf_kg_url = "http://mock-kg:8000"
    settings.usf_query_url = "http://mock-query:8000"
    settings.jwt_algorithm = "HS256"
    settings.jwt_secret = "test-secret"
    settings.jwt_private_key = ""
    settings.jwt_public_key = ""
    return settings


@pytest.fixture
def mock_opa_allow():
    """OPA decision: allow=True, no PII fields."""
    return {
        "result": {
            "allow": True,
            "pii_fields": [],
            "filters": [],
            "policy_version": "v1.0-test",
        }
    }


@pytest.fixture
def mock_opa_deny():
    """OPA decision: allow=False."""
    return {
        "result": {
            "allow": False,
            "pii_fields": [],
            "filters": [],
            "policy_version": "v1.0-test",
        }
    }


@pytest.fixture
def mock_opa_pii():
    """OPA decision: allow=True, PII fields present."""
    return {
        "result": {
            "allow": True,
            "pii_fields": ["email", "ssn", "dob"],
            "filters": [],
            "policy_version": "v1.0-test",
        }
    }
