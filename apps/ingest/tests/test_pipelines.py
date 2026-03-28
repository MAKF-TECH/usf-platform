"""Tests for usf-ingest pipelines — no Docker required."""
from __future__ import annotations

from unittest.mock import patch, MagicMock


class TestR2RMLGenerator:
    """Tests for apps/ingest/usf_ingest/pipelines/structured/r2rml_generator.py"""

    def test_generate_r2rml_returns_turtle_string(self, sample_schema_info):
        """generate_r2rml produces a non-empty Turtle string containing TriplesMap."""
        with patch(
            "usf_ingest.pipelines.structured.schema_introspect.infer_column_semantics",
            return_value="financial_institution",
        ):
            from usf_ingest.pipelines.structured.r2rml_generator import generate_r2rml

            result = generate_r2rml(
                table_name="transactions",
                schema_info=sample_schema_info,
                db_connection="jdbc:postgresql://localhost/test",
            )
            assert isinstance(result, str)
            assert "TriplesMap" in result
            assert "transactions" in result

    def test_generate_r2rml_contains_column_references(self, sample_schema_info):
        """Each column from schema_info appears in the R2RML output."""
        with patch(
            "usf_ingest.pipelines.structured.schema_introspect.infer_column_semantics",
            return_value=None,
        ):
            from usf_ingest.pipelines.structured.r2rml_generator import generate_r2rml

            result = generate_r2rml(
                table_name="transactions",
                schema_info=sample_schema_info,
                db_connection="jdbc:postgresql://localhost/test",
            )
            for col in sample_schema_info["columns"]:
                assert col["name"] in result

    def test_generate_r2rml_uses_fibo_hints(self, sample_schema_info):
        """When fibo_hints provided, those URIs appear in the output."""
        fibo_uri = "https://spec.edmcouncil.org/fibo/ontology/FBC/Test/CustomClass"
        with patch(
            "usf_ingest.pipelines.structured.schema_introspect.infer_column_semantics",
            return_value=None,
        ):
            from usf_ingest.pipelines.structured.r2rml_generator import generate_r2rml

            result = generate_r2rml(
                table_name="accounts",
                schema_info=sample_schema_info,
                db_connection="jdbc:postgresql://localhost/test",
                fibo_hints={"bank_name": fibo_uri},
            )
            assert fibo_uri in result

    def test_sql_type_to_xsd_mapping(self):
        """Internal _sql_type_to_xsd correctly maps SQL types to XSD."""
        from usf_ingest.pipelines.structured.r2rml_generator import _sql_type_to_xsd
        from rdflib.namespace import XSD

        assert _sql_type_to_xsd("integer") == XSD.integer
        assert _sql_type_to_xsd("decimal") == XSD.decimal
        assert _sql_type_to_xsd("boolean") == XSD.boolean
        assert _sql_type_to_xsd("timestamp") == XSD.dateTime
        assert _sql_type_to_xsd("date") == XSD.date
        assert _sql_type_to_xsd("varchar") is None


class TestConfidenceFilter:
    """Tests for apps/ingest/usf_ingest/pipelines/unstructured/confidence_filter.py"""

    def test_filter_passes_grounded_high_confidence(self, mock_extraction_result):
        """Grounded extraction with high confidence passes the filter."""
        from usf_ingest.pipelines.unstructured.confidence_filter import ConfidenceFilter

        ext = mock_extraction_result(confidence_score=0.9, char_interval=(0, 14))
        flt = ConfidenceFilter(confidence_threshold=0.5)
        passed, quarantined = flt.filter([ext])
        assert len(passed) == 1
        assert len(quarantined) == 0

    def test_filter_quarantines_ungrounded(self, mock_extraction_result):
        """Extraction with char_interval=None is quarantined as ungrounded."""
        from usf_ingest.pipelines.unstructured.confidence_filter import ConfidenceFilter

        ext = mock_extraction_result(confidence_score=0.9, char_interval=None)
        flt = ConfidenceFilter(confidence_threshold=0.5)
        passed, quarantined = flt.filter([ext])
        assert len(passed) == 0
        assert len(quarantined) == 1
        assert "ungrounded" in quarantined[0].reason

    def test_filter_quarantines_low_confidence(self, mock_extraction_result):
        """Extraction below confidence threshold is quarantined."""
        from usf_ingest.pipelines.unstructured.confidence_filter import ConfidenceFilter

        ext = mock_extraction_result(confidence_score=0.3, char_interval=(0, 10))
        flt = ConfidenceFilter(confidence_threshold=0.5)
        passed, quarantined = flt.filter([ext])
        assert len(passed) == 0
        assert len(quarantined) == 1
        assert "low confidence" in quarantined[0].reason

    def test_filter_quarantines_invalid_interval(self, mock_extraction_result):
        """Extraction with negative or zero-length char_interval is quarantined."""
        from usf_ingest.pipelines.unstructured.confidence_filter import ConfidenceFilter

        ext = mock_extraction_result(confidence_score=0.9, char_interval=(10, 5))
        flt = ConfidenceFilter(confidence_threshold=0.5)
        passed, quarantined = flt.filter([ext])
        assert len(passed) == 0
        assert len(quarantined) == 1
        assert "invalid char_interval" in quarantined[0].reason

    def test_filter_invalid_threshold_raises(self):
        """ConfidenceFilter rejects threshold outside [0, 1]."""
        from usf_ingest.pipelines.unstructured.confidence_filter import ConfidenceFilter
        import pytest

        with pytest.raises(ValueError, match="confidence_threshold"):
            ConfidenceFilter(confidence_threshold=1.5)

    def test_filter_mixed_extractions(self, mock_extraction_result):
        """Mixed batch: only grounded, high-confidence extractions pass."""
        from usf_ingest.pipelines.unstructured.confidence_filter import ConfidenceFilter

        exts = [
            mock_extraction_result(confidence_score=0.9, char_interval=(0, 14)),
            mock_extraction_result(confidence_score=0.8, char_interval=None),
            mock_extraction_result(confidence_score=0.3, char_interval=(20, 30)),
            mock_extraction_result(confidence_score=0.6, char_interval=(40, 50)),
        ]
        flt = ConfidenceFilter(confidence_threshold=0.5)
        passed, quarantined = flt.filter(exts, job_id="test-job")
        assert len(passed) == 2
        assert len(quarantined) == 2
