from __future__ import annotations

"""Kafka/Redpanda consumer — OpenLineage events → AuditLog."""

import asyncio
import json

from aiokafka import AIOKafkaConsumer
from loguru import logger

from usf_audit.config import get_settings
from usf_audit.db import get_session
from usf_audit.models import AuditAction, AuditLogCreate, AuditStatus
from usf_audit.services.audit_writer import write_audit_log


def _event_to_audit(event: dict) -> AuditLogCreate | None:
    event_type = event.get("eventType", "").upper()
    if event_type not in ("COMPLETE", "FAIL", "START"):
        return None
    job = event.get("job", {})
    run = event.get("run", {})
    tenant_id = run.get("facets", {}).get("usf_ingestion", {}).get("tenant_id", "unknown")
    return AuditLogCreate(
        tenant_id=tenant_id,
        action=AuditAction.INGEST,
        status=AuditStatus.SUCCESS if event_type == "COMPLETE" else AuditStatus.ERROR,
        context=job.get("name"),
        query_hash=run.get("runId"),
        prov_jsonld=event,
        metadata={"event_type": event_type},
    )


async def start_kafka_consumer() -> None:
    settings = get_settings()
    consumer = AIOKafkaConsumer(
        settings.OPENLINEAGE_TOPIC,
        bootstrap_servers=settings.REDPANDA_BROKERS,
        group_id="usf-audit-consumer",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    await consumer.start()
    logger.info("Kafka consumer started", extra={"topic": settings.OPENLINEAGE_TOPIC})
    try:
        async for msg in consumer:
            try:
                entry = _event_to_audit(msg.value)
                if entry:
                    async for session in get_session():
                        await write_audit_log(session, entry)
            except Exception as exc:
                logger.error(f"Kafka message processing error: {exc}", exc_info=True)
    finally:
        await consumer.stop()
