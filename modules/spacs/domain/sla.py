"""Pure Python SLA stage evaluation for SPACS.

Enforces:
- BR-SPACS-013 (Review SLA and Escalation)
- UC-SPACS-024 (Issue SLA Reminder / Escalation)
- Stage-aware multi-stage reminder and escalation progression
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def evaluate_due_sla_stages(
    sla_snapshot: dict[str, Any],
    task_created_at: datetime,
    already_notified_stage_keys: set[str],
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Evaluates task age against configured SLA stages.

    Returns a list of stages that have become due and have not yet been notified.
    Each returned stage dict contains: 'key', 'recipient_role', 'is_escalation', 'offset_hours'.
    """
    if not sla_snapshot or not sla_snapshot.get("stages"):
        return []

    if now is None:
        now = datetime.now(timezone.utc)

    # Ensure timezone aware
    if task_created_at.tzinfo is None:
        task_created_at = task_created_at.replace(tzinfo=timezone.utc)

    task_age_seconds = (now - task_created_at).total_seconds()
    task_age_hours = task_age_seconds / 3600.0

    due_stages: list[dict[str, Any]] = []
    # Sort stages by offset_hours so earlier reminders evaluate before later escalations
    stages = sorted(sla_snapshot.get("stages", []), key=lambda s: s.get("offset_hours", 0))

    for stage in stages:
        stage_key = stage.get("key")
        if not stage_key:
            continue

        if stage_key in already_notified_stage_keys:
            continue

        offset = stage.get("offset_hours", 0)
        if task_age_hours >= offset:
            due_stages.append(stage)

    return due_stages
