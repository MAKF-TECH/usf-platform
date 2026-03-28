from __future__ import annotations

import re
import textwrap
from typing import Any

from loguru import logger
from openai import AsyncOpenAI

from usf_query.config import settings
from usf_query.models import QueryResult, QueryType, SemanticQuery
from usf_query.services.query_router import route_query

try:
    import rdflib
    from rdflib import Graph
    from rdflib.exceptions import Error as RDFLibError
    HAS_RDFLIB = True
except ImportError:
    HAS_RDFLIB = False


class NL2SPARQLError(Exception):
    def __init__(self, question: str, last_error: str) -> None:
        super().__init__(f"Failed to generate valid SPARQL for: {question}. Last: {last_error}")
        self.question = question
        self.last_error = last_error


def _extract_sparql(text: str) -> str:
    """Extract SPARQL from LLM response (markdown code block or raw)."""
    # Try ```sparql ... ``` block
    match = re.search(r"```(?:sparql)?\s*(SELECT|CONSTRUCT|ASK|DESCRIBE.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Try raw SPARQL (starts with SELECT/CONSTRUCT/ASK/DESCRIBE/PREFIX)
    match = re.search(
        r"((?:PREFIX\s+\S+:\s*<[^>]+>\s*)*(?:SELECT|CONSTRUCT|ASK|DESCRIBE)\b.*)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return text.strip()


def _validate_sparql_syntax(sparql: str, ontology_ttl: str | None = None) -> tuple[bool, str]:
    """
    Validate SPARQL syntax and optionally check prefixes against ontology.
    Returns (is_valid, error_message).
    """
    if not HAS_RDFLIB:
        # Can't validate without rdflib — assume valid, rely on backend
        return True, ""

    try:
        g = Graph()
        g.parse(data=sparql, format="n3") if ontology_ttl else None
        # Use rdflib's SPARQL parser
        from rdflib.plugins.sparql import prepareQuery
        prepareQuery(sparql)
        return True, ""
    except Exception as exc:
        return False, str(exc)


_SYSTEM_PROMPT = textwrap.dedent("""
    You are a SPARQL expert. Generate valid SPARQL 1.1 queries based on the user's natural language question
    and the provided ontology schema.

    Rules:
    1. Use only classes and properties defined in the ontology schema
    2. Always declare PREFIX statements for all namespaces used
    3. Return ONLY the SPARQL query, no explanation
    4. Use LIMIT 1000 unless the user asks for everything
    5. Prefer SELECT queries; use CONSTRUCT only when asked for graph output
""").strip()


def _build_prompt(question: str, ontology_context: str, error: str | None = None) -> str:
    parts = [f"Ontology schema:\n{ontology_context}", f"\nQuestion: {question}"]
    if error:
        parts.append(f"\nThe previous SPARQL was invalid. Error: {error}\nPlease fix it.")
    return "\n".join(parts)


async def nl_to_sparql(
    question: str,
    ontology_context: str,
    max_iterations: int | None = None,
) -> str:
    """
    NL → SPARQL pipeline:
    1. LLM drafts SPARQL from question + ontology schema
    2. Validate syntax with rdflib
    3. If invalid, feed error back to LLM (up to max_iterations)
    4. Return validated SPARQL or raise NL2SPARQLError
    """
    if max_iterations is None:
        max_iterations = settings.nl2sparql_max_iterations

    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    last_error = ""
    for iteration in range(1, max_iterations + 1):
        user_prompt = _build_prompt(question, ontology_context, error=last_error if iteration > 1 else None)

        logger.info("NL2SPARQL iteration", iteration=iteration, question=question[:80])

        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=1024,
        )

        raw = response.choices[0].message.content or ""
        sparql = _extract_sparql(raw)

        is_valid, error_msg = _validate_sparql_syntax(sparql)
        if is_valid:
            logger.info("NL2SPARQL success", iteration=iteration, question=question[:80])
            return sparql

        last_error = error_msg
        logger.warning(
            "NL2SPARQL invalid SPARQL, retrying",
            iteration=iteration,
            error=error_msg[:200],
        )

    raise NL2SPARQLError(question=question, last_error=last_error)


def validate_sparql_syntax(sparql: str) -> list[str]:
    """
    Public API: validate SPARQL syntax using rdflib.
    Returns a list of error strings. Empty list = valid.
    """
    if not HAS_RDFLIB:
        return []
    try:
        from rdflib.plugins.sparql import prepareQuery
        prepareQuery(sparql)
        return []
    except Exception as exc:
        return [str(exc)]


async def execute_nl_query(question: str, ontology_context: str, context: str | None, tenant_id: str | None) -> QueryResult:
    """Full NL query pipeline: NL → SPARQL → execute → return QueryResult."""
    sparql = await nl_to_sparql(question, ontology_context)
    semantic_query = SemanticQuery(
        query=sparql,
        query_type=QueryType.SPARQL,
        context=context,
        tenant_id=tenant_id,
    )
    result = await route_query(semantic_query)
    result.sparql_generated = sparql
    return result
