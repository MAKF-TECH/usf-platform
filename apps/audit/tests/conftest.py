"""Shared fixtures for usf-audit tests."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture(autouse=True)
def mock_db():
    with patch("usf_audit.db.create_db_and_tables", new_callable=AsyncMock), \
         patch("usf_audit.services.kafka_consumer.start_kafka_consumer", new_callable=AsyncMock):
        yield
