
"""Transactional services for employee leave requests."""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
)
from modules.leave.domain.constants import (
    CL,
    RH,
    SCL,
    EL,
    VL,
    COL,
    DRAFT,
    AWAITING_SUBSTITUTE,
    APPLICANT_ACTION_REQUIRED,
    AWAITING_UNIT_HEAD,
    AWAITING_DIRECTOR_SANCTION,
    APPROVED,
    REJECTED,
    WITHDRAWN,
    EXTENSION_AWAITING_SUBSTITUTE,
    EXTENSION_APPLICANT_ACTION_REQUIRED,
    EXTENSION_AWAITING_UNIT_HEAD,
)
from modules.leave.domain.calculations import calculate_chargeable_days
from modules.leave.domain.state_machine import (
    get_next_state,
    TransitionException,
    ACTION_SUBMIT,
    ACTION_SUBMIT_WITH_SUBSTITUTE,
    ACTION_SUBMIT_DIRECTOR,
    ACTION_SUBSTITUTE_ACCEPT,
    ACTION_SUBSTITUTE_ACCEPT_DIRECTOR,
    ACTION_SUBSTITUTE_DECLINE,
    ACTION_NOMINATE_REPLACEMENT,
    ACTION_WITHDRAW,
    ACTOR_EMPLOYEE,
    ACTOR_SUBSTITUTE,
    ACTOR_UNIT_HEAD,
    ACTOR_ESTABLISHMENT,
    ACTOR_SANCTIONING_AUTHORITY,
    ACTOR_DIRECTOR,
    ACTOR_LEAVE_ADMIN,
    ACTOR_SYSTEM,
)
from modules.leave.models.requests import (
    LeaveRequest,
    LeaveRequestTransition,
)
from modules.leave.models.ledger import (
    LeaveBalanceLedger,
    LeaveLedgerTransaction,
)
from modules.leave.models.policy import HolidayCalendar


LEAVE_CATEGORIES = {CL, RH, SCL, EL, VL, COL}
NON_CONTINUOUS_CATEGORIES = {CL, RH, SCL}
CONTINUOUS_CATEGORIES = {EL, COL, VL}


def _actor_kind(actor):
    if actor is None:
        return ACTOR_SYSTEM

    user = getattr(actor, "user", None)
    kind = getattr(actor, "kind", None)

    if kind is None and user is not None:
        kind = getattr(user, "kind", None)

    return kind or ACTOR_EMPLOYEE


def _actor_user_id(actor):
    if actor is None:
        return None

    user_id = getattr(actor, "user_id", None)
    if user_id is not None:
        return user_id

    user = getattr(actor, "user", None)
    return getattr(user, "pk", None) if user is not None else None


def _ledger_for_request(request, *, lock=True):
    qs = LeaveBalanceLedger.objects.filter(
        user_id=request.user_id,
        category=request.category,
        year=request.start_date.year,
    )
    if lock:
        qs = qs.select_for_update()
    return qs.first()


def _record_ledger_change(
    *,
    request,
    delta,
    transaction_type,
    remarks,
):
    """Record a signed ledger transaction and update utilization atomically."""
    delta = Decimal(str(delta))
    ledger = _ledger_for_request(request)

    if ledger is None:
        raise ConflictError(
            "No leave balance ledger exists for the request's category and year."
        )

    # A positive deduction increases utilization; a negative reversal reduces it.
    ledger.utilized += delta
    if ledger.utilized < 0:
        raise ConflictError("Ledger utilization cannot become negative.")

    ledger.save(update_fields=["utilized", "updated_at"])

    LeaveLedgerTransaction.objects.create(
        user_id=request.user_id,
        category=request.category,
        delta=delta,
        transaction_type=transaction_type,
        reference_id=str(request.pk),
        remarks=remarks,
    )


@transaction.atomic
def transition(*, request_id: int, action: str, actor, remarks: str = ""):
    """Lock, validate, audit, and apply a leave-request state transition."""
    request = (
        LeaveRequest.objects.select_for_update()
        .filter(pk=request_id)
        .first()
    )
    if request is None:
        raise NotFoundError("No such leave request.")

    actor_kind = _actor_kind(actor)
    current_state = request.status

    try:
        next_state = get_next_state(current_state, action, actor_kind)
    except TransitionException as exc:
        raise ConflictError(str(exc)) from exc

    # Ordinary approval must not deduct a second time: application creation
    # already made the provisional deduction.
    #
    # Withdrawal restores provisional utilization. Other balance adjustments
    # are owned by their dedicated workflows.
    if next_state in {WITHDRAWN}:
        _record_ledger_change(
            request=request,
            delta=-request.chargeable_days,
            transaction_type="reversal",
            remarks=f"Withdrawn: {current_state} -> {next_state}",
        )

    LeaveRequestTransition.objects.create(
        leave_request=request,
        from_status=current_state,
        to_status=next_state,
        actor_user_id=_actor_user_id(actor),
        actor_role=actor_kind,
        remarks=remarks,
    )

    request.status = next_state
    request.save(update_fields=["status", "updated_at"])
    return request


@transaction.atomic
def apply_for_leave(
    *,
    user_id: int,
    category: str,
    start_date,
    end_date,
    purpose: str,
    is_faculty: bool = False,
    half_day_type: str = "none",
    station_leave_required: bool = False,
    station_leave_details=None,
    substitute_user_id=None,
    actor=None,
):
    """Validate, provisionally deduct, and create a leave request."""
    if category not in LEAVE_CATEGORIES:
        raise BadRequestError("Unsupported leave category.")

    if start_date > end_date:
        raise BadRequestError("Start date must not be after end date.")

    if half_day_type not in {"none", "first_half", "second_half"}:
        raise BadRequestError("Invalid half-day selection.")

    if category not in NON_CONTINUOUS_CATEGORIES and half_day_type != "none":
        raise BadRequestError("Half-day leave is not supported for this category.")

    if substitute_user_id == user_id:
        raise BadRequestError("An employee cannot substitute for themselves.")

    holidays = set(
        HolidayCalendar.objects.filter(
            year__gte=start_date.year,
            year__lte=end_date.year,
            is_published=True,
        ).values_list("date", flat=True)
    )
    weekends = {5, 6}

    days = Decimal(str(calculate_chargeable_days(
        category,
        start_date,
        end_date,
        half_day_type,
        holidays,
        weekends,
    )))

    if days <= 0:
        raise BadRequestError("The requested leave has no chargeable days.")

    overlap = LeaveRequest.objects.filter(
        user_id=user_id,
        status__in=[
            DRAFT,
            AWAITING_SUBSTITUTE,
            APPLICANT_ACTION_REQUIRED,
            AWAITING_UNIT_HEAD,
            AWAITING_DIRECTOR_SANCTION,
            APPROVED,
        ],
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).exists()
    if overlap:
        raise ConflictError("The requested dates overlap an existing leave request.")

    ledger = (
        LeaveBalanceLedger.objects.select_for_update()
        .filter(
            user_id=user_id,
            category=category,
            year=start_date.year,
        )
        .first()
    )
    if ledger is None:
        raise ConflictError("No leave balance is configured for this year.")

    if ledger.balance - ledger.utilized < days:
        raise ConflictError("Insufficient leave balance.")

    if substitute_user_id is not None:
        initial_action = ACTION_SUBMIT_WITH_SUBSTITUTE
    elif is_faculty and getattr(actor, "is_director", False):
        initial_action = ACTION_SUBMIT_DIRECTOR
    else:
        initial_action = ACTION_SUBMIT

    actor_kind = _actor_kind(actor)
    try:
        initial_status = get_next_state(DRAFT, initial_action, actor_kind)
    except TransitionException as exc:
        raise ConflictError(str(exc)) from exc

    request = LeaveRequest.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        purpose=purpose,
        half_day_type=half_day_type,
        chargeable_days=days,
        is_faculty=is_faculty,
        station_leave_required=station_leave_required,
        station_leave_details=station_leave_details,
        substitute_user_id=substitute_user_id,
        substitute_status="pending" if substitute_user_id is not None else "none",
        status=initial_status,
    )

    # Provisional deduction at application time.
    _record_ledger_change(
        request=request,
        delta=days,
        transaction_type="deduction",
        remarks="Provisional deduction for leave application.",
    )

    LeaveRequestTransition.objects.create(
        leave_request=request,
        from_status=DRAFT,
        to_status=initial_status,
        actor_user_id=user_id,
        actor_role=actor_kind,
        remarks="Leave application submitted.",
    )

    return request


@transaction.atomic
def respond_substitute(*, request_id: int, actor, accept: bool, remarks: str = ""):
    """Record substitute acceptance or decline."""
    request = (
        LeaveRequest.objects.select_for_update()
        .filter(pk=request_id)
        .first()
    )
    if request is None:
        raise NotFoundError("No such leave request.")

    if _actor_kind(actor) != ACTOR_SUBSTITUTE:
        raise ConflictError("Only the nominated substitute may respond.")

    if request.substitute_user_id != _actor_user_id(actor):
        raise ConflictError("You are not the nominated substitute.")

    if request.status != AWAITING_SUBSTITUTE:
        raise ConflictError("This request is not awaiting a substitute response.")

    action = ACTION_SUBSTITUTE_ACCEPT if accept else ACTION_SUBSTITUTE_DECLINE
    try:
        next_state = get_next_state(request.status, action, ACTOR_SUBSTITUTE)
    except TransitionException as exc:
        raise ConflictError(str(exc)) from exc

    request.status = next_state
    request.substitute_status = "accepted" if accept else "declined"
    request.save(update_fields=["status", "substitute_status", "updated_at"])

    LeaveRequestTransition.objects.create(
        leave_request=request,
        from_status=AWAITING_SUBSTITUTE,
        to_status=next_state,
        actor_user_id=_actor_user_id(actor),
        actor_role=ACTOR_SUBSTITUTE,
        remarks=remarks,
    )
    return request


@transaction.atomic
def nominate_replacement_substitute(
    *,
    request_id: int,
    actor,
    substitute_user_id: int,
    remarks: str = "",
):
    """Nominate a replacement after the previous substitute declines."""
    request = (
        LeaveRequest.objects.select_for_update()
        .filter(pk=request_id)
        .first()
    )
    if request is None:
        raise NotFoundError("No such leave request.")

    if _actor_user_id(actor) != request.user_id:
        raise ConflictError("Only the applicant may nominate a replacement.")

    if substitute_user_id == request.user_id:
        raise BadRequestError("An employee cannot substitute for themselves.")

    if request.status != APPLICANT_ACTION_REQUIRED:
        raise ConflictError("This request does not require a replacement substitute.")

    try:
        next_state = get_next_state(
            request.status,
            ACTION_NOMINATE_REPLACEMENT,
            ACTOR_EMPLOYEE,
        )
    except TransitionException as exc:
        raise ConflictError(str(exc)) from exc

    old_state = request.status
    request.substitute_user_id = substitute_user_id
    request.substitute_status = "pending"
    request.status = next_state
    request.save(update_fields=[
        "substitute_user_id",
        "substitute_status",
        "status",
        "updated_at",
    ])

    LeaveRequestTransition.objects.create(
        leave_request=request,
        from_status=old_state,
        to_status=next_state,
        actor_user_id=_actor_user_id(actor),
        actor_role=ACTOR_EMPLOYEE,
        remarks=remarks,
    )
    return request


@transaction.atomic
def withdraw_request(*, request_id: int, actor, remarks: str = ""):
    """Withdraw a pending leave request and restore its provisional deduction."""
    request = (
        LeaveRequest.objects.select_for_update()
        .filter(pk=request_id)
        .first()
    )
    if request is None:
        raise NotFoundError("No such leave request.")

    if _actor_user_id(actor) != request.user_id:
        raise ConflictError("Only the applicant may withdraw this request.")

    old_state = request.status
    if old_state not in {
        DRAFT,
        AWAITING_SUBSTITUTE,
        APPLICANT_ACTION_REQUIRED,
        AWAITING_UNIT_HEAD,
    }:
        raise ConflictError("This request is not in a withdrawable state.")

    try:
        next_state = get_next_state(
            old_state,
            ACTION_WITHDRAW,
            ACTOR_EMPLOYEE,
        )
    except TransitionException as exc:
        raise ConflictError(str(exc)) from exc

    _record_ledger_change(
        request=request,
        delta=-request.chargeable_days,
        transaction_type="reversal",
        remarks=f"Provisional deduction restored on withdrawal: {remarks}",
    )

    request.status = next_state
    request.save(update_fields=["status", "updated_at"])

    LeaveRequestTransition.objects.create(
        leave_request=request,
        from_status=old_state,
        to_status=next_state,
        actor_user_id=_actor_user_id(actor),
        actor_role=ACTOR_EMPLOYEE,
        remarks=remarks,
    )
    return request
