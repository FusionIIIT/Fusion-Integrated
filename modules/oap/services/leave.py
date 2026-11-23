from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError
from core.files import drive
from modules.oap.domain import roles
from modules.oap.domain import state_machines as sm
from modules.oap.models import LeaveApplication
from modules.oap.selectors import scoping
from modules.oap.services import notifications
from modules.oap.services.common import domain_guard, locked, need, need_role, record

DECISIONS = {"approve": "approve", "reject": "reject"}


def _document(raw: str) -> str:
    if not raw:
        return ""
    try:
        return drive.parse(raw).url
    except drive.InvalidDriveLink as exc:
        raise BadRequestError(exc.message, code=exc.code) from exc


def submit(
    principal, *, reason: str, from_date: date, to_date: date, supporting_document_link: str = ""
) -> LeaveApplication:
    need(principal, "oap.leave_application.create")
    if to_date < from_date:
        raise BadRequestError(
            "The leave end date cannot be before its start date.", code="dates_out_of_order"
        )
    link = _document(supporting_document_link)
    with transaction.atomic():
        app = LeaveApplication.objects.create(
            user_id=principal.user_id,
            reason=reason,
            from_date=from_date,
            to_date=to_date,
            supporting_document_link=link,
        )
        record("leave", app.pk, "", sm.LEAVE_SUBMITTED, principal.user_id)
        notifications.notify(
            [principal.user_id],
            "Leave application submitted",
            f"Your leave application #{app.pk} was submitted for HoD review.",
        )
    return app


def decide(principal, pk: int, outcome: str) -> LeaveApplication:
    need(principal, "oap.leave_application.approve")
    need_role(principal, roles.HOD)
    if outcome not in DECISIONS:
        raise BadRequestError("Outcome must be 'approve' or 'reject'.", code="invalid_outcome")
    with transaction.atomic(), domain_guard():
        app = locked(scoping.leave_for(principal), pk, "Leave application not found.")
        new_state = sm.next_state("leave", app.status, DECISIONS[outcome], "hod")
        previous = app.status
        app.status = new_state
        app.decided_by_user_id = principal.user_id
        app.decided_at = timezone.now()
        app.save(update_fields=["status", "decided_by_user_id", "decided_at", "updated_at"])
        record("leave", app.pk, previous, new_state, principal.user_id)
        notifications.notify(
            [app.user_id],
            "Leave application decided",
            f"Your leave application #{app.pk} was {new_state}.",
        )
    return app
