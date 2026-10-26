"""All writes. Transactions + domain validation live here; views stay thin.

Scope (Phase 2, Assignment 6B): submit / Unit-Head decide / withdraw / cancel
/ substitute response. NOT implemented here — see ../../UNRESOLVED.md:
entitlement-balance accounting (so cancellation does not actually restore a
balance, per BR-EL-023's second clause), the Dean/Registrar/Director
higher-sanction path for SCL/EL/COL/VL (BR-EL-018/019), extension, resumption,
year-end processing, SLA reminders/escalation, offline-sanction entry.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.elm.domain.rules import (
    can_cancel,
    can_withdraw,
    overlaps,
    validate_substitute,
)
from modules.elm.models import Category, HalfDay, LeaveRequest, Status
from modules.elm.selectors import leave_requests as sel


def _get_owned(user_id: int, leave_request_id: int) -> LeaveRequest:
    row = sel.visible_to(user_id).filter(pk=leave_request_id).first()
    if row is None:
        raise NotFoundError("Leave request not found.")
    return row


@transaction.atomic
def submit(
    *,
    applicant_user_id: int,
    category: str,
    start_date,
    end_date,
    unit_head_user_id: int,
    half_day: str = HalfDay.NONE,
    station_leave: bool = False,
    station_leave_details: str = "",
    reason: str = "",
    substitute_user_id: int | None = None,
) -> LeaveRequest:
    # BR-EL-001
    if category not in Category.values:
        raise BadRequestError(f"Unsupported leave category: {category!r}.",
                              code="invalid_category")
    # BR-EL-010
    if half_day != HalfDay.NONE and category != Category.CL:
        raise BadRequestError("Only CL supports a half-day request.",
                              code="invalid_half_day")
    if end_date < start_date:
        raise BadRequestError("end_date cannot be before start_date.",
                              code="invalid_date_range")

    # BR-EL-012: overlap against the applicant's own active requests.
    for existing in sel.active_for_applicant(applicant_user_id):
        if overlaps(start_date, end_date, half_day,
                    existing.start_date, existing.end_date, existing.half_day):
            raise ConflictError(
                f"Overlaps existing leave request #{existing.pk}.")

    substitute_consent = "not_required"
    if substitute_user_id is not None:
        # BR-EL-014: must be a real employee, not the applicant, with no
        # conflicting leave of their own during the same period.
        known = directory.get_employees()
        is_known_employee = any(e.user_id == substitute_user_id for e in known)
        has_conflict = any(
            overlaps(start_date, end_date, half_day,
                     r.start_date, r.end_date, r.half_day)
            for r in sel.active_for_substitute(substitute_user_id)
        )
        ok, why = validate_substitute(
            applicant_user_id, substitute_user_id, is_known_employee, has_conflict
        )
        if not ok:
            raise BadRequestError(why, code="invalid_substitute")
        substitute_consent = "pending"  # BR-EL-015: gate closed until accepted

    return LeaveRequest.objects.create(
        applicant_user_id=applicant_user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        station_leave=station_leave,
        station_leave_details=station_leave_details,
        reason=reason,
        unit_head_user_id=unit_head_user_id,
        substitute_user_id=substitute_user_id,
        substitute_consent=substitute_consent,
        status=Status.PENDING,
    )


@transaction.atomic
def decide_as_unit_head(
    *, acting_user_id: int, leave_request_id: int, approve: bool, remarks: str = "",
) -> LeaveRequest:
    row = _get_owned(acting_user_id, leave_request_id)
    if row.unit_head_user_id != acting_user_id:
        raise ConflictError("Only the assigned Unit Head may decide this request.")
    if row.status != Status.PENDING:
        raise ConflictError(f"Request is '{row.status}', not pending.")

    if row.category in (Category.CL, Category.RH):
        # BR-EL-016: Unit Head is the final authority for CL/RH.
        row.status = Status.APPROVED if approve else Status.REJECTED
    else:
        # BR-EL-017: Unit Head records a recommendation only; the
        # configured higher-sanction routing (BR-EL-018/019) that would
        # carry this to a final decision is NOT implemented (see
        # UNRESOLVED.md) — stopping here rather than faking an approval.
        row.status = (
            Status.UNIT_HEAD_RECOMMENDED if approve
            else Status.UNIT_HEAD_NOT_RECOMMENDED
        )
    row.unit_head_remarks = remarks
    row.unit_head_decided_at = timezone.now()
    row.save(update_fields=[
        "status", "unit_head_remarks", "unit_head_decided_at", "updated_at"
    ])
    return row


@transaction.atomic
def withdraw(*, acting_user_id: int, leave_request_id: int) -> LeaveRequest:
    row = _get_owned(acting_user_id, leave_request_id)
    if row.applicant_user_id != acting_user_id:
        raise ConflictError("Only the applicant may withdraw this request.")
    # BR-EL-022 / BR-EL-034
    if not can_withdraw(row.status):
        raise ConflictError(f"Request is '{row.status}'; only a pending "
                            "request can be withdrawn.")
    row.status = Status.WITHDRAWN
    row.withdrawn_at = timezone.now()
    row.save(update_fields=["status", "withdrawn_at", "updated_at"])
    return row


@transaction.atomic
def cancel(*, acting_user_id: int, leave_request_id: int) -> LeaveRequest:
    row = _get_owned(acting_user_id, leave_request_id)
    if row.applicant_user_id != acting_user_id:
        raise ConflictError("Only the applicant may cancel this leave.")
    # BR-EL-023. NOTE: no entitlement-balance ledger exists in this build,
    # so "restores/adjusts already deducted balance" is NOT performed —
    # only the status transition is. See UNRESOLVED.md.
    if not can_cancel(row.status, row.start_date, timezone.now().date()):
        raise ConflictError("Only an approved, not-yet-started leave can be "
                            "cancelled.")
    row.status = Status.CANCELLED
    row.cancelled_at = timezone.now()
    row.save(update_fields=["status", "cancelled_at", "updated_at"])
    return row


@transaction.atomic
def substitute_respond(
    *, acting_user_id: int, leave_request_id: int, accept: bool,
) -> LeaveRequest:
    """BR-EL-015. Re-nomination after a decline is NOT implemented — see
    UNRESOLVED.md; the applicant's only recourse today is withdraw+resubmit."""
    row = LeaveRequest.objects.filter(pk=leave_request_id).first()
    if row is None or row.substitute_user_id != acting_user_id:
        raise NotFoundError("Leave request not found.")
    if row.substitute_consent != "pending":
        raise ConflictError("This substitute nomination already has a response.")
    row.substitute_consent = "accepted" if accept else "declined"
    row.save(update_fields=["substitute_consent", "updated_at"])
    return row
