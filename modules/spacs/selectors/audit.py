"""Audit trail selectors and privacy redaction for SPACS.

Enforces:
- CFR-SPACS-011 (Student status view vs staff export)
- CFR-SPACS-016 (Audit Trail)
- BR-SPACS-021 (Audit access control and privacy redaction)
"""
from __future__ import annotations

from typing import Any
from django.db.models import QuerySet
from modules.spacs.models import SpacsAuditLog, ScholarshipApplication, ApplicationTransition


def get_audit_trail(
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_user_id: int | None = None,
    action: str | None = None,
    limit: int = 100,
) -> QuerySet[SpacsAuditLog]:
    """Retrieves protected audit records with optional filters."""
    qs = SpacsAuditLog.objects.all()

    if entity_type:
        qs = qs.filter(entity_type=entity_type)
    if entity_id:
        qs = qs.filter(entity_id=entity_id)
    if actor_user_id:
        qs = qs.filter(actor_user_id=actor_user_id)
    if action:
        qs = qs.filter(action=action)

    return qs[:limit]


def get_application_timeline(
    application: ScholarshipApplication,
    is_staff: bool = False,
) -> list[dict[str, Any]]:
    """Returns application transition history.

    Redacts internal reviewer notes and staff user IDs for students (CFR-SPACS-011, BR-SPACS-021).
    """
    transitions = ApplicationTransition.objects.filter(application=application).order_by("at")
    results = []

    for row in transitions:
        entry: dict[str, Any] = {
            "from_status": row.from_status,
            "to_status": row.to_status,
            "at": row.at,
        }
        if is_staff:
            entry["actor_user_id"] = row.actor_user_id
            entry["actor_role_label"] = row.actor_role_label
            entry["reason"] = row.reason
        else:
            # Student view: reveal only external explanation if returned for correction
            if row.to_status == "correction_required":
                entry["correction_request"] = row.reason
            entry["actor_role"] = row.actor_role_label

        results.append(entry)

    return results
