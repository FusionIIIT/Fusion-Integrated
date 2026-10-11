"""Application service for leave submissions and withdrawals.

Enforces BR-EL-001, BR-EL-002, BR-EL-003, BR-EL-004, BR-EL-005, BR-EL-006, BR-EL-009,
BR-EL-010, BR-EL-011, BR-EL-012, BR-EL-013, BR-EL-014, BR-EL-020, BR-EL-022, BR-EL-034.
"""

from datetime import date

from django.db import transaction

from core.api.exceptions import BadRequestError
from fusion_auth.principal import Principal
from modules.directory.contracts import get_users
from modules.leave.domain.constants import (
    Event,
    HalfDay,
    LeaveCategory,
    RequestStatus,
    SubstituteStatus,
)
from modules.leave.domain.counting import calculate_leave_days
from modules.leave.domain.exceptions import LeaveDomainError
from modules.leave.domain.validation import (
    validate_balance,
    validate_category_eligibility,
    validate_non_overlap,
    validate_rh_dates,
    validate_station_leave,
    validate_substitute,
    validate_vl_dates,
)
from modules.leave.models.requests import LeaveRequest
from modules.leave.models.sla import SlaTaskClock
from modules.leave.selectors.balances import get_category_balance
from modules.leave.selectors.calendar import (
    get_closed_holidays,
    get_published_rh_dates,
    get_vacation_periods,
)
from modules.leave.selectors.requests import (
    get_active_intervals,
    get_request_by_id,
    get_substitute_active_intervals,
)
from modules.leave.services.transitions import _translate_error, execute_transition


def apply_for_leave(
    principal: Principal,
    category: str,
    start_date: date,
    end_date: date,
    purpose: str,
    half_day: str = HalfDay.NONE.value,
    station_leave_applied: bool = False,
    station_details: dict | None = None,
    substitute_user_id: int | None = None,
) -> LeaveRequest:
    """Creates and submits a new leave application (EL-UC-001)."""
    user_id = principal.user_id

    # 1. Fetch user kind & department from directory
    users = get_users([user_id])
    user_dto = users.get(user_id)
    employee_kind = user_dto.kind if user_dto else "staff"
    department = user_dto.department if user_dto else ""

    try:
        # 2. Category eligibility (BR-EL-001)
        validate_category_eligibility(category, employee_kind)

        # 3. Calendar & Holiday Validation (BR-EL-003, BR-EL-006, BR-EL-031)
        year = start_date.year
        closed_holidays = get_closed_holidays(year)
        if category == LeaveCategory.RH:
            published_rh = get_published_rh_dates(year)
            validate_rh_dates([start_date], published_rh)
        elif category == LeaveCategory.VL:
            vac_periods = get_vacation_periods()
            validate_vl_dates(start_date, end_date, vac_periods)

        # 4. Leave day counting (BR-EL-010, BR-EL-011)
        days_count = calculate_leave_days(
            category=category,
            start_date=start_date,
            end_date=end_date,
            half_day=half_day,
            closed_holidays=closed_holidays,
        )

        # 5. Balance check
        available_balance = get_category_balance(user_id, category)
        validate_balance(available_balance, days_count, category)

        # 6. Non-overlap check (BR-EL-012)
        active_intervals = get_active_intervals(user_id)
        validate_non_overlap(start_date, end_date, half_day, active_intervals)

        # 7. Substitute eligibility (BR-EL-014)
        if substitute_user_id:
            sub_intervals = get_substitute_active_intervals(substitute_user_id)
            validate_substitute(user_id, substitute_user_id, sub_intervals, start_date, end_date)

        # 8. Station leave coupling (BR-EL-013)
        validate_station_leave(station_leave_applied, station_details)

    except LeaveDomainError as err:
        raise _translate_error(err) from err

    with transaction.atomic():
        sub_status = (
            SubstituteStatus.PENDING.value
            if substitute_user_id
            else SubstituteStatus.NOT_REQUIRED.value
        )

        req = LeaveRequest.objects.create(
            user_id=user_id,
            category=category,
            start_date=start_date,
            end_date=end_date,
            half_day=half_day,
            days_count=days_count,
            purpose=purpose,
            station_leave_applied=station_leave_applied,
            station_details=station_details or {},
            status=RequestStatus.DRAFT.value,
            substitute_user_id=substitute_user_id,
            substitute_status=sub_status,
            department=department,
        )

        is_director = principal.active_role == "Director"
        context = {
            "needs_substitute": bool(substitute_user_id),
            "is_director": is_director,
        }

        # Transition from DRAFT to next state via choke point
        req = execute_transition(
            request_id=req.id,
            event=Event.SUBMIT,
            actor_user_id=user_id,
            actor_role="applicant",
            remarks="Application submitted by employee",
            context=context,
        )

        # Start SLA clock for pending task if assigned to substitute or unit head
        if req.status == RequestStatus.AWAITING_SUBSTITUTE_RESPONSE:
            SlaTaskClock.objects.create(
                request=req,
                task_type="substitute_response",
                assigned_to_user_id=substitute_user_id,
                assigned_to_role="substitute",
                state=req.status,
            )
        elif req.status == RequestStatus.AWAITING_UNIT_HEAD_REVIEW:
            SlaTaskClock.objects.create(
                request=req,
                task_type="unit_head_review",
                assigned_to_role="Unit Head",
                state=req.status,
            )

        return req


def withdraw_leave_request(request_id: int, principal: Principal) -> LeaveRequest:
    """Withdraws a pending leave request before final approval (EL-UC-007 / BR-EL-022)."""
    req = get_request_by_id(request_id, principal)

    if req.user_id != principal.user_id:
        raise BadRequestError("Only the applicant may withdraw this leave request.")

    # Execute transition via choke point
    req = execute_transition(
        request_id=req.id,
        event=Event.WITHDRAW,
        actor_user_id=principal.user_id,
        actor_role="applicant",
        remarks="Request withdrawn by applicant",
    )

    # Cancel any active SLA clocks
    SlaTaskClock.objects.filter(request=req, is_pending=True).update(is_pending=False)

    return req
