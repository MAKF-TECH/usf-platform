"""USF typed error hierarchy."""
from __future__ import annotations
from typing import Any


class USFError(Exception):
    code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(self, message: str, detail: dict[str, Any] | None = None, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}
        if code:
            self.code = code

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "detail": self.detail}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"


class AuthenticationError(USFError):
    code = "AUTHENTICATION_REQUIRED"
    http_status = 401

class AccessDeniedError(USFError):
    code = "ACCESS_DENIED"
    http_status = 403

class ValidationError(USFError):
    code = "VALIDATION_ERROR"
    http_status = 400

class SemanticValidationError(USFError):
    code = "SEMANTIC_VALIDATION_ERROR"
    http_status = 422

class ContextError(USFError):
    code = "CONTEXT_ERROR"
    http_status = 400

class ContextAmbiguousError(ContextError):
    """HTTP 409 — term defined in multiple contexts; must specify X-USF-Context."""
    code = "CONTEXT_AMBIGUOUS"
    http_status = 409

class ContextNotFoundError(ContextError):
    code = "CONTEXT_NOT_FOUND"
    http_status = 404

class SDLValidationError(USFError):
    code = "SDL_VALIDATION_ERROR"
    http_status = 400

class SDLCompilationError(USFError):
    code = "SDL_COMPILATION_ERROR"
    http_status = 500

class QueryError(USFError):
    code = "QUERY_ERROR"
    http_status = 400

class NL2SPARQLError(QueryError):
    code = "NL2SPARQL_FAILED"
    http_status = 422

class QueryTimeoutError(QueryError):
    code = "QUERY_TIMEOUT"
    http_status = 504

class MetricNotFoundError(QueryError):
    code = "METRIC_NOT_FOUND"
    http_status = 404

class IngestionError(USFError):
    code = "INGESTION_ERROR"
    http_status = 500

class SourceConnectionError(IngestionError):
    code = "SOURCE_CONNECTION_ERROR"
    http_status = 502

class ExtractionError(IngestionError):
    code = "EXTRACTION_ERROR"
    http_status = 500

class KGError(USFError):
    code = "KG_ERROR"
    http_status = 500

class NamedGraphNotFoundError(KGError):
    code = "NAMED_GRAPH_NOT_FOUND"
    http_status = 404

class EntityNotFoundError(KGError):
    code = "ENTITY_NOT_FOUND"
    http_status = 404

class SHACLViolationError(KGError):
    code = "SHACL_VIOLATION"
    http_status = 422

class DependencyUnavailableError(USFError):
    code = "DEPENDENCY_UNAVAILABLE"
    http_status = 503
