"""Tests for usf-sdl compiler services."""
from __future__ import annotations
import pytest


class TestOWLCompiler:
    def test_produces_turtle(self, sample_sdl):
        from usf_sdl_svc.services.owl_compiler import compile_sdl_to_owl

        result = compile_sdl_to_owl(sample_sdl)
        assert isinstance(result, str)
        assert "Class" in result

    def test_contains_entity_labels(self, sample_sdl):
        from usf_sdl_svc.services.owl_compiler import compile_sdl_to_owl

        result = compile_sdl_to_owl(sample_sdl)
        assert "Transaction" in result and "Bank" in result

    def test_has_object_property(self, sample_sdl):
        from usf_sdl_svc.services.owl_compiler import compile_sdl_to_owl

        result = compile_sdl_to_owl(sample_sdl)
        assert "ObjectProperty" in result

    def test_has_fibo_equivalent(self, sample_sdl):
        from usf_sdl_svc.services.owl_compiler import compile_sdl_to_owl

        result = compile_sdl_to_owl(sample_sdl)
        assert "equivalentClass" in result or "fibo" in result.lower()

    def test_has_restriction(self, sample_sdl):
        from usf_sdl_svc.services.owl_compiler import compile_sdl_to_owl

        result = compile_sdl_to_owl(sample_sdl)
        assert "Restriction" in result


class TestSQLCompiler:
    def test_postgres_dialect(self, sample_sdl, sample_table_map):
        from usf_sdl_svc.services.sql_compiler import compile_metric_to_sql

        result = compile_metric_to_sql(sample_sdl["metrics"][0], sample_table_map, dialect="postgres")
        assert "SELECT" in result.upper() and "FROM" in result.upper()

    def test_snowflake_dialect(self, sample_sdl, sample_table_map):
        from usf_sdl_svc.services.sql_compiler import compile_metric_to_sql

        result = compile_metric_to_sql(sample_sdl["metrics"][0], sample_table_map, dialect="snowflake")
        assert "SELECT" in result.upper()

    def test_unsupported_raises(self, sample_sdl, sample_table_map):
        from usf_sdl_svc.services.sql_compiler import compile_metric_to_sql

        with pytest.raises(ValueError, match="Unsupported dialect"):
            compile_metric_to_sql(sample_sdl["metrics"][0], sample_table_map, dialect="oracle")

    def test_group_by(self, sample_sdl, sample_table_map):
        from usf_sdl_svc.services.sql_compiler import compile_metric_to_sql

        result = compile_metric_to_sql(sample_sdl["metrics"][0], sample_table_map, dialect="postgres")
        assert "GROUP BY" in result.upper()


class TestR2RMLGen:
    def test_has_triples_map(self, sample_sdl, sample_table_map):
        from usf_sdl_svc.services.r2rml_gen import generate_r2rml

        result = generate_r2rml(sample_sdl, table_map=sample_table_map)
        assert "TriplesMap" in result

    def test_contains_tables(self, sample_sdl, sample_table_map):
        from usf_sdl_svc.services.r2rml_gen import generate_r2rml

        result = generate_r2rml(sample_sdl, table_map=sample_table_map)
        assert "transactions" in result and "banks" in result


class TestHealthEndpoint:
    def test_health_ok(self):
        from fastapi.testclient import TestClient
        from usf_sdl_svc.main import app

        with TestClient(app) as client:
            r = client.get("/health")
            assert r.status_code == 200
            assert r.json()["status"] == "ok"
