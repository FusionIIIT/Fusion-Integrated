"""Immutable audit trail (PMS-AFR-207..212, BR-PMS-121, BR-PMS-122)."""
from __future__ import annotations

from modules.patents.models import PatentAuditLog


def record(
    actor,
    action_type: str,
    application=None,
    previous_state: str = "",
    new_state: str = "",
    **details,
) -> PatentAuditLog:
    """Append one audit record. `actor` is a principal, a user id, or None for system work."""
    actor_id = actor if isinstance(actor, int) else getattr(actor, "user_id", None)
    return PatentAuditLog.objects.create(
        application=application,
        actor_user_id=actor_id,
        action_type=action_type,
        previous_state=previous_state,
        new_state=new_state,
        details={k: v for k, v in details.items() if v not in (None, "")},
    )


def render(entry: PatentAuditLog) -> str:
    """One readable line per record, carrying every required audit field."""
    number = entry.application.application_number if entry.application_id else "-"
    parts = [
        entry.created_at.isoformat(),
        f"user={entry.actor_user_id if entry.actor_user_id is not None else 'system'}",
        f"action={entry.action_type}",
        f"application={number}",
        f"previous={entry.previous_state or '-'}",
        f"new={entry.new_state or '-'}",
    ]
    if entry.details:
        parts.append("details=" + "; ".join(f"{k}: {v}" for k, v in entry.details.items()))
    return " | ".join(parts)
