"""Shared API error response models for OpenAPI documentation."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    """Generic error response."""
    error: str
    message: str
    details: dict | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "details": {"trace_id": "abc-123"}
            }]
        }
    )


class ContextAmbiguousErrorResponse(BaseModel):
    """Returned when a metric exists in multiple contexts and no X-USF-Context header is set."""
    error: str = "context_ambiguous"
    metric: str
    available_contexts: list[str]
    hint: str = "Set X-USF-Context header to one of the available_contexts"

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "error": "context_ambiguous",
                "metric": "total_exposure_by_counterparty",
                "available_contexts": ["risk", "finance", "ops"],
                "hint": "Set X-USF-Context header to one of the available_contexts"
            }]
        }
    )


class ABACDeniedResponse(BaseModel):
    """Returned when ABAC policy denies access."""
    error: str = "access_denied"
    required_role: str | None = None
    required_context: str | None = None
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "error": "access_denied",
                "required_role": "analyst",
                "required_context": "risk",
                "message": "Insufficient clearance for risk context"
            }]
        }
    )


class ValidationErrorResponse(BaseModel):
    """Returned for request validation failures."""
    error: str = "validation_error"
    details: list[dict]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "error": "validation_error",
                "details": [{"loc": ["body", "metric"], "msg": "field required", "type": "value_error.missing"}]
            }]
        }
    )


class NotFoundResponse(BaseModel):
    """Resource not found."""
    error: str = "not_found"
    message: str
    resource_type: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "error": "not_found",
                "message": "Entity not found: https://usf.makf.tech/entity/123",
                "resource_type": "entity"
            }]
        }
    )


class BadGatewayResponse(BaseModel):
    """Upstream service error."""
    error: str = "bad_gateway"
    message: str
    upstream_service: str | None = None
