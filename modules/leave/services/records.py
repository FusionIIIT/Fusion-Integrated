"""Record synchronisation, which is not a second approval (BR-EL-029, BR-EL-037).

Two capabilities live here and both are deliberately *not* sanctioning:

EL-UC-016  record leave already sanctioned through an authorised paper route,
           with its evidence reference, so the account and history match
           reality. No approval workflow is created.
EL-UC-017  correct a recorded value within the administrator's authorised
           scope. A correction that would amount to a new decision is refused
           and must use the sanctioning path instead.

The distinction is enforced by what these functions can write: a ledger entry
and an adjustment row, never a decision.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.domain import categories as cat
from modules.leave.domain import counting
from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveRecordAdjustment, LeaveRequest
from modules.leave.selectors import leave as sel
from modules.leave.services import accounts, authz, facts, notifications

log = logging.getLogger("fusion.leave.records")

#: BR-EL-029 — only an authorised offline sanction may be synchronised.
P_BALANCE = "leave.balance.update"


def _employee_kind(user_id: int) -> str:
    employee = facts.employee(user_id)
    return employee.kind if employee else cat.STAFF


@transaction.atomic
def record_offline(*, actor, employee_user_id: int, category: str, period_from,
                   period_to, evidence_reference: str, purpose: str = "",
                   certified_by: str = "") -> LeaveRequest:
    """EL-UC-016 — synchronise leave already sanctioned outside ELM.

    The entry is validated for record consistency, the account moves, and the
    request is created already Approved because the sanction already happened.
    """
    authz.require(actor, P_BALANCE)
    if category not in cat.CATEGORIES:
        raise ConflictError(f"{category!r} is not a leave category in this baseline.",
                            code="unsupported_category",
                            details=[{"supported": list(cat.CATEGORIES)}])
    if not (evidence_reference or "").strip():
        raise ConflictError(
            "Recording offline-sanctioned leave needs the sanction/reference "
            "evidence.", code="evidence_required")

    employee = facts.employee(employee_user_id)
    if employee is None:
        raise ConflictError("That employee is not in the directory.",
                            code="employee_not_found")
    if period_to < period_from:
        raise ConflictError("The recorded period is not a valid range.",
                            code="period_invalid")
    if not cat.may_be_used_by(category, employee.kind):
        raise ConflictError(
            f"{cat.LABELS[category]} does not apply to a {employee.kind} employee.",
            code="category_not_applicable")

    existing = sel.active_intervals(user_id=employee_user_id)
    clash = [i for i in existing
             if not (i.end < period_from or period_to < i.start)]
    if clash:
        raise ConflictError(
            "The recorded period overlaps leave already on the employee's "
            "calendar; resolve the overlap before synchronising.",
            code="overlapping_leave",
            details=[{"from": i.start.isoformat(), "to": i.end.isoformat()}
                     for i in clash])

    days = counting.chargeable_days(category=category, start=period_from,
                                    end=period_to).days
    policy = sel.current_policy(period_from.year)

    request = LeaveRequest.objects.create(
        kind=sm.NEW, category=category, status=sm.APPROVED,
        user_id=employee_user_id, period_from=period_from, period_to=period_to,
        days_counted=days, purpose=(purpose or "Offline-sanctioned leave")[:300],
        source="offline", evidence_reference=evidence_reference[:160],
        decision_note=(f"Recorded from an authorising paper sanction"
                       f"{' by ' + certified_by if certified_by else ''}."),
        submitted_at=timezone.now(), decided_at=timezone.now(),
        decided_by_user_id=getattr(actor, "user_id", None))
    request.reference = f"ELMO-{period_from.year}-{request.pk:06d}"
    request.save(update_fields=["reference", "updated_at"])

    accounts.debit(
        user_id=employee_user_id, category=category, leave_year=period_from.year,
        days=days, request_id=request.pk,
        entitled_days=accounts.entitlement_for(
            category, employee.kind,
            entitlements=policy.entitlements if policy else None),
        note=f"Offline-sanctioned leave recorded ({evidence_reference})")

    LeaveRecordAdjustment.objects.create(
        request=request, action="annotate", field="evidence_reference",
        before="", after=evidence_reference[:200],
        reason="EL-UC-016 retrospective synchronisation",
        actor_user_id=getattr(actor, "user_id", 0))
    notifications.enqueue(
        topic="leave.record.synchronised",
        dedupe_key=f"leave.record:{request.pk}:offline",
        recipient_user_id=employee_user_id,
        subject="A leave record was added to your account",
        body=(f"{cat.LABELS[category]} from {period_from} to {period_to} "
              f"({days} day(s)) was recorded from an offline sanction."),
        payload={"request_id": request.pk})
    log.info("leave.records.offline_recorded request=%s user=%s by=%s",
             request.pk, employee_user_id, getattr(actor, "user_id", None))
    return request


@transaction.atomic
def adjust_balance(*, actor, employee_user_id: int, category: str, days: Decimal,
                   note: str, leave_year: int | None = None):
    """EL-UC-017 — an authorised balance correction, never a sanction."""
    authz.require(actor, P_BALANCE)
    if category not in cat.CATEGORIES:
        raise ConflictError(f"{category!r} is not a leave category in this baseline.",
                            code="unsupported_category")
    employee = facts.employee(employee_user_id)
    if employee is None:
        raise ConflictError("That employee is not in the directory.",
                            code="employee_not_found")
    year = leave_year or timezone.localdate().year
    policy = sel.current_policy(year)
    balance = accounts.adjust(
        user_id=employee_user_id, category=category, leave_year=year, days=days,
        employee_kind=employee.kind,
        entitlements=policy.entitlements if policy else None,
        note=note, actor_user_id=getattr(actor, "user_id", 0))
    log.info("leave.records.balance_adjusted user=%s category=%s days=%s by=%s",
             employee_user_id, category, days, getattr(actor, "user_id", None))
    return balance


@transaction.atomic
def correct_request(*, actor, request_id: int, field: str, value: str,
                    reason: str) -> LeaveRequest:
    """EL-UC-017 — correct a recorded field, keeping the before and after.

    Fields that would change what was decided are refused: `status`, the
    period and the day count are the decision, so changing them is a sanction
    and must go through the sanctioning path (BR-EL-037).
    """
    authz.require(actor, P_BALANCE)
    request = LeaveRequest.objects.select_for_update().filter(pk=request_id).first()
    if request is None:
        raise NotFoundError("No such leave record.")
    if not (reason or "").strip():
        raise ConflictError("A correction needs a reason.", code="reason_required")

    editable = {"purpose", "evidence_reference", "station_leave", "decision_note"}
    if field not in editable:
        raise ConflictError(
            f"{field!r} is part of the decision, not a record value; a change "
            "to it is a sanction, not maintenance.",
            code="sanction_equivalent_change",
            details=[{"editable": sorted(editable)}])

    before = str(getattr(request, field, ""))
    setattr(request, field, value)
    request.save(update_fields=[field, "updated_at"])
    LeaveRecordAdjustment.objects.create(
        request=request, action="update", field=field, before=before[:200],
        after=str(value)[:200], reason=reason[:300],
        actor_user_id=getattr(actor, "user_id", 0))
    return request
