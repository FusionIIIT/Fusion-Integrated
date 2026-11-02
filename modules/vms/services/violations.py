"""Violation records.

VMS-BR-003: violations exist ONLY for expired passes and unauthorized zone
access. Every other refusal is an error, not a row.

VMS-BR-006: completing an already-closed visit raises a ConflictError — it
does not invent a third kind of violation, which VMS-BR-003 forbids. The
conflict IS the new violation the rule speaks of.

VMS-BR-010: a successful visibility check (roll-call present, re-validation)
auto-closes the open violations it makes moot.
"""
from __future__ import annotations

from django.utils import timezone

from core.api.exceptions import BadRequestError
from modules.vms.models import Violation, VisitLog


def raise_violation(*, kind: str, visit_id: int, visitor_id: int,
                    pass_id: int | None = None, zone_code: str = "",
                    details: dict | None = None) -> Violation:
    """Record a violation, refusing any kind outside VMS-BR-003."""
    allowed = {c for c, _ in Violation.KINDS}
    if kind not in allowed:
        raise BadRequestError(
            f"{kind!r} is not a violation kind VMS records.",
            code="invalid_violation_kind",
            details=[{"allowed": sorted(allowed)}])
    row = Violation.objects.create(
        visit_id=visit_id, visitor_id=visitor_id, pass_id=pass_id,
        kind=kind, zone_code=zone_code, details=details or {})
    VisitLog.objects.create(
        visit_id=visit_id, visitor_id=visitor_id, event_type="VIOLATION",
        pass_id=pass_id, zone_code=zone_code, occurred_at=timezone.now(),
        details={"violation_id": row.id, "kind": kind, **(details or {})})
    return row


def close_on_visibility(visit_id: int, *,
                        actor_user_id: int | None = None) -> list[Violation]:
    """VMS-BR-010: auto-close open violations once the visitor is seen."""
    rows = list(Violation.objects.filter(visit_id=visit_id, status="OPEN"))
    now = timezone.now()
    for row in rows:
        row.status = "RESOLVED"
        row.resolved_at = now
        row.resolved_by_user_id = actor_user_id
        row.save(update_fields=["status", "resolved_at", "resolved_by_user_id",
                                "updated_at"])
    return rows


def open_violations(visit_id: int) -> list[Violation]:
    return list(Violation.objects.filter(visit_id=visit_id, status="OPEN"))
