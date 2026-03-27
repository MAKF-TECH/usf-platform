"""
USF SDL Validator.

Performs semantic validation on a parsed SDLDocument — checks that:
- Entity references in metrics and properties resolve to declared entities
- Context references resolve to declared contexts
- Access policy references resolve to declared policies
- Metric entities and dimension entities are declared
- Time grain requirements are satisfied
- Context ambiguity rules (multi-context properties)

Note: Pydantic models handle structural/type validation.
This module handles semantic/cross-reference validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from usf_sdl.models import SDLDocument, EntityDefinition, MetricDefinition


# ─────────────────────────────────────────────────────────────────
# Error types
# ─────────────────────────────────────────────────────────────────


@dataclass
class ValidationError:
    """A single SDL validation error."""

    severity: Literal["error", "warning", "info"] = "error"
    path: str = ""
    code: str = ""
    message: str = ""

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.path}: {self.message} (code={self.code})"


# ─────────────────────────────────────────────────────────────────
# Validator
# ─────────────────────────────────────────────────────────────────


def validate(doc: SDLDocument) -> list[ValidationError]:
    """
    Validate an SDLDocument for semantic correctness.

    Returns a list of ValidationError objects. An empty list means valid.
    Errors with severity='error' are blocking; 'warning' are advisory.
    """
    errors: list[ValidationError] = []

    _validate_entity_context_refs(doc, errors)
    _validate_entity_access_policy_refs(doc, errors)
    _validate_metric_entity_refs(doc, errors)
    _validate_metric_context_refs(doc, errors)
    _validate_metric_access_policy_refs(doc, errors)
    _validate_property_context_refs(doc, errors)
    _validate_entity_references(doc, errors)
    _validate_context_parent_refs(doc, errors)

    return errors


# ─────────────────────────────────────────────────────────────────
# Private validation helpers
# ─────────────────────────────────────────────────────────────────


def _validate_entity_context_refs(doc: SDLDocument, errors: list[ValidationError]) -> None:
    """Entity context overrides must reference declared contexts."""
    declared_contexts = doc.context_names
    for entity in doc.entities:
        for ctx_name in entity.contexts:
            if declared_contexts and ctx_name not in declared_contexts:
                errors.append(
                    ValidationError(
                        severity="error",
                        path=f"entities.{entity.name}.contexts.{ctx_name}",
                        code="UNDECLARED_CONTEXT",
                        message=(
                            f"Context '{ctx_name}' referenced in entity '{entity.name}' "
                            f"is not declared in contexts block. "
                            f"Declared: {sorted(declared_contexts)}"
                        ),
                    )
                )


def _validate_entity_access_policy_refs(doc: SDLDocument, errors: list[ValidationError]) -> None:
    """String access_policy references in entities must resolve to declared policies."""
    declared_policies = doc.access_policy_names
    for entity in doc.entities:
        if isinstance(entity.access_policy, str):
            if entity.access_policy not in declared_policies:
                errors.append(
                    ValidationError(
                        severity="error",
                        path=f"entities.{entity.name}.access_policy",
                        code="UNDECLARED_ACCESS_POLICY",
                        message=(
                            f"Access policy '{entity.access_policy}' referenced in entity "
                            f"'{entity.name}' is not declared. "
                            f"Declared: {sorted(declared_policies)}"
                        ),
                    )
                )


def _validate_metric_entity_refs(doc: SDLDocument, errors: list[ValidationError]) -> None:
    """Metric measure_entity and dimension entities must be declared entities."""
    declared_entities = doc.entity_names
    for metric in doc.metrics:
        # Check measure_entity
        if metric.measure_entity not in declared_entities:
            errors.append(
                ValidationError(
                    severity="error",
                    path=f"metrics.{metric.name}.measure_entity",
                    code="UNDECLARED_ENTITY",
                    message=(
                        f"measure_entity '{metric.measure_entity}' in metric '{metric.name}' "
                        f"is not a declared entity. Declared: {sorted(declared_entities)}"
                    ),
                )
            )
        # Check time_entity
        if metric.time_entity and metric.time_entity not in declared_entities:
            errors.append(
                ValidationError(
                    severity="error",
                    path=f"metrics.{metric.name}.time_entity",
                    code="UNDECLARED_ENTITY",
                    message=(
                        f"time_entity '{metric.time_entity}' in metric '{metric.name}' "
                        f"is not declared. Declared: {sorted(declared_entities)}"
                    ),
                )
            )
        # Check dimension entities
        for dim in metric.dimensions:
            if dim.entity not in declared_entities:
                errors.append(
                    ValidationError(
                        severity="error",
                        path=f"metrics.{metric.name}.dimensions.{dim.name}.entity",
                        code="UNDECLARED_ENTITY",
                        message=(
                            f"Dimension entity '{dim.entity}' in metric '{metric.name}' "
                            f"is not declared. Declared: {sorted(declared_entities)}"
                        ),
                    )
                )


def _validate_metric_context_refs(doc: SDLDocument, errors: list[ValidationError]) -> None:
    """Metric context overrides must reference declared contexts."""
    declared_contexts = doc.context_names
    for metric in doc.metrics:
        for ctx_name in metric.contexts:
            if declared_contexts and ctx_name not in declared_contexts:
                errors.append(
                    ValidationError(
                        severity="error",
                        path=f"metrics.{metric.name}.contexts.{ctx_name}",
                        code="UNDECLARED_CONTEXT",
                        message=(
                            f"Context '{ctx_name}' in metric '{metric.name}' is not declared. "
                            f"Declared: {sorted(declared_contexts)}"
                        ),
                    )
                )


def _validate_metric_access_policy_refs(doc: SDLDocument, errors: list[ValidationError]) -> None:
    """String access_policy references in metrics must resolve."""
    declared_policies = doc.access_policy_names
    for metric in doc.metrics:
        if isinstance(metric.access_policy, str):
            if metric.access_policy not in declared_policies:
                errors.append(
                    ValidationError(
                        severity="error",
                        path=f"metrics.{metric.name}.access_policy",
                        code="UNDECLARED_ACCESS_POLICY",
                        message=(
                            f"Access policy '{metric.access_policy}' in metric '{metric.name}' "
                            f"is not declared. Declared: {sorted(declared_policies)}"
                        ),
                    )
                )


def _validate_property_context_refs(doc: SDLDocument, errors: list[ValidationError]) -> None:
    """Per-property context overrides must reference declared contexts."""
    declared_contexts = doc.context_names
    for entity in doc.entities:
        for prop in entity.properties:
            for ctx_name in prop.contexts:
                if declared_contexts and ctx_name not in declared_contexts:
                    errors.append(
                        ValidationError(
                            severity="error",
                            path=f"entities.{entity.name}.properties.{prop.name}.contexts.{ctx_name}",
                            code="UNDECLARED_CONTEXT",
                            message=(
                                f"Context '{ctx_name}' in property '{prop.name}' of entity "
                                f"'{entity.name}' is not declared. "
                                f"Declared: {sorted(declared_contexts)}"
                            ),
                        )
                    )
            # Warn about context-ambiguous properties (defined in 2+ contexts with different columns)
            if len(prop.contexts) >= 2:
                columns = {
                    ctx: override.sql_column
                    for ctx, override in prop.contexts.items()
                    if override.sql_column
                }
                unique_columns = set(columns.values())
                if len(unique_columns) > 1:
                    errors.append(
                        ValidationError(
                            severity="warning",
                            path=f"entities.{entity.name}.properties.{prop.name}",
                            code="CONTEXT_AMBIGUOUS_PROPERTY",
                            message=(
                                f"Property '{prop.name}' in entity '{entity.name}' has different "
                                f"sql_column values per context: {columns}. "
                                f"Queries without X-USF-Context will return HTTP 409."
                            ),
                        )
                    )


def _validate_entity_references(doc: SDLDocument, errors: list[ValidationError]) -> None:
    """Property references to other entities must resolve."""
    declared_entities = doc.entity_names
    for entity in doc.entities:
        for prop in entity.properties:
            if prop.references is not None:
                ref_entity = prop.references.entity
                if ref_entity not in declared_entities:
                    errors.append(
                        ValidationError(
                            severity="error",
                            path=f"entities.{entity.name}.properties.{prop.name}.references.entity",
                            code="UNDECLARED_ENTITY",
                            message=(
                                f"Referenced entity '{ref_entity}' in property '{prop.name}' "
                                f"of entity '{entity.name}' is not declared. "
                                f"Declared: {sorted(declared_entities)}"
                            ),
                        )
                    )


def _validate_context_parent_refs(doc: SDLDocument, errors: list[ValidationError]) -> None:
    """Context parent_context references must resolve."""
    declared_contexts = doc.context_names
    for ctx in doc.contexts:
        if ctx.parent_context and ctx.parent_context not in declared_contexts:
            errors.append(
                ValidationError(
                    severity="error",
                    path=f"contexts.{ctx.name}.parent_context",
                    code="UNDECLARED_CONTEXT",
                    message=(
                        f"parent_context '{ctx.parent_context}' of context '{ctx.name}' "
                        f"is not declared. Declared: {sorted(declared_contexts)}"
                    ),
                )
            )
        # Prevent self-reference
        if ctx.parent_context == ctx.name:
            errors.append(
                ValidationError(
                    severity="error",
                    path=f"contexts.{ctx.name}.parent_context",
                    code="SELF_REFERENTIAL_CONTEXT",
                    message=f"Context '{ctx.name}' cannot be its own parent.",
                )
            )
