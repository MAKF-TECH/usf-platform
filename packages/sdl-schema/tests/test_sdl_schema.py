"""
Tests for the USF SDL Schema package.

Tests cover:
- Model parsing from YAML
- Field validation (slugs, CURIEs, types)
- Semantic validator cross-reference checks
- Context-ambiguous property detection
- FIBO banking example round-trips
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from usf_sdl.models import (
    SDLDocument,
    ContextDefinition,
    EntityDefinition,
    MetricDefinition,
    AccessPolicyDefinition,
    PropertyDefinition,
    DimensionDefinition,
    InlineAccessPolicy,
    EntityReference,
)
from usf_sdl.validator import validate, ValidationError

# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────

FIBO_BANKING_YAML = Path(__file__).parent.parent / "usf_sdl" / "examples" / "fibo_banking.yaml"


MINIMAL_VALID_YAML = textwrap.dedent("""\
    sdl_version: "1.0"
    tenant: test-tenant
    ontology_module: fibo

    contexts:
      - name: finance
        description: Finance context

    access_policies:
      - name: public_read
        description: Public read
        read: [role:viewer]
        pii: false
        clearance: internal

    entities:
      - name: Account
        ontology_class: fibo:Account
        description: A bank account
        sql_table: accounts
        properties:
          - name: account_id
            ontology_property: fibo:hasIdentifier
            sql_column: id
            type: string
        access_policy: public_read

    metrics:
      - name: total_balance
        ontology_class: fibo:FinancialExposure
        description: Total balance
        type: sum
        measure: balance
        measure_entity: Account
        dimensions:
          - name: account_type
            entity: Account
            property: account_id
            ontology_property: fibo:hasIdentifier
        time_grains: [day, month]
        time_column: "a.created_at"
        time_entity: Account
        access_policy: public_read
""")


# ─────────────────────────────────────────────────────────────────
# Model parsing tests
# ─────────────────────────────────────────────────────────────────

class TestSDLDocumentParsing:
    def test_parse_minimal_yaml(self) -> None:
        doc = SDLDocument.from_yaml(MINIMAL_VALID_YAML)
        assert doc.tenant == "test-tenant"
        assert doc.ontology_module == "fibo"
        assert len(doc.contexts) == 1
        assert len(doc.entities) == 1
        assert len(doc.metrics) == 1

    def test_parse_fibo_banking_example(self) -> None:
        if not FIBO_BANKING_YAML.exists():
            pytest.skip("FIBO banking example not found")
        doc = SDLDocument.from_yaml(FIBO_BANKING_YAML.read_text())
        assert doc.ontology_module == "fibo"
        assert len(doc.contexts) >= 2
        assert len(doc.entities) >= 3
        assert len(doc.metrics) >= 1

    def test_context_names_accessible(self) -> None:
        doc = SDLDocument.from_yaml(MINIMAL_VALID_YAML)
        assert "finance" in doc.context_names

    def test_entity_names_accessible(self) -> None:
        doc = SDLDocument.from_yaml(MINIMAL_VALID_YAML)
        assert "Account" in doc.entity_names

    def test_access_policy_names_accessible(self) -> None:
        doc = SDLDocument.from_yaml(MINIMAL_VALID_YAML)
        assert "public_read" in doc.access_policy_names


# ─────────────────────────────────────────────────────────────────
# Field validation tests
# ─────────────────────────────────────────────────────────────────

class TestFieldValidation:
    def test_entity_name_must_be_pascal_case(self) -> None:
        with pytest.raises(Exception, match="PascalCase"):
            EntityDefinition(
                name="bank_account",  # invalid: snake_case
                ontology_class="fibo:Account",
                description="test",
                sql_table="accounts",
                properties=[
                    PropertyDefinition(
                        name="id",
                        ontology_property="fibo:hasIdentifier",
                        sql_column="id",
                    )
                ],
            )

    def test_ontology_class_must_be_curie(self) -> None:
        with pytest.raises(Exception, match="CURIE"):
            EntityDefinition(
                name="Account",
                ontology_class="NotACurie",  # invalid
                description="test",
                sql_table="accounts",
                properties=[
                    PropertyDefinition(
                        name="id",
                        ontology_property="fibo:hasIdentifier",
                        sql_column="id",
                    )
                ],
            )

    def test_metric_type_must_be_valid(self) -> None:
        with pytest.raises(Exception):
            MetricDefinition(
                name="test_metric",
                ontology_class="fibo:Exposure",
                description="test",
                type="invalid_type",  # not in VALID_AGGREGATION_TYPES
                measure="amount",
                measure_entity="Account",
                dimensions=[
                    DimensionDefinition(
                        name="account_type",
                        entity="Account",
                        property="id",
                        ontology_property="fibo:hasIdentifier",
                    )
                ],
            )

    def test_context_name_must_be_slug(self) -> None:
        with pytest.raises(Exception):
            ContextDefinition(name="Finance Context", description="test")  # spaces not allowed

    def test_property_requires_sql_column_or_contexts(self) -> None:
        with pytest.raises(Exception, match="sql_column"):
            PropertyDefinition(
                name="balance",
                ontology_property="fibo:hasBalance",
                # neither sql_column nor contexts provided
            )

    def test_invalid_ontology_module_rejected(self) -> None:
        with pytest.raises(Exception):
            SDLDocument.from_yaml("sdl_version: '1.0'\nontology_module: invalid_module\n")

    def test_time_grain_requires_time_column(self) -> None:
        with pytest.raises(Exception, match="time_column"):
            MetricDefinition(
                name="test_metric",
                ontology_class="fibo:Exposure",
                description="test",
                type="sum",
                measure="amount",
                measure_entity="Account",
                dimensions=[
                    DimensionDefinition(
                        name="d",
                        entity="Account",
                        property="id",
                        ontology_property="fibo:hasIdentifier",
                    )
                ],
                time_grains=["day"],
                # no time_column — should fail
            )

    def test_duplicate_entity_names_rejected(self) -> None:
        yaml_with_duplicates = MINIMAL_VALID_YAML + textwrap.dedent("""\
              - name: Account
                ontology_class: fibo:CommercialBank
                description: Duplicate
                sql_table: banks
                properties:
                  - name: id
                    ontology_property: fibo:hasIdentifier
                    sql_column: id
        """)
        with pytest.raises(Exception, match="Duplicate"):
            SDLDocument.from_yaml(yaml_with_duplicates)


# ─────────────────────────────────────────────────────────────────
# Semantic validator tests
# ─────────────────────────────────────────────────────────────────

class TestValidator:
    def test_valid_document_has_no_errors(self) -> None:
        doc = SDLDocument.from_yaml(MINIMAL_VALID_YAML)
        errors = validate(doc)
        blocking = [e for e in errors if e.severity == "error"]
        assert blocking == [], f"Unexpected errors: {blocking}"

    def test_undeclared_context_in_entity_is_error(self) -> None:
        yaml_bad = textwrap.dedent("""\
            sdl_version: "1.0"
            entities:
              - name: Account
                ontology_class: fibo:Account
                description: test
                sql_table: accounts
                contexts:
                  ghost_context:
                    description: I do not exist
                properties:
                  - name: id
                    ontology_property: fibo:hasIdentifier
                    sql_column: id
        """)
        doc = SDLDocument.from_yaml(yaml_bad)
        errors = validate(doc)
        codes = [e.code for e in errors]
        assert "UNDECLARED_CONTEXT" in codes

    def test_undeclared_entity_in_metric_is_error(self) -> None:
        yaml_bad = textwrap.dedent("""\
            sdl_version: "1.0"
            metrics:
              - name: bad_metric
                ontology_class: fibo:Exposure
                description: test
                type: sum
                measure: amount
                measure_entity: GhostEntity
                dimensions:
                  - name: d
                    entity: GhostEntity
                    property: id
                    ontology_property: fibo:hasIdentifier
        """)
        doc = SDLDocument.from_yaml(yaml_bad)
        errors = validate(doc)
        codes = [e.code for e in errors]
        assert "UNDECLARED_ENTITY" in codes

    def test_undeclared_access_policy_ref_is_error(self) -> None:
        yaml_bad = textwrap.dedent("""\
            sdl_version: "1.0"
            entities:
              - name: Account
                ontology_class: fibo:Account
                description: test
                sql_table: accounts
                access_policy: nonexistent_policy
                properties:
                  - name: id
                    ontology_property: fibo:hasIdentifier
                    sql_column: id
        """)
        doc = SDLDocument.from_yaml(yaml_bad)
        errors = validate(doc)
        codes = [e.code for e in errors]
        assert "UNDECLARED_ACCESS_POLICY" in codes

    def test_context_ambiguous_property_is_warning(self) -> None:
        yaml_ambig = textwrap.dedent("""\
            sdl_version: "1.0"
            contexts:
              - name: risk
                description: Risk context
              - name: finance
                description: Finance context
            entities:
              - name: Account
                ontology_class: fibo:Account
                description: test
                sql_table: accounts
                properties:
                  - name: balance
                    ontology_property: fibo:hasBalance
                    type: decimal
                    contexts:
                      risk:
                        sql_column: eod_balance
                      finance:
                        sql_column: current_balance
        """)
        doc = SDLDocument.from_yaml(yaml_ambig)
        errors = validate(doc)
        warnings = [e for e in errors if e.code == "CONTEXT_AMBIGUOUS_PROPERTY"]
        assert len(warnings) == 1
        assert warnings[0].severity == "warning"

    def test_self_referential_context_is_error(self) -> None:
        yaml_self_ref = textwrap.dedent("""\
            sdl_version: "1.0"
            contexts:
              - name: finance
                description: Finance
                parent_context: finance
        """)
        doc = SDLDocument.from_yaml(yaml_self_ref)
        errors = validate(doc)
        codes = [e.code for e in errors]
        assert "SELF_REFERENTIAL_CONTEXT" in codes

    def test_fibo_banking_example_validates(self) -> None:
        if not FIBO_BANKING_YAML.exists():
            pytest.skip("FIBO banking example not found")
        doc = SDLDocument.from_yaml(FIBO_BANKING_YAML.read_text())
        errors = validate(doc)
        blocking = [e for e in errors if e.severity == "error"]
        assert blocking == [], f"FIBO example has errors: {blocking}"

    def test_validation_error_str_representation(self) -> None:
        err = ValidationError(
            severity="error",
            path="entities.Account.properties.balance",
            code="TEST_CODE",
            message="Test message",
        )
        s = str(err)
        assert "ERROR" in s
        assert "TEST_CODE" in s
        assert "Test message" in s
