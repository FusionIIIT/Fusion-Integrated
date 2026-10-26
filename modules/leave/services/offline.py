"""Offline-sanctioned leave, recorded after the fact (EL-UC-016).

Leave already authorised on paper, where ELM could not be used, is a
synchronisation job rather than a second approval workflow (BR-EL-029,
BR-EL-037). Three things follow from that, and they are the whole module:

    the entry needs sanction/reference evidence, or it is not recorded
    it lands APPROVED, with no stages and no tasks — nobody sanctions it again
    it posts to the account like any other approved leave

An administrator who does this is maintaining a record. The moment it became a
way to approve leave it would be a different, and much worse, feature.
"""
from __future__ import annotations

import logging
from datetime import date

from core.api.exceptions import ConflictError, ValidationError
from modules.leave.domain import categories as cat
from modules.leave.domain.categories import leave_days
from modules.leave.domain.state_machine import APPROVED, KIND_NEW
from modules.leave.models import LeavePolicy, LeaveRequest
from modules.leave.selectors import balances as balance_selectors
from modules.leave.services import accounts, notifications

log = logging.getLogger("fusion.leave.offline")


def record(*, principal, user_id: int, category_code: str, from_date: date,
           to_date: date, sanctioned_on: date, sanction_reference: str,
           reason: str) -> LeaveRequest:
    """Enter leave that was already sanctioned offline."""
    policy = LeavePolicy.current()
    if policy is None:
        raise ValidationError("Leave has not been configured yet.",
                              code="policy_missing")

    if not sanction_reference.strip():
        raise ValidationError(
            "Sanction or reference evidence is required for an offline entry.",
            code="reference_missing")
    if category_code not in cat.CATEGORIES:
        raise ValidationError(
            f"{category_code or 'That'} is not a leave category.",
            code="category_not_supported")
    if to_date < from_date:
        raise ValidationError("The leave cannot end before it starts.",
                              code="invalid_period")

    cal = balance_selectors.effective_calendar(policy.year_label)
    if any(_overlaps(r, from_date, to_date) for r in _active(user_id)):
        raise ConflictError(
            "That period overlaps leave already recorded for this employee.",
            code="overlapping_leave")

    kind = _employee_kind(user_id)
    if kind not in cat.category(category_code).kinds:
        raise ValidationError(
            f"{cat.category(category_code).label} is not available to "
            f"{kind} employees.", code="category_not_applicable")

    days = leave_days(code=category_code, start=from_date, end=to_date,
                      closed_dates=cal["closed_dates"])

    request = LeaveRequest.objects.create(
        kind=KIND_NEW, category=category_code, user_id=user_id,
        from_date=from_date, to_date=to_date, days=days,
        purpose=f"Offline entry: {reason}", is_offline=True,
        sanction_reference=sanction_reference, sanctioned_on=sanctioned_on,
        offline_reason=reason, applicant_roles=[],
        unit_head_user_id=None, final_authority="Offline sanction",
        status=APPROVED, decision="approve",
        decision_remarks=f"Recorded from offline sanction {sanction_reference}",
        decided_by_user_id=principal.user_id)

    accounts.post(user_id=user_id, year_label=policy.year_label,
                  category=category_code, days=-days, kind="offline_entry",
                  note=f"Offline sanction {sanction_reference}", request=request)
    notifications.notify(
        topic="leave.decided", dedupe_key=f"leave.offline:{request.pk}",
        recipient_user_id=user_id,
        subject="Leave recorded from your offline sanction",
        body=(f"{request.get_category_display()} from {from_date} to "
              f"{to_date} has been recorded against reference "
              f"{sanction_reference}."),
        request=request)
    return request


def _active(user_id: int):
    return (LeaveRequest.objects
            .filter(user_id=user_id, kind=KIND_NEW)
            .exclude(status__in=["rejected", "withdrawn", "cancelled"])
            .only("from_date", "to_date", "half"))


def _overlaps(request: LeaveRequest, start: date, end: date) -> bool:
    return cat.Interval(start, end).overlaps(request.interval)


def _employee_kind(user_id: int) -> str:
    from modules.directory import contracts as directory

    person = directory.get_users([user_id]).get(user_id)
    return person.kind if person else cat.STAFF
