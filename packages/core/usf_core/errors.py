"""
USF typed error hierarchy.

All USF services raise typed errors. FastAPI exception handlers
convert these to the standard error envelope at the HTTP boundary.

Error codes match the `error.code` field in the API response envelope.

Design:
- All errors are USFError subclasses
- Each error carries a machine-readable code, HTTP status hint, and context dict
- No naked Exception raises in business logic — always use typed errors
"""

from __future__ import annotations

from typing import Any


class USFError(Exception):
    """
    Base class for all USF errors.

    Attributes:
        message: Human-readable description.
        code: Machine-readable error code (matches API error envelope).
        http_status: Suggested HTTP status code.
        detail: Additional structured context.
    """

    code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(
        self,
        message: str,
        detail: dict[str, Any] | None = None,
        *,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}
        if code:
            self.code = code

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the API error envelope format."""
        return {
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
        }

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"


# ─────────────────────────────────────────────────────────────────
# Authentication & Authorization errors
# ─────────────────────────────────────────────────────────────────


class AuthenticationError(USFError):
    """JWT is missing, malformed, expired, or signature invalid. → HTTP 401."""

    code = "AUTHENTICATION_REQUIRED"
    http_status = 401


class AccessDeniedError(USFError):
    """
    OPA policy returned deny for this request. → HTTP 403.

    detail should include: policy_version, abac_decision, filter_applied.
    """

    code = "ACCESS_DENIED"
    http_status = 403


# ─────────────────────────────────────────────────────────────────
# Validation errors
# ─────────────────────────────────────────────────────────────────


class ValidationError(USFError):
    """
    Input validation failed (structural or type error). → HTTP 400.

    detail should include: field, value, constraint.
    """

    code = "VALIDATION_ERROR"
    http_status = 400


class SemanticValidationError(USFError):
    """
    Ontology-level validation failed (class unknown, property mismatch). → HTTP 422.

    detail should include: sparql_fragment, ontology_class, suggestion.
    """

    code = "SEMANTIC_VALIDATION_ERROR"
    http_status = 422


# ─────────────────────────────────────────────────────────────────
# Context / SDL errors
# ─────────────────────────────────────────────────────────────────


class ContextError(USFError):
    """Base class for context-related errors."""

    code = "CONTEXT_ERROR"
    http_status = 400


class ContextAmbiguousError(ContextError):
    """
    A term or metric is defined in multiple contexts and no context was specified.
    Returns HTTP 409 (Conflict) per the API contract.

    detail should include: term, contexts (list of {name, definition}).
    """

    code = "CONTEXT_AMBIGUOUS"
    http_status = 409


class ContextNotFoundError(ContextError):
    """
    The specified context does not exist for this tenant. → HTTP 404.
    """

    code = "CONTEXT_NOT_FOUND"
    http_status = 404


class SDLValidationError(USFError):
    """
    SDL YAML failed Pydantic or semantic validation. → HTTP 400.

    detail should include: errors (list of {path, message, code}).
    """

    code = "SDL_VALIDATION_ERROR"
    http_status = 400


class SDLCompilationError(USFError):
    """
    SDL compilation to OWL/SQL/R2RML failed. → HTTP 500 (internal compiler error).
    """

    code = "SDL_COMPILATION_ERROR"
    http_status = 500


# ─────────────────────────────────────────────────────────────────
# Query errors
# ─────────────────────────────────────────────────────────────────


class QueryError(USFError):
    """Base class for query execution errors."""

    code = "QUERY_ERROR"
    http_status = 400


class NL2SPARQLError(QueryError):
    """
    Natural language → SPARQL failed after max iterations. → HTTP 422.

    detail should include: question, last_sparql_attempt, validation_errors, iterations.
    """

    code = "NL2SPARQL_FAILED"
    http_status = 422


class QueryTimeoutError(QueryError):
    """
    Query execution exceeded the timeout. → HTTP 504.
    """

    code = "QUERY_TIMEOUT"
    http_status = 504


class MetricNotFoundError(QueryError):
    """
    Requested SDL metric does not exist or is not accessible. → HTTP 404.
    """

    code = "METRIC_NOT_FOUND"
    http_status = 404


# ─────────────────────────────────────────────────────────────────
# Ingestion errors
# ─────────────────────────────────────────────────────────────────


class IngestionError(USFError):
    """Base class for ingestion errors."""

    code = "INGESTION_ERROR"
    http_status = 500


class SourceConnectionError(IngestionError):
    """
    Cannot connect to the registered data source. → HTTP 502 (bad gateway).
    """

    code = "SOURCE_CONNECTION_ERROR"
    http_status = 502


class ExtractionError(IngestionError):
    """
    LLM or parser failed to extract entities from a document. → HTTP 500.
    """

    code = "EXTRACTION_ERROR"
    http_status = 500


# ─────────────────────────────────────────────────────────────────
# KG errors
# ─────────────────────────────────────────────────────────────────


class KGError(USFError):
    """Base class for knowledge graph errors."""

    code = "KG_ERROR"
    http_status = 500


class NamedGraphNotFoundError(KGError):
    """
    The requested named graph URI does not exist. → HTTP 404.
    """

    code = "NAMED_GRAPH_NOT_FOUND"
    http_status = 404


class EntityNotFoundError(KGError):
    """
    The requested entity IRI does not exist in the KG. → HTTP 404.
    """

    code = "ENTITY_NOT_FOUND"
    http_status = 404


class SHACLViolationError(KGError):
    """
    Triple insertion failed SHACL validation and quarantine_on_violation=False. → HTTP 422.

    detail should include: violations (list of {focus_node, shape, message}).
    """

    code = "SHACL_VIOLATION"
    http_status = 422


# ─────────────────────────────────────────────────────────────────
# Dependency errors
# ─────────────────────────────────────────────────────────────────


class DependencyUnavailableError(USFError):
    """
    A required sidecar or service is unreachable (QLever, OPA, etc.). → HTTP 503.

    detail should include: dependency, url.
    """

    code = "DEPENDENCY_UNAVAILABLE"
    http_status = 503
