"""Audit trail recording for ELM transitions."""
from __future__ import annotations

from modules.elm.models import LeaveApplication, LeaveAuditTrail


def record_audit(
    application: LeaveApplication,
    actor_id: int,
    action: str,
    from_status: str,
    to_status: str,
    remarks: str = "",
) -> LeaveAuditTrail:
    """Record an immutable audit row for an application transition."""
    return LeaveAuditTrail.objects.create(
        application=application,
        actor_id=actor_id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        remarks=remarks,
    )
