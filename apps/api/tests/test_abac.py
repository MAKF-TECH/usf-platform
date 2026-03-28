"""Tests for ABAC (Attribute-Based Access Control) via OPA."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from usf_api.middleware.abac import TokenClaims, ResourceRequest, ABACDecision, check_abac


def _make_user(role: str, clearance: str = "internal", department: str = "finance") -> TokenClaims:
    return TokenClaims(
        sub=f"user-{role}",
        tenant_id="acme-bank",
        role=role,
        department=department,
        clearance=clearance,
    )


def _make_resource(context: str = "finance", metric: str = "total_balance") -> ResourceRequest:
    return ResourceRequest(context=context, metric=metric, action="read")


async def test_finance_analyst_can_read_finance_context():
    """Mock OPA returns allow=true for finance_analyst + finance context."""
    user = _make_user("finance_analyst")
    resource = _make_resource("finance")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "result": {"allow": True, "pii_fields": [], "filters": [], "policy_version": "v1"}
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("usf_api.middleware.abac.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client_cls:
        mock_settings.opa_url = "http://mock-opa:8181"
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        decision = await check_abac(user, resource)

    assert decision.allow is True
    assert decision.pii_fields == []


async def test_risk_analyst_blocked_from_finance():
    """Mock OPA returns allow=false → ABACDecision with allow=False."""
    user = _make_user("risk_analyst", department="risk")
    resource = _make_resource("finance")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "result": {"allow": False, "pii_fields": [], "filters": [], "policy_version": "v1"}
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("usf_api.middleware.abac.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client_cls:
        mock_settings.opa_url = "http://mock-opa:8181"
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        decision = await check_abac(user, resource)

    assert decision.allow is False


async def test_auditor_can_read_all():
    """Auditor role + any context → allow=true."""
    user = _make_user("auditor", clearance="confidential")
    resource = _make_resource("risk")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "result": {"allow": True, "pii_fields": [], "filters": [], "policy_version": "v1"}
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("usf_api.middleware.abac.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client_cls:
        mock_settings.opa_url = "http://mock-opa:8181"
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        decision = await check_abac(user, resource)

    assert decision.allow is True


async def test_pii_filter_applied_for_low_clearance():
    """Low clearance user → pii_fields list is non-empty in ABACDecision."""
    user = _make_user("analyst", clearance="public")
    resource = _make_resource("finance")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "result": {
            "allow": True,
            "pii_fields": ["email", "ssn", "dob"],
            "filters": [],
            "policy_version": "v1",
        }
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("usf_api.middleware.abac.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client_cls:
        mock_settings.opa_url = "http://mock-opa:8181"
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        decision = await check_abac(user, resource)

    assert len(decision.pii_fields) > 0
    assert "email" in decision.pii_fields


async def test_abac_fails_closed_when_opa_unreachable():
    """When OPA is unreachable, check_abac returns allow=False (fail-closed)."""
    import httpx
    user = _make_user("finance_analyst")
    resource = _make_resource("finance")

    with patch("usf_api.middleware.abac.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client_cls:
        mock_settings.opa_url = "http://mock-opa:8181"
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        mock_client_cls.return_value = mock_client

        decision = await check_abac(user, resource)

    assert decision.allow is False
