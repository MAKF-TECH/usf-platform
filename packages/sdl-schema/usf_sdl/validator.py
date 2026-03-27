"""USF SDL Semantic Validator — cross-reference checks."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from usf_sdl.models import SDLDocument


@dataclass
class ValidationError:
    severity: Literal["error", "warning", "info"] = "error"
    path: str = ""
    code: str = ""
    message: str = ""
    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.path}: {self.message} (code={self.code})"


def validate(doc: SDLDocument) -> list[ValidationError]:
    """Validate an SDLDocument. Empty list = valid. Errors block; warnings are advisory."""
    errors: list[ValidationError] = []
    _check_entity_context_refs(doc, errors)
    _check_entity_policy_refs(doc, errors)
    _check_metric_entity_refs(doc, errors)
    _check_metric_context_refs(doc, errors)
    _check_metric_policy_refs(doc, errors)
    _check_property_context_refs(doc, errors)
    _check_entity_references(doc, errors)
    _check_context_parent_refs(doc, errors)
    return errors


def _check_entity_context_refs(doc: SDLDocument, errors: list[ValidationError]) -> None:
    for entity in doc.entities:
        for ctx in entity.contexts:
            if doc.context_names and ctx not in doc.context_names:
                errors.append(ValidationError("error", f"entities.{entity.name}.contexts.{ctx}", "UNDECLARED_CONTEXT", f"Context '{ctx}' not declared. Declared: {sorted(doc.context_names)}"))


def _check_entity_policy_refs(doc: SDLDocument, errors: list[ValidationError]) -> None:
    for entity in doc.entities:
        if isinstance(entity.access_policy, str) and entity.access_policy not in doc.access_policy_names:
            errors.append(ValidationError("error", f"entities.{entity.name}.access_policy", "UNDECLARED_ACCESS_POLICY", f"Policy '{entity.access_policy}' not declared"))


def _check_metric_entity_refs(doc: SDLDocument, errors: list[ValidationError]) -> None:
    for metric in doc.metrics:
        for ref, label in [(metric.measure_entity, "measure_entity"), (metric.time_entity, "time_entity")]:
            if ref and ref not in doc.entity_names:
                errors.append(ValidationError("error", f"metrics.{metric.name}.{label}", "UNDECLARED_ENTITY", f"Entity '{ref}' not declared"))
        for dim in metric.dimensions:
            if dim.entity not in doc.entity_names:
                errors.append(ValidationError("error", f"metrics.{metric.name}.dimensions.{dim.name}.entity", "UNDECLARED_ENTITY", f"Entity '{dim.entity}' not declared"))


def _check_metric_context_refs(doc: SDLDocument, errors: list[ValidationError]) -> None:
    for metric in doc.metrics:
        for ctx in metric.contexts:
            if doc.context_names and ctx not in doc.context_names:
                errors.append(ValidationError("error", f"metrics.{metric.name}.contexts.{ctx}", "UNDECLARED_CONTEXT", f"Context '{ctx}' not declared"))


def _check_metric_policy_refs(doc: SDLDocument, errors: list[ValidationError]) -> None:
    for metric in doc.metrics:
        if isinstance(metric.access_policy, str) and metric.access_policy not in doc.access_policy_names:
            errors.append(ValidationError("error", f"metrics.{metric.name}.access_policy", "UNDECLARED_ACCESS_POLICY", f"Policy '{metric.access_policy}' not declared"))


def _check_property_context_refs(doc: SDLDocument, errors: list[ValidationError]) -> None:
    for entity in doc.entities:
        for prop in entity.properties:
            for ctx in prop.contexts:
                if doc.context_names and ctx not in doc.context_names:
                    errors.append(ValidationError("error", f"entities.{entity.name}.properties.{prop.name}.contexts.{ctx}", "UNDECLARED_CONTEXT", f"Context '{ctx}' not declared"))
            if len(prop.contexts) >= 2:
                columns = {ctx: o.sql_column for ctx, o in prop.contexts.items() if o.sql_column}
                if len(set(columns.values())) > 1:
                    errors.append(ValidationError("warning", f"entities.{entity.name}.properties.{prop.name}", "CONTEXT_AMBIGUOUS_PROPERTY", f"Property '{prop.name}' has different sql_column per context: {columns}. Queries without X-USF-Context return HTTP 409."))


def _check_entity_references(doc: SDLDocument, errors: list[ValidationError]) -> None:
    for entity in doc.entities:
        for prop in entity.properties:
            if prop.references and prop.references.entity not in doc.entity_names:
                errors.append(ValidationError("error", f"entities.{entity.name}.properties.{prop.name}.references.entity", "UNDECLARED_ENTITY", f"Referenced entity '{prop.references.entity}' not declared"))


def _check_context_parent_refs(doc: SDLDocument, errors: list[ValidationError]) -> None:
    for ctx in doc.contexts:
        if ctx.parent_context:
            if ctx.parent_context not in doc.context_names:
                errors.append(ValidationError("error", f"contexts.{ctx.name}.parent_context", "UNDECLARED_CONTEXT", f"parent_context '{ctx.parent_context}' not declared"))
            if ctx.parent_context == ctx.name:
                errors.append(ValidationError("error", f"contexts.{ctx.name}.parent_context", "SELF_REFERENTIAL_CONTEXT", f"Context '{ctx.name}' cannot be its own parent"))
