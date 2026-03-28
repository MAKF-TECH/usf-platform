"""Tests for context resolution middleware — X-USF-Context header logic."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException


async def test_context_header_resolves_correctly():
    """X-USF-Context: finance → ContextResolution with named_graph containing 'finance'."""
    from usf_api.middleware.context_router import resolve_context

    with patch("usf_api.middleware.context_router._get_tenant_contexts", new=AsyncMock(return_value=["finance", "risk"])):
        result = await resolve_context(
            context_header="finance",
            tenant_id="acme-bank",
        )

    assert result.context == "finance"
    assert "finance" in result.named_graph
    assert result.inferred is False


async def test_missing_context_single_option_resolves():
    """No context header, only one context exists → auto-resolve without 409."""
    from usf_api.middleware.context_router import resolve_context

    with patch("usf_api.middleware.context_router._get_tenant_contexts", new=AsyncMock(return_value=["finance"])):
        result = await resolve_context(
            context_header=None,
            tenant_id="acme-bank",
        )

    assert result.context == "finance"
    assert result.inferred is True


async def test_missing_context_ambiguous_raises_409():
    """No context, metric defined in 2 contexts → HTTPException 409 with available_contexts."""
    from usf_api.middleware.context_router import resolve_context

    with patch("usf_api.middleware.context_router._get_tenant_contexts", new=AsyncMock(return_value=["finance", "risk"])), \
         patch("usf_api.middleware.context_router._get_contexts_for_metric", new=AsyncMock(return_value=["finance", "risk"])):
        with pytest.raises(HTTPException) as exc_info:
            await resolve_context(
                context_header=None,
                tenant_id="acme-bank",
                metric_name="total_balance",
            )

    assert exc_info.value.status_code == 409
    detail = exc_info.value.detail
    assert "available_contexts" in detail


async def test_unknown_context_raises_404():
    """X-USF-Context: nonexistent → HTTPException 404."""
    from usf_api.middleware.context_router import resolve_context

    with patch("usf_api.middleware.context_router._get_tenant_contexts", new=AsyncMock(return_value=["finance", "risk"])):
        with pytest.raises(HTTPException) as exc_info:
            await resolve_context(
                context_header="nonexistent",
                tenant_id="acme-bank",
            )

    assert exc_info.value.status_code == 404


async def test_context_resolution_builds_correct_named_graph():
    """Named graph URI follows usf://{tenant}/context/{ctx}/latest pattern."""
    from usf_api.middleware.context_router import resolve_context

    with patch("usf_api.middleware.context_router._get_tenant_contexts", new=AsyncMock(return_value=["finance"])):
        result = await resolve_context(
            context_header="finance",
            tenant_id="acme-bank",
        )

    assert result.named_graph == "usf://acme-bank/context/finance/latest"
