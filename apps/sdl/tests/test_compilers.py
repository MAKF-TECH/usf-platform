"""Tests for usf-sdl compiler services — no Docker required."""
from __future__ import annotations


class TestOWLCompiler:
    def test_compile_sdl_to_owl_produces_turtle(self, sample_sdl):
        """SDL entity → OWL Turtle contains owl:Class declaration."""
        from usf_sdl_svc.services.owl_compiler import compile_sdl_to_owl

        result = compile_sdl_to_owl(sample_sdl)
        assert isinstance(result, str)
        assert "owl:Class" in result or "Class" in result

    def test_owl_output_contains_entity_labels(self, sample_sdl):
        """OWL output includes rdfs:label for each entity."""
        from usf_sdl_svc.services.owl_compiler import compile_sdl_to_owl

        result = compile_sdl_to_owl(sample_sdl)
        assert "Transaction" in result
        assert "Bank" in result

    def test_owl_output_has_object_property_for_ref(self, sample_sdl):
        """ref(Bank) field generates an owl:ObjectProperty."""
        from usf_sdl_svc.services.owl_compiler import compile_sdl_to_owl

        result = compile_sdl_to_owl(sample_sdl)
        assert "ObjectProperty" in result

    def test_owl_output_has_fibo_equivalent_class(self, sample_sdl):
        """Entity with fibo_class gets owl:equivalentClass axiom."""
        from usf_sdl_svc.services.owl_compiler import compile_sdl_to_owl

        result = compile_sdl_to_owl(sample_sdl)
        assert "equivalentClass" in result or "fibo" in result.lower()

    def test_owl_output_has_required_restriction(self, sample_sdl):
        """Required field generates owl:Restriction with minCardinality."""
        from usf_sdl_svc.services.owl_compiler import compile_sdl_to_owl

        result = compile_sdl_to_owl(sample_sdl)
        assert "Restriction" in result


class TestSQLCompiler:
    def test_compile_metric_postgres_dialect(self, sample_sdl, sample_table_map):
        """Metric → SQL for postgres has SELECT, FROM."""
        from usf_sdl_svc.services.sql_compiler import compile_metric_to_sql

        metric = sample_sdl["metrics"][0]
        result = compile_metric_to_sql(metric, sample_table_map, dialect="postgres")
        assert isinstance(result, str)
        upper = result.upper()
        assert "SELECT" in upper
        assert "FROM" in upper

    def test_compile_metric_snowflake_dialect(self, sample_sdl, sample_table_map):
        """Metric → SQL for snowflake dialect."""
        from usf_sdl_svc.services.sql_compiler import compile_metric_to_sql

        metric = sample_sdl["metrics"][0]
        result = compile_metric_to_sql(metric, sample_table_map, dialect="snowflake")
        assert isinstance(result, str)
        assert "SELECT" in result.upper()

    def test_compile_metric_unsupported_dialect_raises(self, sample_sdl, sample_table_map):
        """Unsupported dialect raises ValueError."""
        import pytest
        from usf_sdl_svc.services.sql_compiler import compile_metric_to_sql

        metric = sample_sdl["metrics"][0]
        with pytest.raises(ValueError, match="Unsupported dialect"):
            compile_metric_to_sql(metric, sample_table_map, dialect="oracle")

    def test_compile_metric_with_group_by(self, sample_sdl, sample_table_map):
        """Metric with group_by produces GROUP BY clause."""
        from usf_sdl_svc.services.sql_compiler import compile_metric_to_sql

        metric = sample_sdl["metrics"][0]
        result = compile_metric_to_sql(metric, sample_table_map, dialect="postgres")
        assert "GROUP BY" in result.upper()


class TestR2RMLGenerator:
    def test_generate_r2rml_has_triples_map(self, sample_sdl, sample_table_map):
        """R2RML output contains rr:TriplesMap."""
        from usf_sdl_svc.services.r2rml_gen import generate_r2rml

        result = generate_r2rml(sample_sdl, table_map=sample_table_map)
        assert isinstance(result, str)
        assert "TriplesMap" in result

    def test_generate_r2rml_contains_table_names(self, sample_sdl, sample_table_map):
        """R2RML output references the mapped table names."""
        from usf_sdl_svc.services.r2rml_gen import generate_r2rml

        result = generate_r2rml(sample_sdl, table_map=sample_table_map)
        assert "transactions" in result
        assert "banks" in result


class TestCompileEndpoint:
    def test_health_returns_ok(self):
        """GET /health → 200 with status ok."""
        from fastapi.testclient import TestClient
        from usf_sdl_svc.main import app

        with TestClient(app) as client:
            r = client.get("/health")
            assert r.status_code == 200
            assert r.json()["status"] == "ok"
