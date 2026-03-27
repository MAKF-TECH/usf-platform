from __future__ import annotations


class USFError(Exception):
    """Base USF error."""

    def __init__(self, message: str, code: str = "usf_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ContextAmbiguousError(USFError):
    """Raised when context is required but multiple contexts match."""

    def __init__(self, metric: str | None, available_contexts: list[str]) -> None:
        super().__init__(
            message=f"Context ambiguous for metric '{metric}'. Set X-USF-Context header.",
            code="context_ambiguous",
        )
        self.metric = metric
        self.available_contexts = available_contexts


class NL2SPARQLError(USFError):
    """Raised when NL→SPARQL conversion fails after max iterations."""

    def __init__(self, question: str, last_error: str) -> None:
        super().__init__(
            message=f"Failed to generate valid SPARQL for: {question}. Last error: {last_error}",
            code="nl2sparql_failed",
        )


class ABACDeniedError(USFError):
    """Raised when ABAC policy denies the request."""

    def __init__(self, reason: str = "Access denied by policy") -> None:
        super().__init__(message=reason, code="abac_denied")
