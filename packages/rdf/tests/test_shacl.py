"""Tests for SHACLValidator."""
import pytest
from rdflib import Graph
from usf_rdf.shacl import SHACLValidator

SHAPES_TTL = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <https://example.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:PersonShape a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property [
        sh:path ex:name ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
    ] .
"""

DATA_VALID_TTL = """
@prefix ex: <https://example.org/> .
ex:Alice a ex:Person ; ex:name "Alice" .
"""

DATA_INVALID_TTL = """
@prefix ex: <https://example.org/> .
ex:Bob a ex:Person .
"""


def test_valid_data():
    v = SHACLValidator()
    v.load_shapes_turtle(SHAPES_TTL)
    g = Graph()
    g.parse(data=DATA_VALID_TTL, format="turtle")
    conforms, violations = v.validate(g)
    assert conforms is True
    assert len(violations) == 0


def test_invalid_data():
    v = SHACLValidator()
    v.load_shapes_turtle(SHAPES_TTL)
    g = Graph()
    g.parse(data=DATA_INVALID_TTL, format="turtle")
    conforms, violations = v.validate(g)
    assert conforms is False
    assert len(violations) > 0
    assert "Bob" in violations[0].focus_node
