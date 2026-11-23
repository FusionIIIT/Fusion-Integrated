"""Escalations and exceptional cases PCC_ADMIN handles (BR-PMS-104; UC-PMS-016, 027)."""
from __future__ import annotations

from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import Escalation
from modules.pms.selectors import policy as policy_selector
from modules.pms.selectors import scoping
from modules.pms.services import audit, notifications
from modules.pms.services.base import lock, now, require, ruled

P_HANDLE = "pms.escalation.review"
LABELS = {
    "missed_review": "A Director review deadline was missed",
    "missed_revision": "A revision period ended",
    "missed_office_action": "An office-action response deadline was missed",
    "missed_maintenance": "A maintenance deadline was missed",
    "no_eligible_director": "No eligible Director is available",
    "no_eligible_attorney": "No eligible attorney is available",
    "conflicted_admin": "PCC_ADMIN is an applicant or inventor on this application",
    "budget_threshold": "A budget exceeds the threshold",
    "inactive_renewal_director": "The renewal decision's Director is no longer active",
}


def raise_case(kind: str, application, subject_id: int, *, deadline=None,
               note: str = "") -> Escalation | None:
    """Open one escalation per (kind, subject); a repeat while it is open does nothing."""
    try:
        with transaction.atomic():
            case = Escalation.objects.create(kind=kind, application=application,
                                             subject_id=subject_id, deadline=deadline,
                                             note=note[:2000])
    except IntegrityError:
        return None
    audit.record(None, f"escalation.{kind}", application=application, obj=case, to="open",
                 details={"subject_id": subject_id})
    spec = policy_selector.current()
    notifications.enqueue_many(
        topic="escalation.raised", key=f"escalation:{case.pk}",
        recipients=spec.escalation_recipients,
        subject=f"PMS escalation: {application.reference or 'draft'}",
        body=(f"{LABELS.get(kind, kind)} on application {application.reference}. "
              f"Open Patent Management, Deadlines & Escalations, to handle it."))
    return case


def resolve_open(application, kinds: tuple[str, ...], actor, note: str) -> int:
    rows = list(Escalation.objects.select_for_update().filter(
        application=application, kind__in=kinds, status__in=("open", "routed")))
    for case in rows:
        frm = case.status
        case.status, case.note = "resolved", (case.note + "\n" + note).strip()[:4000]
        case.handled_by_user_id, case.handled_at = getattr(actor, "user_id", None), now()
        case.save(update_fields=["status", "note", "handled_by_user_id", "handled_at",
                                 "updated_at"])
        audit.record(actor, "escalation.resolved", application=application, obj=case,
                     frm=frm, to="resolved")
    return len(rows)


@ruled
def handle(*, actor, escalation_id: int, action: str, note: str) -> Escalation:
    """UC-PMS-027: route the case to whoever decides it, or record it resolved."""
    require(actor, P_HANDLE)
    text = (note or "").strip()
    if action not in ("route", "resolve"):
        raise InvalidInput("Choose to route the case or to record it resolved.",
                           code="invalid_action")
    if not text:
        raise InvalidInput("Record what was done, or to whom the case was routed.",
                           code="note_required")
    with transaction.atomic():
        case = lock(scoping.escalations_for(actor), escalation_id, "escalation")
        if case.status == "resolved" or (action == "route" and case.status == "routed"):
            raise ConflictError(f"This escalation is already {case.status}.",
                                code="escalation_closed")
        frm = case.status
        case.status = "routed" if action == "route" else "resolved"
        case.note = (case.note + "\n" + text).strip()[:4000]
        case.handled_by_user_id, case.handled_at = actor.user_id, now()
        case.save(update_fields=["status", "note", "handled_by_user_id", "handled_at",
                                 "updated_at"])
        audit.record(actor, f"escalation.{action}", application=case.application, obj=case,
                     frm=frm, to=case.status)
    return case
