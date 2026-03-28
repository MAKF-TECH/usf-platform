"""Tests for usf-ingest pipelines — no Docker required."""
from __future__ import annotations
from unittest.mock import patch


class TestR2RMLGenerator:
    def test_generate_r2rml_returns_turtle(self, sample_schema_info):
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

    def test_generate_r2rml_contains_columns(self, sample_schema_info):
        with patch(
            "usf_ingest.pipelines.structured.schema_introspect.infer_column_semantics",
            return_value=None,
        ):
            from usf_ingest.pipelines.structured.r2rml_generator import generate_r2rml

            result = generate_r2rml(
                table_name="tx",
                schema_info=sample_schema_info,
                db_connection="jdbc:postgresql://localhost/test",
            )
            for col in sample_schema_info["columns"]:
                assert col["name"] in result

    def test_sql_type_to_xsd(self):
        from usf_ingest.pipelines.structured.r2rml_generator import _sql_type_to_xsd
        from rdflib.namespace import XSD

        assert _sql_type_to_xsd("integer") == XSD.integer
        assert _sql_type_to_xsd("decimal") == XSD.decimal
        assert _sql_type_to_xsd("boolean") == XSD.boolean
        assert _sql_type_to_xsd("timestamp") == XSD.dateTime
        assert _sql_type_to_xsd("varchar") is None


class TestConfidenceFilter:
    def test_passes_grounded_high_confidence(self, mock_extraction_result):
        from usf_ingest.pipelines.unstructured.confidence_filter import ConfidenceFilter

        ext = mock_extraction_result(confidence_score=0.9, char_interval=(0, 14))
        passed, quarantined = ConfidenceFilter(0.5).filter([ext])
        assert len(passed) == 1 and len(quarantined) == 0

    def test_quarantines_ungrounded(self, mock_extraction_result):
        from usf_ingest.pipelines.unstructured.confidence_filter import ConfidenceFilter

        ext = mock_extraction_result(confidence_score=0.9, char_interval=None)
        passed, quarantined = ConfidenceFilter(0.5).filter([ext])
        assert len(passed) == 0 and "ungrounded" in quarantined[0].reason

    def test_quarantines_low_confidence(self, mock_extraction_result):
        from usf_ingest.pipelines.unstructured.confidence_filter import ConfidenceFilter

        ext = mock_extraction_result(confidence_score=0.3, char_interval=(0, 10))
        passed, quarantined = ConfidenceFilter(0.5).filter([ext])
        assert len(passed) == 0 and "low confidence" in quarantined[0].reason

    def test_quarantines_invalid_interval(self, mock_extraction_result):
        from usf_ingest.pipelines.unstructured.confidence_filter import ConfidenceFilter

        ext = mock_extraction_result(confidence_score=0.9, char_interval=(10, 5))
        passed, quarantined = ConfidenceFilter(0.5).filter([ext])
        assert len(passed) == 0 and "invalid" in quarantined[0].reason

    def test_invalid_threshold_raises(self):
        from usf_ingest.pipelines.unstructured.confidence_filter import ConfidenceFilter
        import pytest

        with pytest.raises(ValueError):
            ConfidenceFilter(1.5)

    def test_mixed_extractions(self, mock_extraction_result):
        from usf_ingest.pipelines.unstructured.confidence_filter import ConfidenceFilter

        exts = [
            mock_extraction_result(confidence_score=0.9, char_interval=(0, 14)),
            mock_extraction_result(confidence_score=0.8, char_interval=None),
            mock_extraction_result(confidence_score=0.3, char_interval=(20, 30)),
            mock_extraction_result(confidence_score=0.6, char_interval=(40, 50)),
        ]
        passed, quarantined = ConfidenceFilter(0.5).filter(exts, job_id="j1")
        assert len(passed) == 2 and len(quarantined) == 2
