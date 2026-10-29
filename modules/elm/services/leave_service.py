"""Leave request lifecycle service functions (CW-EL-01 through CW-EL-04).

All writes to LeaveRequest go through these functions.
Transitions enforce state machine rules, permission checks, and transaction safety.
"""
from __future__ import annotations

import datetime
from decimal import Decimal
import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain import leave_policy as lp
from modules.elm.domain import state_machine as sm
from modules.elm.models import (
    HolidayCalendar,
    LeaveBalance,
    LeaveRequest,
    LeaveTransition,
)
from modules.elm.services import balances as balance_service

log = logging.getLogger("fusion.elm.services")


def resolve_or_raise(frm: str, to: str, kind: str) -> sm.Transition:
    """`sm.resolve` with domain errors translated to platform HTTP-compatible exceptions."""
    try:
        return sm.resolve(frm, to, kind)
    except sm.InvalidTransition as exc:
        raise ConflictError(
            f"A leave request cannot move from '{exc.frm}' to '{exc.to}'.",
            code="invalid_transition",
            details=[{"from": exc.frm, "to": exc.to,
                      "allowed": sm.allowed_targets(exc.frm, kind)}],
        ) from exc
    except sm.ActorNotAllowed as exc:
        raise PermissionDeniedError(
            f"Your role ({exc.actor_kind}) cannot make that change.",
            code="actor_not_allowed",
            details=[{"from": exc.frm, "to": exc.to, "actor": exc.actor_kind}],
        ) from exc


def get_actor_kind(actor: Any, request: LeaveRequest | None = None) -> str:
    """Determine the actor's state machine lane."""
    if actor is None:
        return sm.SYSTEM

    actor_user_id = getattr(actor, "user_id", None)

    # Substitute lane
    if request is not None and request.substitute_id and actor_user_id == request.substitute_id:
        return sm.SUBSTITUTE

    # Admin / Director lane
    if getattr(actor, "is_director", False):
        return sm.DIRECTOR

    # Sanctioning Authority / Unit Head
    if hasattr(actor, "has_permission"):
        if actor.has_permission("elm.admin.manage_calendar") or actor.has_permission("elm.leave.report"):
            return sm.SANCTION_AUTH
        if actor.has_permission("elm.leave.approve"):
            # If acting on their own leave, drop to employee lane (self-approval guard)
            if request is not None and request.user_id == actor_user_id:
                return sm.EMPLOYEE
            return sm.UNIT_HEAD

    return sm.EMPLOYEE


def _check_overlapping_leaves(user_id: int, start_date: datetime.date, end_date: datetime.date, exclude_id: int | None = None) -> None:
    """Ensure employee has no overlapping active leave applications (BR-EL-012)."""
    active_statuses = [
        sm.AWAITING_SUBSTITUTE,
        sm.AWAITING_UNIT_HEAD,
        sm.AWAITING_ESTABLISHMENT,
        sm.AWAITING_SANCTION,
        sm.APPROVED,
        sm.ONGOING,
        sm.CANCEL_REQUESTED,
        sm.EXTENSION_REQUESTED,
        sm.RESUMPTION_SUBMITTED,
    ]
    qs = LeaveRequest.objects.filter(
        user_id=user_id,
        status__in=active_statuses,
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)

    if qs.exists():
        overlap = qs.first()
        raise ConflictError(
            f"Overlapping leave request exists (Leave #{overlap.pk} from {overlap.start_date} to {overlap.end_date}).",
            code="overlapping_leave",
        )


# -- Create & Submit ----------------------------------------------------------

@transaction.atomic
def create_leave_request(
    actor: Any,
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    half: str = "full",
    purpose: str = "",
    substitute_id: int | None = None,
    station_leave_required: bool = False,
    station_leave_address: str = "",
    submit: bool = True,
    is_faculty: bool = False,
) -> LeaveRequest:
    """Create a new leave request (draft or direct submit)."""
    user_id = getattr(actor, "user_id", None)
    if not user_id:
        raise PermissionDeniedError("Valid authenticated user required.", code="user_required")

    category = category.upper()
    if category not in lp.VALID_CATEGORIES:
        raise BadRequestError(f"Invalid leave category '{category}'.", code="invalid_category")

    if end_date < start_date:
        raise BadRequestError("End date cannot precede start date.", code="invalid_dates")

    # Pure domain validation
    validation = lp.validate_application(
        category=category,
        start_date=start_date,
        end_date=end_date,
        half=half,
        is_faculty=is_faculty,
        substitute_id=substitute_id,
        station_leave_required=station_leave_required,
        station_leave_address=station_leave_address,
    )
    if not validation.is_valid:
        raise ConflictError(
            validation.errors[0] if validation.errors else "Leave application validation failed.",
            code="validation_failed",
            details=validation.errors,
        )

    # Overlap check (BR-EL-012)
    _check_overlapping_leaves(user_id, start_date, end_date)

    days_counted = Decimal(str(validation.days_counted))

    # Check balance if submitting
    if submit and category in (lp.CL, lp.RH, lp.EL, lp.COL):
        balance = balance_service.get_or_create_balance(user_id, category, start_date.year)
        if Decimal(str(balance.available)) < days_counted:
            raise ConflictError(
                f"Insufficient {category} balance. Required: {days_counted}, Available: {balance.available}.",
                code="insufficient_balance",
            )

    kind = get_actor_kind(actor)
    initial_status = sm.DRAFT
    if submit:
        # Determine whether substitute is required
        if lp.is_substitute_required(category) and substitute_id:
            resolve_or_raise(sm.DRAFT, sm.AWAITING_SUBSTITUTE, kind)
            initial_status = sm.AWAITING_SUBSTITUTE
        else:
            resolve_or_raise(sm.DRAFT, sm.AWAITING_UNIT_HEAD, kind)
            initial_status = sm.AWAITING_UNIT_HEAD

    req = LeaveRequest.objects.create(
        user_id=user_id,
        category=category,
        status=initial_status,
        request_type="new",
        start_date=start_date,
        end_date=end_date,
        half=half,
        days_counted=days_counted,
        purpose=purpose,
        station_leave_required=station_leave_required,
        station_leave_address=station_leave_address,
        substitute_id=substitute_id,
        submitted_at=timezone.now() if submit else None,
    )

    LeaveTransition.objects.create(
        leave_request=req,
        from_status=sm.DRAFT,
        to_status=initial_status,
        actor_user_id=user_id,
        actor_role=kind,
        reason="Initial application submitted" if submit else "Draft created",
    )

    return req


@transaction.atomic
def submit_draft(actor: Any, request_id: int) -> LeaveRequest:
    """Submit a draft leave request."""
    user_id = getattr(actor, "user_id", None)
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError("Leave request not found.", code="request_not_found")

    if req.user_id != user_id:
        raise PermissionDeniedError("You can only submit your own leave request.", code="not_owner")

    if req.status != sm.DRAFT:
        raise ConflictError(f"Request is already in status '{req.status}'.", code="not_draft")

    _check_overlapping_leaves(user_id, req.start_date, req.end_date, exclude_id=req.pk)

    # Balance check
    if req.category in (lp.CL, lp.RH, lp.EL, lp.COL):
        balance = balance_service.get_or_create_balance(user_id, req.category, req.start_date.year)
        if Decimal(str(balance.available)) < req.days_counted:
            raise ConflictError(
                f"Insufficient {req.category} balance. Required: {req.days_counted}, Available: {balance.available}.",
                code="insufficient_balance",
            )

    kind = get_actor_kind(actor, req)
    if lp.is_substitute_required(req.category) and req.substitute_id:
        target = sm.AWAITING_SUBSTITUTE
    else:
        target = sm.AWAITING_UNIT_HEAD

    resolve_or_raise(req.status, target, kind)

    req.status = target
    req.submitted_at = timezone.now()
    req.save()

    LeaveTransition.objects.create(
        leave_request=req,
        from_status=sm.DRAFT,
        to_status=target,
        actor_user_id=user_id,
        actor_role=kind,
        reason="Draft submitted",
    )
    return req


# -- Substitute Gate ----------------------------------------------------------

@transaction.atomic
def respond_substitute(actor: Any, request_id: int, accept: bool, reason: str = "") -> LeaveRequest:
    """Substitute accepts or declines nomination (BR-EL-015)."""
    user_id = getattr(actor, "user_id", None)
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError("Leave request not found.", code="request_not_found")

    if req.substitute_id != user_id and not getattr(actor, "is_superuser", False):
        raise PermissionDeniedError("Only the nominated substitute may respond.", code="not_substitute")

    if req.status != sm.AWAITING_SUBSTITUTE:
        raise ConflictError(f"Request is not awaiting substitute (current status: {req.status}).", code="invalid_state")

    kind = sm.SUBSTITUTE
    if accept:
        target = sm.AWAITING_UNIT_HEAD
        resolve_or_raise(req.status, target, kind)
        req.substitute_accepted = True
        req.status = target
    else:
        target = sm.DRAFT
        resolve_or_raise(req.status, target, kind)
        req.substitute_accepted = False
        req.status = target

    req.save()

    LeaveTransition.objects.create(
        leave_request=req,
        from_status=sm.AWAITING_SUBSTITUTE,
        to_status=target,
        actor_user_id=user_id,
        actor_role=kind,
        reason=reason or ("Substitute accepted nomination" if accept else "Substitute declined nomination"),
    )
    return req


# -- Unit Head Review / Direct Sanction ----------------------------------------

@transaction.atomic
def review_unit_head(
    actor: Any,
    request_id: int,
    action: str,  # "approve", "reject", "recommend", "not_recommend"
    reason: str = "",
) -> LeaveRequest:
    """Unit Head review: direct sanction for CL/RH (BR-EL-016) or recommendation for others (BR-EL-017)."""
    user_id = getattr(actor, "user_id", None)
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError("Leave request not found.", code="request_not_found")

    if req.status != sm.AWAITING_UNIT_HEAD:
        raise ConflictError(f"Request is not awaiting Unit Head (current status: {req.status}).", code="invalid_state")

    kind = sm.UNIT_HEAD

    if req.category in (lp.CL, lp.RH):
        # Direct approval or rejection
        if action == "approve":
            target = sm.APPROVED
            resolve_or_raise(req.status, target, kind)
            req.status = target
            req.approved_at = timezone.now()
            # Deduct balance
            balance_service.deduct_leave_balance(req.user_id, req.category, req.start_date.year, req.days_counted)
        elif action == "reject":
            if not reason.strip():
                raise ConflictError("A rejection reason is required.", code="reason_required")
            target = sm.REJECTED
            resolve_or_raise(req.status, target, kind)
            req.status = target
        else:
            raise BadRequestError("Action must be 'approve' or 'reject' for CL/RH.", code="invalid_action")
    else:
        # SCL, EL, COL, VL: recommendation path
        if action not in ("recommend", "not_recommend"):
            raise BadRequestError("Action must be 'recommend' or 'not_recommend' for this category.", code="invalid_action")

        req.unit_head_recommendation = "recommended" if action == "recommend" else "not_recommended"
        target = sm.AWAITING_SANCTION
        resolve_or_raise(req.status, target, kind)
        req.status = target

    req.save()

    LeaveTransition.objects.create(
        leave_request=req,
        from_status=sm.AWAITING_UNIT_HEAD,
        to_status=target,
        actor_user_id=user_id,
        actor_role=kind,
        recommendation=req.unit_head_recommendation,
        reason=reason,
    )
    return req


# -- Sanctioning Authority Decision -------------------------------------------

@transaction.atomic
def sanction_leave(
    actor: Any,
    request_id: int,
    approve: bool,
    reason: str = "",
) -> LeaveRequest:
    """Final sanction decision (BR-EL-018)."""
    user_id = getattr(actor, "user_id", None)
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError("Leave request not found.", code="request_not_found")

    if req.status != sm.AWAITING_SANCTION:
        raise ConflictError(f"Request is not awaiting sanction (current status: {req.status}).", code="invalid_state")

    kind = sm.SANCTION_AUTH
    if approve:
        target = sm.APPROVED
        resolve_or_raise(req.status, target, kind)
        req.status = target
        req.approved_at = timezone.now()
        # Deduct balance
        balance_service.deduct_leave_balance(req.user_id, req.category, req.start_date.year, req.days_counted)
    else:
        if not reason.strip():
            raise ConflictError("A rejection reason is required.", code="reason_required")
        target = sm.REJECTED
        resolve_or_raise(req.status, target, kind)
        req.status = target

    req.save()

    LeaveTransition.objects.create(
        leave_request=req,
        from_status=sm.AWAITING_SANCTION,
        to_status=target,
        actor_user_id=user_id,
        actor_role=kind,
        reason=reason or ("Approved by sanctioning authority" if approve else "Rejected"),
    )
    return req


# -- Withdrawal ---------------------------------------------------------------

@transaction.atomic
def withdraw_leave(actor: Any, request_id: int, reason: str = "") -> LeaveRequest:
    """Withdraw an in-flight leave request prior to approval (BR-EL-022)."""
    user_id = getattr(actor, "user_id", None)
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError("Leave request not found.", code="request_not_found")

    if req.user_id != user_id:
        raise PermissionDeniedError("You can only withdraw your own leave request.", code="not_owner")

    kind = sm.EMPLOYEE
    target = sm.WITHDRAWN
    resolve_or_raise(req.status, target, kind)

    prev_status = req.status
    req.status = target
    req.save()

    LeaveTransition.objects.create(
        leave_request=req,
        from_status=prev_status,
        to_status=target,
        actor_user_id=user_id,
        actor_role=kind,
        reason=reason or "Withdrawn by employee",
    )
    return req


# -- Cancellation of Approved Leave (CW-EL-02) -------------------------------

@transaction.atomic
def request_cancellation(actor: Any, request_id: int, reason: str = "") -> LeaveRequest:
    """Request cancellation of approved leave before start date (CW-EL-02, BR-EL-023)."""
    user_id = getattr(actor, "user_id", None)
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError("Leave request not found.", code="request_not_found")

    if req.user_id != user_id:
        raise PermissionDeniedError("You can only cancel your own leave.", code="not_owner")

    if req.status != sm.APPROVED:
        raise ConflictError(f"Only approved leave can be cancelled (current status: {req.status}).", code="invalid_state")

    today = timezone.localdate() if hasattr(timezone, "localdate") else datetime.date.today()
    if req.start_date <= today:
        raise ConflictError("Leave cannot be cancelled after or on start date.", code="already_started")

    kind = sm.EMPLOYEE
    target = sm.CANCEL_REQUESTED
    resolve_or_raise(req.status, target, kind)

    req.status = target
    req.save()

    LeaveTransition.objects.create(
        leave_request=req,
        from_status=sm.APPROVED,
        to_status=target,
        actor_user_id=user_id,
        actor_role=kind,
        reason=reason or "Cancellation requested by employee",
    )
    return req


@transaction.atomic
def decide_cancellation(
    actor: Any,
    request_id: int,
    approve: bool,
    reason: str = "",
) -> LeaveRequest:
    """Sanctioning authority / Unit Head decides cancellation request (CW-EL-02)."""
    user_id = getattr(actor, "user_id", None)
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError("Leave request not found.", code="request_not_found")

    if req.status != sm.CANCEL_REQUESTED:
        raise ConflictError(f"Request is not awaiting cancellation review (status: {req.status}).", code="invalid_state")

    kind = sm.SANCTION_AUTH
    if approve:
        target = sm.CANCELLED
        resolve_or_raise(req.status, target, kind)
        req.status = target
        # Refund days back to balance!
        balance_service.refund_leave_balance(req.user_id, req.category, req.start_date.year, req.days_counted)
    else:
        if not reason.strip():
            raise ConflictError("Reason is required to reject cancellation.", code="reason_required")
        target = sm.APPROVED
        resolve_or_raise(req.status, target, kind)
        req.status = target

    req.save()

    LeaveTransition.objects.create(
        leave_request=req,
        from_status=sm.CANCEL_REQUESTED,
        to_status=target,
        actor_user_id=user_id,
        actor_role=kind,
        reason=reason or ("Cancellation approved, balance refunded" if approve else "Cancellation rejected"),
    )
    return req


# -- Extension of Ongoing Leave (CW-EL-03) -----------------------------------

@transaction.atomic
def request_extension(
    actor: Any,
    request_id: int,
    new_end_date: datetime.date,
    reason: str = "",
) -> LeaveRequest:
    """Request extension of ongoing EL/COL/VL leave (CW-EL-03, BR-EL-025)."""
    user_id = getattr(actor, "user_id", None)
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError("Leave request not found.", code="request_not_found")

    if req.user_id != user_id:
        raise PermissionDeniedError("You can only extend your own leave.", code="not_owner")

    if not lp.is_extendable(req.category):
        raise ConflictError(f"Leave category {req.category} cannot be extended.", code="not_extendable")

    if new_end_date <= req.end_date:
        raise BadRequestError("New end date must be after current end date.", code="invalid_dates")

    # Extension start date is the day after current end_date
    ext_start = req.end_date + datetime.timedelta(days=1)
    extra_days = Decimal(str(lp.count_leave_days(start=ext_start, end=new_end_date, category=req.category)))

    # Balance check for additional days
    balance = balance_service.get_or_create_balance(user_id, req.category, req.start_date.year)
    if Decimal(str(balance.available)) < extra_days:
        raise ConflictError(
            f"Insufficient balance for extension. Required: {extra_days}, Available: {balance.available}.",
            code="insufficient_balance",
        )

    kind = sm.EMPLOYEE
    target = sm.EXTENSION_REQUESTED
    # Note: if currently APPROVED and ongoing date, transition from ONGOING
    current_status = sm.ONGOING if req.status in (sm.APPROVED, sm.ONGOING) else req.status
    resolve_or_raise(current_status, target, kind)

    req.status = target
    req.save()

    LeaveTransition.objects.create(
        leave_request=req,
        from_status=current_status,
        to_status=target,
        actor_user_id=user_id,
        actor_role=kind,
        reason=f"Extension requested until {new_end_date} (+{extra_days} days). {reason}".strip(),
    )
    return req


@transaction.atomic
def decide_extension(
    actor: Any,
    request_id: int,
    approve: bool,
    new_end_date: datetime.date | None = None,
    reason: str = "",
) -> LeaveRequest:
    """Sanction authority decides extension request (CW-EL-03)."""
    user_id = getattr(actor, "user_id", None)
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError("Leave request not found.", code="request_not_found")

    if req.status != sm.EXTENSION_REQUESTED:
        raise ConflictError(f"Request is not awaiting extension decision (status: {req.status}).", code="invalid_state")

    kind = sm.SANCTION_AUTH
    if approve:
        target = sm.EXTENSION_APPROVED
        resolve_or_raise(req.status, target, kind)
        if new_end_date and new_end_date > req.end_date:
            ext_start = req.end_date + datetime.timedelta(days=1)
            extra_days = Decimal(str(lp.count_leave_days(start=ext_start, end=new_end_date, category=req.category)))
            req.end_date = new_end_date
            req.days_counted += extra_days
            balance_service.deduct_leave_balance(req.user_id, req.category, req.start_date.year, extra_days)
        req.status = target
    else:
        if not reason.strip():
            raise ConflictError("Reason is required to reject extension.", code="reason_required")
        target = sm.ONGOING
        resolve_or_raise(req.status, target, kind)
        req.status = target

    req.save()

    LeaveTransition.objects.create(
        leave_request=req,
        from_status=sm.EXTENSION_REQUESTED,
        to_status=target,
        actor_user_id=user_id,
        actor_role=kind,
        reason=reason or ("Extension approved" if approve else "Extension rejected"),
    )
    return req


# -- Duty Resumption / Early Return (CW-EL-04) --------------------------------

@transaction.atomic
def submit_resumption(
    actor: Any,
    request_id: int,
    resumption_date: datetime.date,
    reason: str = "",
) -> LeaveRequest:
    """Submit duty resumption report (CW-EL-04, BR-EL-027)."""
    user_id = getattr(actor, "user_id", None)
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError("Leave request not found.", code="request_not_found")

    if req.user_id != user_id:
        raise PermissionDeniedError("You can only submit resumption for your own leave.", code="not_owner")

    if not lp.is_resumable(req.category):
        raise ConflictError(f"Resumption report not required for category {req.category}.", code="not_resumable")

    kind = sm.EMPLOYEE
    target = sm.RESUMPTION_SUBMITTED
    current_status = sm.ONGOING if req.status in (sm.APPROVED, sm.ONGOING, sm.EXTENSION_APPROVED) else req.status
    resolve_or_raise(current_status, target, kind)

    req.status = target
    req.actual_resumption_date = resumption_date
    req.save()

    LeaveTransition.objects.create(
        leave_request=req,
        from_status=current_status,
        to_status=target,
        actor_user_id=user_id,
        actor_role=kind,
        reason=f"Duty resumption submitted on {resumption_date}. {reason}".strip(),
    )
    return req


@transaction.atomic
def review_resumption(
    actor: Any,
    request_id: int,
    reason: str = "",
) -> LeaveRequest:
    """Sanctioning authority verifies resumption and adjusts balance for early return (BR-EL-028)."""
    user_id = getattr(actor, "user_id", None)
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError("Leave request not found.", code="request_not_found")

    if req.status != sm.RESUMPTION_SUBMITTED:
        raise ConflictError(f"Request is not awaiting resumption review (status: {req.status}).", code="invalid_state")

    kind = sm.SANCTION_AUTH
    target = sm.RESUMPTION_REVIEWED
    resolve_or_raise(req.status, target, kind)

    # Check if resumption is early (before original end_date)
    if req.actual_resumption_date and req.actual_resumption_date <= req.end_date:
        # Effective end date of leave is the day before resumption
        effective_end = req.actual_resumption_date - datetime.timedelta(days=1)
        if effective_end >= req.start_date:
            actual_days = Decimal(str(lp.count_leave_days(start=req.start_date, end=effective_end, category=req.category, half=req.half)))
            unused_days = req.days_counted - actual_days
            if unused_days > Decimal("0.0"):
                req.days_counted = actual_days
                req.end_date = effective_end
                balance_service.refund_leave_balance(req.user_id, req.category, req.start_date.year, unused_days)

    req.status = target
    req.save()

    LeaveTransition.objects.create(
        leave_request=req,
        from_status=sm.RESUMPTION_SUBMITTED,
        to_status=target,
        actor_user_id=user_id,
        actor_role=kind,
        reason=reason or "Resumption verified and leave record finalized",
    )
    return req


# -- Offline Leave Recording (BR-EL-029) --------------------------------------

@transaction.atomic
def record_offline_leave(
    actor: Any,
    target_user_id: int,
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    offline_reference: str,
    purpose: str = "",
    half: str = "full",
) -> LeaveRequest:
    """Record leave sanctioned offline (BR-EL-029). Admin action."""
    actor_user_id = getattr(actor, "user_id", None)
    category = category.upper()

    if not offline_reference.strip():
        raise BadRequestError("Offline sanction reference/dispatch number is required.", code="reference_required")

    days_counted = Decimal(str(lp.count_leave_days(start=start_date, end=end_date, category=category, half=half)))

    # Deduct balance
    balance_service.deduct_leave_balance(target_user_id, category, start_date.year, days_counted)

    req = LeaveRequest.objects.create(
        user_id=target_user_id,
        category=category,
        status=sm.APPROVED,
        request_type="offline",
        start_date=start_date,
        end_date=end_date,
        half=half,
        days_counted=days_counted,
        purpose=purpose,
        offline_sanction_reference=offline_reference,
        approved_at=timezone.now(),
    )

    LeaveTransition.objects.create(
        leave_request=req,
        from_status=sm.DRAFT,
        to_status=sm.APPROVED,
        actor_user_id=actor_user_id,
        actor_role="admin",
        reason=f"Offline sanction recorded: {offline_reference}",
    )
    return req
