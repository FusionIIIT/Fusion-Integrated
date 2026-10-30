"""Leave domain write operations and workflow services."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain.constants import (
    ALL_LEAVE_CATEGORIES,
    DECISION_APPROVE,
    DECISION_NOT_RECOMMEND,
    DECISION_RECOMMEND,
    DECISION_REJECT,
    DEFAULT_ENTITLEMENTS,
    HALF_DAY_FULL,
    LEAVE_CL,
    LEAVE_COL,
    LEAVE_EL,
    LEAVE_RH,
    LEAVE_SCL,
    LEAVE_VL,
    STATUS_APPROVED,
    STATUS_AWAITING_DIRECTOR_SELF_SANCTION,
    STATUS_AWAITING_FINAL_SANCTION,
    STATUS_AWAITING_SUBSTITUTE,
    STATUS_AWAITING_UNIT_HEAD,
    STATUS_CANCELLATION_PENDING,
    STATUS_CANCELLED,
    STATUS_CLOSED,
    STATUS_REJECTED,
    STATUS_WITHDRAWN,
    SUBSTITUTE_ACCEPTED,
    SUBSTITUTE_DECLINED,
    SUBSTITUTE_NOT_REQUIRED,
    SUBSTITUTE_PENDING,
)
from modules.leave.domain.rules import (
    LeaveValidationError,
    calculate_early_resumption_restoration,
    calculate_leave_days,
    can_cancel_approved,
    can_extend,
    can_modify_pending,
    can_resume,
    can_withdraw_pending,
    check_non_overlap,
    convert_vl_to_el,
)
from modules.leave.models import HolidayCalendar, LeaveBalance, LeaveRequest


def ensure_user_balances(user_id: int, kind: str = "staff", year: int = 2026) -> None:
    """Initialize annual entitlements for a user if they do not yet exist."""
    entitlements = DEFAULT_ENTITLEMENTS.get(kind, DEFAULT_ENTITLEMENTS["staff"])
    for cat, days in entitlements.items():
        LeaveBalance.objects.get_or_create(
            user_id=user_id,
            year=year,
            category=cat,
            defaults={"credited": Decimal(str(days)), "balance": Decimal(str(days))},
        )


def _get_calendar_data(year: int):
    closed = set(
        HolidayCalendar.objects.filter(year=year, is_closed_holiday=True).values_list(
            "date", flat=True
        )
    )
    restricted = set(
        HolidayCalendar.objects.filter(year=year, is_restricted_holiday=True).values_list(
            "date", flat=True
        )
    )
    vacation = set(
        HolidayCalendar.objects.filter(year=year, is_vacation_period=True).values_list(
            "date", flat=True
        )
    )
    return closed, restricted, vacation


@transaction.atomic
def apply_leave(
    user_id: int,
    category: str,
    start_date: date,
    end_date: date,
    purpose: str,
    half_day: str = HALF_DAY_FULL,
    substitute_user_id: int | None = None,
    station_leave: bool = False,
    station_start_date: date | None = None,
    station_end_date: date | None = None,
    station_address: str = "",
    station_contact: str = "",
    is_director: bool = False,
    year: int = 2026,
) -> LeaveRequest:
    """Create and submit a new leave request following WF-EL-01."""
    if category not in ALL_LEAVE_CATEGORIES:
        raise ConflictError(f"Invalid leave category: {category}")

    # Station leave validation (BR-EL-013)
    if station_leave:
        if not station_start_date or not station_end_date:
            raise ConflictError("Station leave requires both departure and return dates.")
        if station_start_date > station_end_date:
            raise ConflictError("Station leave departure date cannot be after return date.")
        if station_start_date > start_date or station_end_date < end_date:
            raise ConflictError("Station leave period must cover the entire leave interval.")
        if not station_address.strip() or not station_contact.strip():
            raise ConflictError("Station leave requires outstation contact address and emergency contact phone.")

    ensure_user_balances(user_id, kind="faculty" if category == LEAVE_VL else "staff", year=year)
    closed, restricted, vacation = _get_calendar_data(start_date.year)

    try:
        requested_days = calculate_leave_days(
            category=category,
            start_date=start_date,
            end_date=end_date,
            half_day=half_day,
            closed_holidays=closed,
            restricted_holidays=restricted,
            vacation_dates=vacation,
        )
    except LeaveValidationError as exc:
        raise ConflictError(str(exc)) from exc

    # Balance validation (SRS-EL-007)
    balance_obj = LeaveBalance.objects.filter(
        user_id=user_id, year=year, category=category
    ).first()
    if not balance_obj or balance_obj.balance < requested_days:
        avail = balance_obj.balance if balance_obj else Decimal("0.0")
        raise ConflictError(
            f"Insufficient {category} balance. Available: {avail}, Requested: {requested_days}"
        )

    # Overlap validation (BR-EL-012, BR-EL-034)
    existing = list(
        LeaveRequest.objects.filter(user_id=user_id).values("id", "start_date", "end_date", "half_day", "status")
    )
    try:
        check_non_overlap(existing, start_date, end_date, half_day)
    except LeaveValidationError as exc:
        raise ConflictError(str(exc)) from exc

    # Substitute validation (BR-EL-014, BR-EL-015)
    sub_status = SUBSTITUTE_NOT_REQUIRED
    initial_status = STATUS_AWAITING_UNIT_HEAD

    if substitute_user_id:
        if substitute_user_id == user_id:
            raise ConflictError("Applicant cannot be nominated as their own substitute.")
        sub_leaves = list(
            LeaveRequest.objects.filter(user_id=substitute_user_id).values(
                "id", "start_date", "end_date", "half_day", "status"
            )
        )
        try:
            check_non_overlap(sub_leaves, start_date, end_date, half_day)
        except LeaveValidationError as exc:
            raise ConflictError(f"Nominated substitute is unavailable: {exc}") from exc
        sub_status = SUBSTITUTE_PENDING
        initial_status = STATUS_AWAITING_SUBSTITUTE
    elif is_director:
        initial_status = STATUS_AWAITING_DIRECTOR_SELF_SANCTION

    req = LeaveRequest.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        requested_days=requested_days,
        purpose=purpose,
        status=initial_status,
        substitute_user_id=substitute_user_id,
        substitute_status=sub_status,
        station_leave=station_leave,
        station_start_date=station_start_date,
        station_end_date=station_end_date,
        station_address=station_address,
        station_contact=station_contact,
    )
    return req


@transaction.atomic
def respond_substitute(
    request_id: int, substitute_user_id: int, accept: bool, remarks: str = "", is_director: bool = False
) -> LeaveRequest:
    """Substitute accepts or declines responsibility (BR-EL-015, WF-EL-01)."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError("Leave request not found.")
    if req.substitute_user_id != substitute_user_id:
        raise PermissionDeniedError("You are not the nominated substitute for this request.")
    if req.status != STATUS_AWAITING_SUBSTITUTE:
        raise ConflictError("This request is not awaiting substitute response.")

    req.substitute_remarks = remarks
    if accept:
        req.substitute_status = SUBSTITUTE_ACCEPTED
        req.status = (
            STATUS_AWAITING_DIRECTOR_SELF_SANCTION if is_director else STATUS_AWAITING_UNIT_HEAD
        )
    else:
        req.substitute_status = SUBSTITUTE_DECLINED
        # Leaves the request blocked at substitute stage until applicant nominates another or withdraws
    req.save()
    return req


@transaction.atomic
def review_unit_head(
    request_id: int, reviewer_user_id: int, decision: str, remarks: str = ""
) -> LeaveRequest:
    """Unit Head review. Final sanction for CL/RH; recommendation for SCL/EL/COL/VL (BR-EL-016, BR-EL-017)."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError("Leave request not found.")
    if req.status != STATUS_AWAITING_UNIT_HEAD:
        raise ConflictError("Request is not awaiting Unit Head review.")

    req.unit_head_user_id = reviewer_user_id
    req.unit_head_decision = decision
    req.unit_head_remarks = remarks

    # CL and RH final sanction by Unit Head (BR-EL-016)
    if req.category in (LEAVE_CL, LEAVE_RH):
        if decision == DECISION_APPROVE:
            req.status = STATUS_APPROVED
            _deduct_leave_balance(req.user_id, req.start_date.year, req.category, req.requested_days)
        else:
            req.status = STATUS_REJECTED
    else:
        # SCL, EL, COL, VL advance to higher sanction (BR-EL-017, BR-EL-018)
        # Unit Head cannot make the final rejection decision for these categories
        if decision == DECISION_REJECT:
            raise ConflictError(
                "Unit Head cannot reject SCL, EL, COL, or VL directly; they may only recommend or not recommend."
            )
        req.status = STATUS_AWAITING_FINAL_SANCTION

    req.save()
    return req


@transaction.atomic
def sanction_final(
    request_id: int, authority_user_id: int, decision: str, remarks: str = ""
) -> LeaveRequest:
    """Final sanction decision for higher-sanction leave or Director self-sanction (BR-EL-018, BR-EL-020)."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError("Leave request not found.")
    if req.status not in (STATUS_AWAITING_FINAL_SANCTION, STATUS_AWAITING_DIRECTOR_SELF_SANCTION):
        raise ConflictError("Request is not awaiting final sanction.")

    req.sanctioning_authority_user_id = authority_user_id
    req.sanctioning_decision = decision
    req.sanctioning_remarks = remarks

    if decision == DECISION_APPROVE:
        req.status = STATUS_APPROVED
        _deduct_leave_balance(req.user_id, req.start_date.year, req.category, req.requested_days)
    else:
        req.status = STATUS_REJECTED

    req.save()
    return req


@transaction.atomic
def modify_pending_request(
    request_id: int,
    user_id: int,
    start_date: date,
    end_date: date,
    purpose: str,
    half_day: str = HALF_DAY_FULL,
    substitute_user_id: int | None = None,
) -> LeaveRequest:
    """Modify a pending leave request before final approval (BR-EL-021, WF-EL-02)."""
    req = LeaveRequest.objects.filter(pk=request_id, user_id=user_id).first()
    if not req:
        raise NotFoundError("Pending leave request not found.")
    if not can_modify_pending(req.status):
        raise ConflictError("This request cannot be modified in its current state.")

    closed, restricted, vacation = _get_calendar_data(start_date.year)
    try:
        new_days = calculate_leave_days(
            category=req.category,
            start_date=start_date,
            end_date=end_date,
            half_day=half_day,
            closed_holidays=closed,
            restricted_holidays=restricted,
            vacation_dates=vacation,
        )
    except LeaveValidationError as exc:
        raise ConflictError(str(exc)) from exc

    existing = list(
        LeaveRequest.objects.filter(user_id=user_id).values("id", "start_date", "end_date", "half_day", "status")
    )
    try:
        check_non_overlap(existing, start_date, end_date, half_day, exclude_request_id=req.pk)
    except LeaveValidationError as exc:
        raise ConflictError(str(exc)) from exc

    req.start_date = start_date
    req.end_date = end_date
    req.half_day = half_day
    req.requested_days = new_days
    req.purpose = purpose

    # Reset substitute consent if substitute changed or dates modified
    if substitute_user_id:
        req.substitute_user_id = substitute_user_id
        req.substitute_status = SUBSTITUTE_PENDING
        req.status = STATUS_AWAITING_SUBSTITUTE
    else:
        req.status = STATUS_AWAITING_UNIT_HEAD

    req.save()
    return req


@transaction.atomic
def withdraw_pending_request(request_id: int, user_id: int) -> LeaveRequest:
    """Immediately withdraw a pending request before final approval (BR-EL-022, WF-EL-02)."""
    req = LeaveRequest.objects.filter(pk=request_id, user_id=user_id).first()
    if not req:
        raise NotFoundError("Leave request not found.")
    if not can_withdraw_pending(req.status):
        raise ConflictError("Request cannot be withdrawn after final approval or once terminal.")

    req.status = STATUS_WITHDRAWN
    req.save()
    return req


@transaction.atomic
def request_cancellation(request_id: int, user_id: int) -> LeaveRequest:
    """Request cancellation of an approved leave before it begins (BR-EL-023, WF-EL-03)."""
    req = LeaveRequest.objects.filter(pk=request_id, user_id=user_id).first()
    if not req:
        raise NotFoundError("Approved leave request not found.")
    if not can_cancel_approved(req.status, req.start_date, date.today()):
        raise ConflictError("Leave can only be cancelled before its approved start date.")

    req.status = STATUS_CANCELLATION_PENDING
    req.save()
    return req


@transaction.atomic
def decide_cancellation(request_id: int, reviewer_user_id: int, approve: bool) -> LeaveRequest:
    """Decide on a cancellation request (BR-EL-023)."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError("Leave request not found.")
    if req.status != STATUS_CANCELLATION_PENDING:
        raise ConflictError("Request is not awaiting cancellation review.")

    if approve:
        req.status = STATUS_CANCELLED
        _restore_leave_balance(req.user_id, req.start_date.year, req.category, req.requested_days)
    else:
        req.status = STATUS_APPROVED
    req.save()
    return req


@transaction.atomic
def submit_extension(
    parent_leave_id: int,
    user_id: int,
    extension_start: date,
    extension_end: date,
    purpose: str,
    substitute_user_id: int | None = None,
) -> LeaveRequest:
    """Submit an incremental extension to ongoing EL/COL/VL (BR-EL-025, WF-EL-04)."""
    parent = LeaveRequest.objects.filter(pk=parent_leave_id, user_id=user_id).first()
    if not parent:
        raise NotFoundError("Parent leave not found.")
    if not can_extend(parent.category, parent.status):
        raise ConflictError("Extensions are only allowed for ongoing EL, COL, or VL.")
    if extension_start <= parent.end_date:
        raise ConflictError(
            f"Extension start date must be strictly after parent leave end date ({parent.end_date})."
        )

    ext_req = apply_leave(
        user_id=user_id,
        category=parent.category,
        start_date=extension_start,
        end_date=extension_end,
        purpose=purpose,
        substitute_user_id=substitute_user_id,
        year=extension_start.year,
    )
    ext_req.parent_leave_id = parent.pk
    ext_req.save()
    return ext_req


@transaction.atomic
def submit_resumption(request_id: int, user_id: int, actual_date: date) -> LeaveRequest:
    """Submit resumption of duty after EL/COL/VL (BR-EL-027, WF-EL-05)."""
    req = LeaveRequest.objects.filter(pk=request_id, user_id=user_id).first()
    if not req:
        raise NotFoundError("Leave request not found.")
    if not can_resume(req.category, req.status):
        raise ConflictError("Duty resumption is only applicable to approved EL, COL, or VL.")

    req.actual_resumption_date = actual_date
    req.save()
    return req


@transaction.atomic
def verify_resumption(request_id: int, verifier_user_id: int) -> LeaveRequest:
    """Verify duty resumption and restore unused leave if returning early (BR-EL-028, WF-EL-05)."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req or not req.actual_resumption_date:
        raise ConflictError("Resumption of duty has not been submitted for this leave.")

    closed, _, _ = _get_calendar_data(req.start_date.year)
    restoration = calculate_early_resumption_restoration(
        category=req.category,
        approved_start=req.start_date,
        approved_end=req.end_date,
        actual_resumption_date=req.actual_resumption_date,
        closed_holidays=closed,
    )

    if restoration > Decimal("0.0"):
        _restore_leave_balance(req.user_id, req.start_date.year, req.category, restoration)
        req.restored_days = restoration

    req.resumption_verified = True
    req.status = STATUS_CLOSED
    req.save()
    return req


@transaction.atomic
def record_offline_leave(
    user_id: int,
    category: str,
    start_date: date,
    end_date: date,
    purpose: str,
    offline_reference: str,
    year: int = 2026,
) -> LeaveRequest:
    """Record leave already sanctioned offline for record synchronization (BR-EL-029)."""
    ensure_user_balances(user_id, year=year)
    closed, _, _ = _get_calendar_data(start_date.year)
    days = calculate_leave_days(
        category=category,
        start_date=start_date,
        end_date=end_date,
        half_day=HALF_DAY_FULL,
        closed_holidays=closed,
    )
    _deduct_leave_balance(user_id, year, category, days)

    return LeaveRequest.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        requested_days=days,
        purpose=purpose,
        status=STATUS_APPROVED,
        is_offline=True,
        offline_reference=offline_reference,
    )


@transaction.atomic
def process_year_end(year: int) -> None:
    """Execute scheduled year-end processing: lapse CL/RH/SCL, convert faculty VL to EL (BR-EL-002..007, WF-EL-07)."""
    # 1. Lapse CL, RH, SCL
    for bal in LeaveBalance.objects.filter(year=year, category__in=[LEAVE_CL, LEAVE_RH, LEAVE_SCL]):
        if bal.balance > Decimal("0.0"):
            bal.lapsed = bal.balance
            bal.balance = Decimal("0.0")
            bal.save()

    # 2. Convert faculty unused VL to EL at 2:1 ratio (BR-EL-007)
    vl_balances = LeaveBalance.objects.filter(year=year, category=LEAVE_VL)
    for vl_bal in vl_balances:
        if vl_bal.balance > Decimal("0.0"):
            converted_el = convert_vl_to_el(vl_bal.balance)
            vl_bal.lapsed = vl_bal.balance
            vl_bal.balance = Decimal("0.0")
            vl_bal.save()

            if converted_el > Decimal("0.0"):
                el_bal, _ = LeaveBalance.objects.get_or_create(
                    user_id=vl_bal.user_id,
                    year=year,
                    category=LEAVE_EL,
                    defaults={"credited": Decimal("0.0"), "balance": Decimal("0.0")},
                )
                el_bal.credited += converted_el
                el_bal.balance += converted_el
                el_bal.save()

    # 3. Carry forward EL and COL balances to next calendar year (BR-EL-005, BR-EL-008, BR-EL-009)
    next_year = year + 1
    for bal in LeaveBalance.objects.filter(year=year, category__in=[LEAVE_EL, LEAVE_COL]):
        if bal.balance > Decimal("0.0"):
            next_bal, created = LeaveBalance.objects.get_or_create(
                user_id=bal.user_id,
                year=next_year,
                category=bal.category,
                defaults={"credited": bal.balance, "balance": bal.balance},
            )
            if not created:
                next_bal.balance += bal.balance
                next_bal.save()


def _deduct_leave_balance(user_id: int, year: int, category: str, days: Decimal) -> None:
    bal = LeaveBalance.objects.filter(user_id=user_id, year=year, category=category).first()
    if bal:
        bal.availed += days
        bal.balance = max(Decimal("0.0"), bal.balance - days)
        bal.save()


def _restore_leave_balance(user_id: int, year: int, category: str, days: Decimal) -> None:
    bal = LeaveBalance.objects.filter(user_id=user_id, year=year, category=category).first()
    if bal:
        bal.availed = max(Decimal("0.0"), bal.availed - days)
        bal.balance += days
        bal.save()
