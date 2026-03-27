"""Tests for NamedGraphManager (uses pyoxigraph as in-process SPARQL)."""
import pytest
from usf_rdf.triples import Triple, batch_to_sparql_update, triples_to_turtle
from rdflib import URIRef, Literal


def test_triple_to_tuple():
    t = Triple(
        subject=URIRef("https://example.org/s"),
        predicate=URIRef("https://example.org/p"),
        obj=Literal("hello"),
    )
    s, p, o = t.to_tuple()
    assert str(s) == "https://example.org/s"


def test_batch_to_sparql_update():
    triples = [
        Triple(
            subject=URIRef("https://example.org/s"),
            predicate=URIRef("https://example.org/p"),
            obj=Literal("hello"),
        )
    ]
    sparql = batch_to_sparql_update(triples, "https://example.org/graph1")
    assert "INSERT DATA" in sparql
    assert "GRAPH <https://example.org/graph1>" in sparql


def test_triples_to_turtle():
    triples = [
        Triple(
            subject=URIRef("https://example.org/s"),
            predicate=URIRef("https://example.org/p"),
            obj=Literal("hello"),
        )
    ]
    ttl = triples_to_turtle(triples)
    assert "hello" in ttl
