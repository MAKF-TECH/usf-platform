"""
USF SDL Schema — Pydantic v2 models for the Semantic Definition Language.

This package provides:
- Pydantic v2 models for all SDL constructs (Context, Entity, Metric, AccessPolicy)
- A validate() function that returns typed ValidationError list
- Example SDL files for the FIBO banking pilot

Usage:
    from usf_sdl.models import SDLDocument
    from usf_sdl.validator import validate

    with open("fibo_banking.yaml") as f:
        doc = SDLDocument.from_yaml(f.read())
    errors = validate(doc)
"""

from usf_sdl.models import (
    SDLDocument,
    ContextDefinition,
    EntityDefinition,
    MetricDefinition,
    AccessPolicyDefinition,
    PropertyDefinition,
    DimensionDefinition,
)
from usf_sdl.validator import validate, ValidationError

__all__ = [
    "SDLDocument",
    "ContextDefinition",
    "EntityDefinition",
    "MetricDefinition",
    "AccessPolicyDefinition",
    "PropertyDefinition",
    "DimensionDefinition",
    "validate",
    "ValidationError",
]
