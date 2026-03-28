"""Tests for SHACLValidator — FIBO Account shapes with real pyshacl."""
import pytest
from rdflib import Graph

from usf_rdf.shacl import SHACLValidator, SHACLViolation

# ── FIBO-inspired SHACL shape for BankAccount ────────────────────────────────
FIBO_ACCOUNT_SHAPE = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix fibo: <https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

fibo:BankAccountShape a sh:NodeShape ;
    sh:targetClass fibo:BankAccount ;
    sh:property [
        sh:path fibo:hasIdentifier ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:message "fibo:hasIdentifier is required and must be a string" ;
    ] ;
    sh:property [
        sh:path fibo:hasBalance ;
        sh:datatype xsd:decimal ;
        sh:maxCount 1 ;
    ] .
"""

VALID_FIBO_ACCOUNT = """
@prefix fibo: <https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<usf://acme/entity/BankAccount/acc001>
    a fibo:BankAccount ;
    fibo:hasIdentifier "ACC-001"^^xsd:string ;
    fibo:hasBalance "50000.00"^^xsd:decimal .
"""

INVALID_FIBO_ACCOUNT_MISSING_IDENTIFIER = """
@prefix fibo: <https://spec.edmcouncil.org/fibo/ontology/FBC/ProductsAndServices/FinancialProductsAndServices/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<usf://acme/entity/BankAccount/acc002>
    a fibo:BankAccount ;
    fibo:hasBalance "25000.00"^^xsd:decimal .
"""


def test_valid_fibo_account_triple_passes():
    """Load FIBO Account shape, validate a conforming Account triple — conforms=True."""
    validator = SHACLValidator()
    validator.load_shapes_turtle(FIBO_ACCOUNT_SHAPE)

    data_graph = Graph()
    data_graph.parse(data=VALID_FIBO_ACCOUNT, format="turtle")

    conforms, violations = validator.validate(data_graph)

    assert conforms is True, f"Expected conforms=True, got violations: {violations}"
    assert len(violations) == 0


def test_missing_required_property_fails():
    """Validate Account triple missing fibo:hasIdentifier — conforms=False, violation reported."""
    validator = SHACLValidator()
    validator.load_shapes_turtle(FIBO_ACCOUNT_SHAPE)

    data_graph = Graph()
    data_graph.parse(data=INVALID_FIBO_ACCOUNT_MISSING_IDENTIFIER, format="turtle")

    conforms, violations = validator.validate(data_graph)

    assert conforms is False, "Expected conforms=False for missing required fibo:hasIdentifier"
    assert len(violations) > 0
    # At least one violation should reference the account entity
    focus_nodes = [v.focus_node for v in violations]
    assert any("acc002" in fn for fn in focus_nodes)


def test_shacl_violation_has_severity_field():
    """SHACLViolation objects must have non-empty severity field."""
    validator = SHACLValidator()
    validator.load_shapes_turtle(FIBO_ACCOUNT_SHAPE)

    data_graph = Graph()
    data_graph.parse(data=INVALID_FIBO_ACCOUNT_MISSING_IDENTIFIER, format="turtle")

    _, violations = validator.validate(data_graph)
    for v in violations:
        assert v.severity in ("Violation", "Warning", "Info"), f"Unexpected severity: {v.severity}"


def test_validate_raises_without_shapes():
    """validate() raises ValueError when no shapes are loaded."""
    validator = SHACLValidator()  # no shapes loaded
    data_graph = Graph()
    data_graph.parse(data=VALID_FIBO_ACCOUNT, format="turtle")

    with pytest.raises(ValueError, match="No SHACL shapes loaded"):
        validator.validate(data_graph)


def test_load_shapes_merges_multiple_graphs():
    """Loading shapes twice should merge both shape graphs."""
    extra_shape = """
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix ex: <https://example.org/> .
    ex:OtherShape a sh:NodeShape ; sh:targetClass ex:Other .
    """
    validator = SHACLValidator()
    validator.load_shapes_turtle(FIBO_ACCOUNT_SHAPE)
    validator.load_shapes_turtle(extra_shape)

    # Should not raise — both shapes are in the combined graph
    data_graph = Graph()
    data_graph.parse(data=VALID_FIBO_ACCOUNT, format="turtle")
    conforms, _ = validator.validate(data_graph)
    assert conforms is True
