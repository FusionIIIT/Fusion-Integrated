"""Transactional audit and internal outbox writes for Quiz service operations."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from modules.quiz.models import AuditEvent, OutboxEvent


def record_audit_event(
    *,
    actor_user_id: int | None,
    actor_kind: str,
    action: str,
    aggregate_type: str,
    aggregate_id: int,
    occurred_at: datetime,
    context: Mapping[str, Any] | None = None,
) -> AuditEvent:
    """Persist minimal audit context without answer text or private keys."""

    return AuditEvent.objects.create(
        actor_user_id=actor_user_id,
        actor_kind=actor_kind,
        action=action,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        occurred_at=occurred_at,
        context=dict(context or {}),
    )


def enqueue_internal_event(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: int,
    dedupe_key: str,
    available_at: datetime,
    payload: Mapping[str, Any] | None = None,
) -> OutboxEvent:
    """Persist an internal event without claiming an external delivery channel."""

    return OutboxEvent.objects.create(
        event_type=event_type,
        schema_version=1,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        dedupe_key=dedupe_key,
        payload=dict(payload or {}),
        available_at=available_at,
    )
