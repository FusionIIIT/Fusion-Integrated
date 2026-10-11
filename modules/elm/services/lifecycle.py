"""Cancellation, extension and resumption
(EL-UC-008/009/010/011).

Each is its own workflow object referencing the
application it acts on, so the original approval is never
edited in place: a cancellation either cancels the leave
and restores the balance or is rejected and changes
nothing; an extension posts only its incremental period;
a resumption is reviewed for normal / early / late and
synchronizes the record.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain.leave_types import (
    COL,
    EL,
    KIND_CANCELLATION,
    KIND_EXTENSION,
    KIND_NEW,
    RESUMPTION_REVIEW_PENDING,
    VL,
)
from modules.elm.domain.policy import (
    LeaveInterval,
    count_days,
    intervals_overlap,
)
from modules.elm.models import (
    LeaveRecord,
    LeaveRequest,
    Resumption,
)
from modules.elm.selectors.requests import closed_dates
from modules.elm.services import authz, workflow
from modules.elm.services import policy as policy_service

log = logging.getLogger("fusion.elm.lifecycle")

ZERO = Decimal("0")


# -- cancellation (EL-UC-008, CW-EL-02) ----------------------------------


@transaction.atomic
def request_cancellation(principal, *,
                           base_request_id: int,
                           effective_date=None,
                           reason: str = "") -> LeaveRequest:
    """Ask to cancel approved leave, from the point of
    cancellation through the end of the approved period.

    The request follows the same hierarchy the original
    leave did (the route is carried over), and approval
    restores the unexpired days to the balance.
    """
    authz.require_permission(principal, "elm.leave.cancel")
    base = _own_approved(principal, base_request_id)
    record = base.leave_record
    if record is None or record.status != "ongoing":
        raise ConflictError(
            "Only leave that is still in force can be "
            "cancelled.", code="leave_not_active")

    effective = effective_date or timezone.now().date()
    if effective < timezone.now().date():
        raise ConflictError(
            "A cancellation cannot be backdated.",
            code="invalid_effective_date")
    if effective > record.end_date:
        raise ConflictError(
            "The approved leave has already ended.",
            code="leave_already_ended")

    days = workflow.remaining_days(record, effective)
    request = LeaveRequest.objects.create(
        user_id=principal.user_id, kind=KIND_CANCELLATION,
        category=base.category, base_request=base,
        status="cancellation_pending_unit_head_review",
        start_date=effective, end_date=record.end_date,
        purpose=(f"Cancellation of approved {base.category} "
                 f"leave ({base.start_date} → {base.end_date})"),
        days=days, leave_year=base.leave_year,
        route=list(base.route or []),
        station_leave=record.station_leave,
        station_details=record.station_details,
    )
    workflow._log(
        request, "state_change",
        to_status="cancellation_pending_unit_head_review",
        actor=principal.user_id,
        actor_label=authz.user_label(principal),
        outcome="cancellation_requested", reason=reason)
    workflow.spawn_tasks(request)
    return request


def _own_approved(principal, base_request_id: int,
                    ):
    try:
        return LeaveRequest.objects.get(
            id=base_request_id, user_id=principal.user_id,
            kind=KIND_NEW, status="approved")
    except LeaveRequest.DoesNotExist as exc:
        raise NotFoundError(
            "No approved leave application with that id "
            "belongs to you.") from exc


# -- extension (EL-UC-009, CW-EL-03) --------------------------------------


@transaction.atomic
def request_extension(principal, *, base_request_id: int,
                        start_date, end_date, purpose: str,
                        substitute_required: bool = False,
                        substitute_user_id: int | None = None,
                        reason: str = "") -> LeaveRequest:
    """Extend ongoing EL/COL/VL.

    The extension must continue the approved leave
    without a gap, must fit the remaining balance, must
    not overlap anything, and — for VL — must stay
    inside a vacation period. On approval only the
    incremental period is posted.
    """
    authz.require_permission(principal, "elm.leave.extend")
    base = _own_approved(principal, base_request_id)
    if base.category not in (EL, COL, VL):
        raise ConflictError(
            "Extensions apply to EL, COL and VL only.",
            code="extension_not_applicable")
    record = base.leave_record
    if record is None or record.status != "ongoing":
        raise ConflictError(
            "The ongoing leave is no longer in force.",
            code="leave_not_active")
    if start_date != record.end_date + timedelta(days=1):
        raise ConflictError(
            "An extension must continue the approved leave "
            "from the day after it ends, without a gap.",
            code="extension_gap")
    if end_date < start_date:
        raise ConflictError(
            "The extension period ends before it starts.",
            code="invalid_period")

    profile = authz.employee_profile(principal.user_id)
    if base.category == VL and (
            profile is None
            or profile.employee_kind != "faculty"):
        raise ConflictError(
            "Vacation Leave applies to faculty only.",
            code="category_not_applicable")

    interval = LeaveInterval(
        category=base.category, start=start_date,
        end=end_date)
    days = count_days(interval, closed=closed_dates(),
                        restricted_holidays=frozenset())
    if days <= ZERO:
        raise ConflictError(
            "The extension period contains no countable "
            "leave days.", code="no_countable_days")

    from modules.elm.selectors import balances as balance_selector

    balance = balance_selector.balance_for(
        principal.user_id, base.leave_year, base.category)
    available = (balance.available_days if balance
                 else policy_service.entitlement_for(
                     base.category,
                     profile.employee_kind if profile
                     else None))
    if available < days:
        raise ConflictError(
            f"Available {base.category} balance "
            f"({available}) is less than the extension "
            f"({days}).", code="insufficient_balance")

    for other in LeaveRequest.objects.filter(
            user_id=principal.user_id).exclude(
                id=base.id).exclude(
                    status__in=("approved", "rejected",
                                "withdrawn")):
        other_interval = LeaveInterval(
            category=other.category, start=other.start_date,
            end=other.end_date, start_half=other.start_half,
            end_half=other.end_half)
        if intervals_overlap(interval, other_interval):
            raise ConflictError(
                f"Overlaps your pending {other.category} "
                f"request.", code="overlapping_leave")
    for ongoing in LeaveRecord.objects.filter(
            user_id=principal.user_id,
            status="ongoing").exclude(id=record.id):
        ongoing_interval = LeaveInterval(
            category=ongoing.category,
            start=ongoing.start_date, end=ongoing.end_date)
        if intervals_overlap(interval, ongoing_interval):
            raise ConflictError(
                f"Overlaps your approved {ongoing.category} "
                f"leave.", code="overlapping_leave")

    request = LeaveRequest.objects.create(
        user_id=principal.user_id, kind=KIND_EXTENSION,
        category=base.category, base_request=base,
        start_date=start_date, end_date=end_date,
        purpose=purpose, days=days,
        leave_year=base.leave_year,
        substitute_required=substitute_required,
        route=list(base.route or []),
    )
    if substitute_required:
        from modules.elm.services.applications import _validate_nominee

        if substitute_user_id is None:
            raise ConflictError(
                "Responsibility coverage is required: "
                "nominate a substitute.",
                code="substitute_required")
        _validate_nominee(request, substitute_user_id)
        from modules.elm.models import SubstituteNomination

        SubstituteNomination.objects.create(
            request=request,
            nominee_user_id=substitute_user_id)

    request.status = workflow.machine.initial_state(
        KIND_EXTENSION, substitute_required=substitute_required)
    request.save()
    workflow._log(
        request, "state_change",
        to_status=request.status,
        actor=principal.user_id,
        actor_label=authz.user_label(principal),
        outcome="extension_requested", reason=reason)
    workflow.spawn_tasks(request)
    return request


# -- resumption (EL-UC-010/011, CW-EL-04) ---------------------------------


@transaction.atomic
def submit_resumption(principal, *, record_id: int,
                        actual_resumption_date,
                        details: str = "") -> Resumption:
    """Report back from EL/COL/VL leave.

    The review decides normal / early / late against the
    approved end date and synchronizes the record and the
    balance.
    """
    authz.require_permission(principal, "elm.leave.resume")
    try:
        record = LeaveRecord.objects.get(
            id=record_id, user_id=principal.user_id,
            category__in=(EL, COL, VL))
    except LeaveRecord.DoesNotExist as exc:
        raise NotFoundError(
            "No EL/COL/VL leave record with that id "
            "belongs to you.") from exc
    if record.status != "ongoing":
        raise ConflictError(
            "This leave is no longer in force.",
            code="leave_not_active")
    if actual_resumption_date < record.start_date:
        raise ConflictError(
            "Resumption cannot precede the leave.",
            code="invalid_resumption_date")
    if Resumption.objects.filter(
            record=record,
            status=RESUMPTION_REVIEW_PENDING).exists():
        raise ConflictError(
            "A resumption for this leave is already "
            "awaiting review.", code="resumption_pending")

    resumption = Resumption.objects.create(
        record=record,
        request=record.source_request,
        actual_resumption_date=actual_resumption_date,
        details=details,
    )
    # The applicable Sanctioning Authority reviews — the
    # person who sanctioned the leave, when the record
    # came through ELM.
    assignee = None
    base_request = record.source_request
    if base_request is not None:
        assignee = base_request.decided_by_user_id
    if assignee is None:
        assignee = record.user_id
    workflow.create_resumption_task(resumption, assignee)
    return resumption


@transaction.atomic
def review_resumption(resumption: Resumption, principal, *,
                        outcome: str,
                        reason: str = "") -> Resumption:
    """Review a resumption as the applicable authority.

    ``normal``  — resumed the day after the approved end:
                  no adjustment.
    ``early``   — resumed before the end: the unused days
                  are restored to the balance.
    ``late``    — resumed after the end: the extra days are
                  charged to the balance and the record is
                  synchronized.
    """
    authz.require_permission(principal, "elm.resume.review")
    if resumption.status != RESUMPTION_REVIEW_PENDING:
        raise ConflictError(
            "This resumption has already been reviewed.",
            code="invalid_transition")

    record = resumption.record
    base_request = record.source_request
    expected_return = record.end_date + timedelta(days=1)
    actual = resumption.actual_resumption_date

    # The reviewer is the authority who sanctioned this
    # leave, or — for an offline-recorded leave — whoever
    # holds the review permission and the matching
    # designation.
    if (base_request is not None
            and principal.user_id != base_request.decided_by_user_id):
        final_step = (list(base_request.route
                           or [{}]))[-1]
        if not authz.is_final_authority(
                principal,
                final_step.get("authority") or ""):
            raise PermissionDeniedError(
                "This resumption is reviewed by the "
                "authority who sanctioned the leave.",
                code="not_actor")
    if outcome == "normal":
        if actual != expected_return:
            raise ConflictError(
                "A normal resumption is the day after the "
                "approved end date.",
                code="resumption_mismatch")
        adjustment = ZERO
        reviewed = "reviewed_normal"
        sync = ("Resumed on the expected date; record "
                "synchronized, no balance adjustment.")
        record.actual_end_date = record.end_date
    elif outcome == "early":
        if actual >= expected_return:
            raise ConflictError(
                "An early resumption precedes the expected "
                "return date.", code="resumption_mismatch")
        interval = LeaveInterval(
            category=record.category, start=actual,
            end=record.end_date,
            start_half=(record.start_half if actual
                        == record.start_date else "full"),
            end_half=record.end_half)
        adjustment = count_days(
            interval, closed=closed_dates())
        reviewed = "reviewed_early"
        sync = (f"Resumed early on {actual}; "
                f"{adjustment} day(s) restored to the "
                f"balance and the record synchronized.")
        record.actual_end_date = actual
    elif outcome == "late":
        if actual <= expected_return:
            raise ConflictError(
                "A late resumption follows the expected "
                "return date.", code="resumption_mismatch")
        interval = LeaveInterval(
            category=record.category,
            start=expected_return,
            end=actual - timedelta(days=1))
        adjustment = -count_days(
            interval, closed=closed_dates())
        reviewed = "reviewed_late"
        sync = (f"Resumed late on {actual}; "
                f"{abs(adjustment)} day(s) charged to the "
                f"balance and the record synchronized.")
        record.actual_end_date = actual
    else:
        raise ConflictError(
            "Outcome must be normal, early or late.",
            code="invalid_outcome")

    if adjustment != ZERO:
        from modules.elm.models import LeaveAccount

        account, _ = LeaveAccount.objects.get_or_create(
            user_id=record.user_id,
            leave_year=record.leave_year,
            category=record.category)
        account.used_days -= adjustment
        account.save()
        workflow._ledger(
            account, delta=adjustment,
            kind="resumption_adjustment",
            actor=principal.user_id,
            reason=f"Resumption review: {outcome}",
            request=base_request)
    record.save(update_fields=["actual_end_date",
                                 "updated_at"])
    resumption.status = reviewed
    resumption.adjustment_days = (
        adjustment if adjustment != ZERO else None)
    resumption.reviewed_by_user_id = principal.user_id
    resumption.reviewed_at = timezone.now()
    resumption.sync_note = sync
    resumption.save()
    workflow._log(
        base_request if base_request is not None
        else _request_for_record(record),
        "state_change",
        to_status="resumption_reviewed",
        actor=principal.user_id,
        actor_label=authz.user_label(principal),
        outcome=reviewed, reason=reason or sync)
    return resumption


def _request_for_record(record: LeaveRecord):
    """The application a record was posted from, if any."""
    return LeaveRequest.objects.filter(
        leave_record=record).first()
