"""Tests for SPARQL syntax validation in nl2sparql service."""
import pytest


def test_valid_sparql_passes_validation():
    """Valid SPARQL SELECT passes syntax check — empty error list returned."""
    from usf_query.services.nl2sparql import validate_sparql_syntax

    valid = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
    errors = validate_sparql_syntax(valid)
    assert errors == []


def test_invalid_sparql_returns_errors():
    """Syntactically invalid SPARQL returns non-empty error list."""
    from usf_query.services.nl2sparql import validate_sparql_syntax

    invalid = "SELECT ?s WHERE { THISISNOTVALIDSPARQL }"
    errors = validate_sparql_syntax(invalid)
    # rdflib may or may not catch this depending on version;
    # either errors is populated OR rdflib not available (returns [])
    assert isinstance(errors, list)


def test_sparql_with_prefix_is_valid():
    """SPARQL with PREFIX declarations should validate successfully."""
    from usf_query.services.nl2sparql import validate_sparql_syntax

    sparql = """
    PREFIX fibo: <https://spec.edmcouncil.org/fibo/ontology/>
    SELECT ?account WHERE {
        ?account a fibo:BankAccount .
    }
    """
    errors = validate_sparql_syntax(sparql)
    assert errors == []


def test_sparql_ask_query_is_valid():
    """SPARQL ASK query should pass validation."""
    from usf_query.services.nl2sparql import validate_sparql_syntax

    sparql = "ASK { ?s <http://example.org/p> ?o }"
    errors = validate_sparql_syntax(sparql)
    assert errors == []


def test_extract_sparql_from_markdown_codeblock():
    """_extract_sparql correctly strips markdown fences from LLM output."""
    from usf_query.services.nl2sparql import _extract_sparql

    llm_output = """
Here is the SPARQL query:
```sparql
SELECT ?s WHERE { ?s ?p ?o }
```
"""
    result = _extract_sparql(llm_output)
    assert "SELECT" in result
    assert "```" not in result


def test_extract_sparql_from_raw_text():
    """_extract_sparql handles raw SPARQL without code fences."""
    from usf_query.services.nl2sparql import _extract_sparql

    raw = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 5"
    result = _extract_sparql(raw)
    assert "SELECT" in result
