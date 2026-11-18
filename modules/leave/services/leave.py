"""All writes to a leave request (EL-WF-001 … EL-WF-008).

Raises domain errors rather than DRF exceptions, so the same call works from a
management command or a Celery task.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.leave.domain import rules
from modules.leave.models import (
    LeaveApplication,
    LeaveApproval,
    LeaveBalance,
    LeaveLedger,
    RestrictedHoliday,
)

log = logging.getLogger("fusion.leave")

OPEN_STATUSES = ("pending_substitute", "pending_unit_head", "pending_authority")


def leave_year_for(day: date) -> str:
    """The institute leave year runs April to March."""
    start = day.year if day.month >= 4 else day.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def _employee_kind(user_id: int) -> str:
    user = directory.get_users([user_id]).get(user_id)
    return user.kind if user else "staff"


def _designation(actor) -> str:
    return actor.active_role or ""


def _closed_dates(year: str) -> set[date]:
    return set(RestrictedHoliday.objects
               .filter(year=year, is_closed_holiday=True, is_published=True)
               .values_list("on_date", flat=True))


def _balance(user_id: int, year: str, leave_type: str,
             employee_kind: str) -> LeaveBalance:
    """The account row, created from policy entitlement on first use."""
    row, created = LeaveBalance.objects.get_or_create(
        user_id=user_id, year=year, leave_type=leave_type,
        defaults={"entitled": rules.entitlement_for(leave_type, employee_kind)},
    )
    if created:
        log.info("leave balance opened", extra={"user_id": user_id,
                                                "leave_type": leave_type})
    return row


def _as_rule_error(exc: rules.RuleViolation) -> ConflictError:
    return ConflictError(f"{exc.message} ({exc.rule})", code="rule_violation")


def _check_overlap(user_id: int, start: date, end: date, half_day: str,
                   exclude_id: int | None = None) -> None:
    existing = LeaveApplication.objects.filter(
        user_id=user_id, kind="leave",
        status__in=(*OPEN_STATUSES, "approved")).exclude(pk=exclude_id)
    for other in existing:
        if rules.overlaps(start, end, half_day, other.start_date,
                          other.end_date, other.half_day):
            raise ConflictError(
                f"This period overlaps leave request #{other.pk} "
                f"({other.start_date} to {other.end_date}).",
                code="overlapping_leave")


def _check_substitute(applicant_id: int, substitute_id: int, start: date,
                      end: date) -> None:
    """BR-EL-014: another employee, not the applicant, and free for the period."""
    if substitute_id == applicant_id:
        raise BadRequestError("You cannot nominate yourself as substitute.",
                              code="invalid_substitute")
    user = directory.get_users([substitute_id]).get(substitute_id)
    if user is None or user.kind not in ("faculty", "staff"):
        raise BadRequestError("The substitute must be another employee.",
                              code="invalid_substitute")
    busy = LeaveApplication.objects.filter(
        user_id=substitute_id, kind="leave",
        status__in=(*OPEN_STATUSES, "approved"),
        start_date__lte=end, end_date__gte=start).exists()
    if busy:
        raise ConflictError(
            "The nominated substitute has leave of their own in this period.",
            code="substitute_unavailable")


@transaction.atomic
def apply_for_leave(actor, *, leave_type: str, start_date: date, end_date: date,
                    half_day: str = "", reason: str = "",
                    station_leave: bool = False, station_place: str = "",
                    substitute_user_id: int | None = None,
                    kind: str = "leave",
                    parent: LeaveApplication | None = None) -> LeaveApplication:
    """EL-UC-001. Validates category, calendar, balance, overlap and substitute
    before the request is allowed to enter approval routing."""
    year = leave_year_for(start_date)
    employee_kind = _employee_kind(actor.user_id)
    try:
        rules.entitlement_for(leave_type, employee_kind)
        days = rules.count_days(leave_type, start_date, end_date, half_day,
                                _closed_dates(year))
    except rules.RuleViolation as exc:
        raise _as_rule_error(exc) from exc

    if leave_type == "RH":
        matched = RestrictedHoliday.objects.filter(
            year=year, on_date__gte=start_date, on_date__lte=end_date,
            is_published=True).exists()
        if not matched:
            raise ConflictError(
                "An RH request must fall on a Restricted Holiday in the "
                "published calendar. (BR-EL-003)", code="rh_not_in_calendar")

    _check_overlap(actor.user_id, start_date, end_date, half_day)

    balance = _balance(actor.user_id, year, leave_type, employee_kind)
    if days > balance.available:
        raise ConflictError(
            f"Only {balance.available} day(s) of {leave_type} remain, and this "
            f"request is for {days}.", code="insufficient_balance")

    if substitute_user_id:
        _check_substitute(actor.user_id, substitute_user_id, start_date, end_date)

    chain = rules.resolve_chain(leave_type, _designation(actor))
    application = LeaveApplication.objects.create(
        user_id=actor.user_id, kind=kind, parent=parent, leave_type=leave_type,
        start_date=start_date, end_date=end_date, half_day=half_day, days=days,
        reason=reason, station_leave=station_leave, station_place=station_place,
        substitute_user_id=substitute_user_id,
        substitute_status="pending" if substitute_user_id else "not_required",
        status="pending_substitute" if substitute_user_id else "pending_unit_head",
        pending_role="Substitute" if substitute_user_id else "Unit Head",
        authority_chain=chain,
    )
    _record(application, "Employee", "submitted", actor.user_id, reason[:300])

    # BR-EL-020: the Director's own leave needs nobody else's signature.
    if not substitute_user_id and _designation(actor) == rules.DIRECTOR_DESIGNATION:
        _approve(application, actor.user_id, "Self-sanctioned (BR-EL-020)")
    return application


def _record(application: LeaveApplication, step_role: str, action: str,
            actor_user_id: int | None, note: str = "") -> None:
    LeaveApproval.objects.create(application=application, step_role=step_role,
                                 action=action, actor_user_id=actor_user_id,
                                 note=note)


def _post_balance(application: LeaveApplication, delta: Decimal,
                  reason: str) -> None:
    year = leave_year_for(application.start_date)
    balance = _balance(application.user_id, year, application.leave_type,
                       _employee_kind(application.user_id))
    balance.availed = balance.availed + delta
    balance.save(update_fields=["availed", "updated_at"])
    LeaveLedger.objects.create(user_id=application.user_id,
                               application=application, year=year,
                               leave_type=application.leave_type, delta=delta,
                               reason=reason)


def _approve(application: LeaveApplication, actor_user_id: int,
             note: str) -> LeaveApplication:
    application.status = "approved"
    application.pending_role = ""
    application.decided_at = timezone.now()
    application.decided_by_user_id = actor_user_id
    application.decision_note = note[:300]
    application.save()
    _record(application, "Sanctioning Authority", "approved", actor_user_id, note)
    if application.kind == "cancellation":
        _cancel_parent(application, actor_user_id)
    else:
        _post_balance(application, application.days, "leave approved")
    return application


def _cancel_parent(cancellation: LeaveApplication, actor_user_id: int) -> None:
    """BR-EL-023: the approved leave is marked cancelled and the deducted
    balance restored."""
    original = cancellation.parent
    if original is None:
        return
    original.status = "cancelled"
    original.decision_note = "Cancelled on request"
    original.save(update_fields=["status", "decision_note", "updated_at"])
    _post_balance(original, -original.days, "cancellation approved")
    _record(original, "System", "cancelled", actor_user_id)


@transaction.atomic
def respond_to_nomination(actor, application: LeaveApplication, *,
                          accept: bool, note: str = "") -> LeaveApplication:
    """EL-UC-002. Consent is a gate: routing does not continue without it."""
    if application.substitute_user_id != actor.user_id:
        raise NotFoundError("Not found.")
    if application.substitute_status != "pending":
        raise ConflictError("This nomination has already been answered.")
    application.substitute_status = "accepted" if accept else "declined"
    if accept:
        application.status = "pending_unit_head"
        application.pending_role = "Unit Head"
    else:
        # BR-EL-015: the applicant nominates somebody else, or withdraws.
        application.status = "pending_substitute"
        application.pending_role = "Substitute"
    application.save()
    _record(application, "Substitute", application.substitute_status,
            actor.user_id, note)
    return application


@transaction.atomic
def review(actor, application: LeaveApplication, *, action: str,
           note: str = "") -> LeaveApplication:
    """EL-UC-003. Final for CL/RH; a recommendation for everything else."""
    if application.status != "pending_unit_head":
        raise ConflictError("This request is not awaiting Unit Head review.")
    if application.leave_type in rules.UNIT_HEAD_FINAL:
        if action not in ("approve", "reject"):
            raise BadRequestError("CL and RH need approve or reject.",
                                  code="invalid_action")
        if action == "approve":
            return _approve(application, actor.user_id, note)
        return _reject(application, actor.user_id, note, "Unit Head")

    if action not in ("recommend", "not_recommend"):
        raise BadRequestError(
            "Higher-sanction leave is recommended or not recommended, not "
            "decided, at this step. (BR-EL-017)", code="invalid_action")
    application.unit_head_recommendation = (
        "recommended" if action == "recommend" else "not_recommended")
    application.status = "pending_authority"
    chain = list(application.authority_chain or ["Registrar"])
    application.pending_role = chain[0]
    application.save()
    _record(application, "Unit Head", application.unit_head_recommendation,
            actor.user_id, note)
    return application


def _reject(application: LeaveApplication, actor_user_id: int, note: str,
            step_role: str) -> LeaveApplication:
    application.status = "rejected"
    application.pending_role = ""
    application.decided_at = timezone.now()
    application.decided_by_user_id = actor_user_id
    application.decision_note = note[:300]
    application.save()
    _record(application, step_role, "rejected", actor_user_id, note)
    return application


@transaction.atomic
def sanction(actor, application: LeaveApplication, *, action: str,
             note: str = "") -> LeaveApplication:
    """EL-UC-004 and EL-UC-005: forward along the configured chain, then decide."""
    if application.status != "pending_authority":
        raise ConflictError("This request is not awaiting a sanctioning decision.")
    if action == "reject":
        return _reject(application, actor.user_id, note, application.pending_role)
    if action not in ("approve", "forward"):
        raise BadRequestError("Expected approve, forward or reject.",
                              code="invalid_action")

    chain = list(application.authority_chain or [])
    if application.pending_role in chain:
        remaining = chain[chain.index(application.pending_role) + 1:]
    else:
        remaining = []
    if action == "forward" and remaining:
        _record(application, application.pending_role, "forwarded",
                actor.user_id, note)
        application.pending_role = remaining[0]
        application.save(update_fields=["pending_role", "updated_at"])
        return application
    return _approve(application, actor.user_id, note)


@transaction.atomic
def withdraw(actor, application: LeaveApplication, *,
             note: str = "") -> LeaveApplication:
    """EL-UC-007. Immediate, and it ends all remaining approval processing."""
    if application.user_id != actor.user_id:
        raise NotFoundError("Not found.")
    if application.status not in OPEN_STATUSES:
        raise ConflictError(
            "Only a pending request can be withdrawn. After final approval, "
            "request cancellation instead. (BR-EL-022)", code="not_pending")
    application.status = "withdrawn"
    application.pending_role = ""
    application.decided_at = timezone.now()
    application.save()
    _record(application, "Employee", "withdrawn", actor.user_id, note)
    return application


@transaction.atomic
def request_cancellation(actor, application: LeaveApplication, *,
                         reason: str = "") -> LeaveApplication:
    """EL-UC-008. A fresh request that follows the same hierarchy."""
    if application.user_id != actor.user_id:
        raise NotFoundError("Not found.")
    if application.status != "approved":
        raise ConflictError("Only approved leave can be cancelled.",
                            code="not_approved")
    if application.start_date <= timezone.localdate():
        raise ConflictError(
            "The leave has already begun; use resumption instead. (BR-EL-023)",
            code="leave_started")
    chain = rules.resolve_chain(application.leave_type, _designation(actor))
    cancellation = LeaveApplication.objects.create(
        user_id=actor.user_id, kind="cancellation", parent=application,
        leave_type=application.leave_type, start_date=application.start_date,
        end_date=application.end_date, days=application.days, reason=reason,
        status="pending_unit_head", pending_role="Unit Head",
        authority_chain=chain,
    )
    _record(cancellation, "Employee", "cancellation_requested", actor.user_id,
            reason[:300])
    return cancellation


@transaction.atomic
def submit_resumption(actor, application: LeaveApplication, *,
                      actual_end_date: date, note: str = "") -> LeaveApplication:
    """EL-UC-010. Early or late resumption adjusts the posted balance."""
    if application.user_id != actor.user_id:
        raise NotFoundError("Not found.")
    if application.leave_type not in rules.EXTENDABLE:
        raise ConflictError("Resumption applies to EL, COL and VL. (BR-EL-027)",
                            code="not_resumable")
    if application.status != "approved":
        raise ConflictError("Only approved leave can be resumed from.",
                            code="not_approved")
    year = leave_year_for(application.start_date)
    try:
        actual_days = rules.count_days(application.leave_type,
                                       application.start_date, actual_end_date,
                                       "", _closed_dates(year))
    except rules.RuleViolation as exc:
        raise _as_rule_error(exc) from exc

    delta = actual_days - application.days
    application.actual_end_date = actual_end_date
    application.resumption_note = note[:300]
    application.save(update_fields=["actual_end_date", "resumption_note",
                                    "updated_at"])
    if delta != 0:
        _post_balance(application, delta, "resumption adjustment")
    _record(application, "Employee", "resumed", actor.user_id,
            f"actual end {actual_end_date}")
    return application
