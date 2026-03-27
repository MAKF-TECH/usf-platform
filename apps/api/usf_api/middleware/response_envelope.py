from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any


def wrap(data: Any, schema_ref: str | None = None, provenance: Any = None, service: str = "usf-api") -> dict[str, Any]:
    return {
        "meta": {"request_id": str(uuid.uuid4()), "timestamp": datetime.now(tz=timezone.utc).isoformat(), "version": "1.0", "service": service},
        "data": data,
        **({"schema_ref": schema_ref} if schema_ref else {}),
        **({"provenance": provenance} if provenance else {}),
    }
