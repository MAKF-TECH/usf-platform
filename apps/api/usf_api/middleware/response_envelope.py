from __future__ import annotations

from typing import Any

from usf_core.models import ProvenanceBlock, ResponseEnvelope, ResponseMeta


def wrap(
    data: Any,
    schema_ref: str | None = None,
    provenance: ProvenanceBlock | None = None,
    service: str = "usf-api",
) -> dict[str, Any]:
    """Wrap response data in standard USF envelope."""
    envelope = ResponseEnvelope(
        meta=ResponseMeta(service=service),
        data=data,
        schema_ref=schema_ref,
        provenance=provenance,
    )
    return envelope.model_dump(mode="json", exclude_none=True)
