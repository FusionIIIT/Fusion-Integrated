"""Leave application creation and lifecycle services."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.elm.domain.constants import (
    ApplicationStatus,
    LeaveCategory,
    SubstituteStatus,
    TaskType,
)
from modules.elm.domain.counting import calculate_chargeable_days
from modules.elm.domain.state_machine import (
    get_initial_submission_status,
    transition_withdrawal,
)
from modules.elm.domain.validation import (
    validate_balance_sufficient,
    validate_category_eligibility,
    validate_overlap,
    validate_rh_date,
    validate_substitute_eligibility,
    validate_vacation_period,
)
from modules.elm.models import LeaveApplication, LeaveAuditLog, WorkflowTask
from modules.elm.selectors.balances import get_balances_for_user
from modules.elm.selectors.calendars import (
    get_active_vacation_periods,
    get_closed_holidays_set,
    get_restricted_holidays_set,
)
from modules.elm.selectors.config import resolve_hierarchy_for_employee
from modules.elm.selectors.leaves import (
    get_active_or_pending_leaves_for_user,
    get_application_by_id,
    get_substitute_active_leaves,
)
from modules.elm.services.balances import ensure_leave_accounts_for_user


@transaction.atomic
def apply_leave(
    *,
    user_id: int,
    user_kind: str,
    user_roles: tuple[str, ...],
    category: str,
    start_date: date,
    end_date: date,
    purpose: str,
    is_half_day: bool = False,
    half_day_session: str | None = None,
    medical_certificate: str = "",
    # Station leave
    is_station_leave: bool = False,
    station_leave_departure: datetime | None = None,
    station_leave_return: datetime | None = None,
    station_destination: str = "",
    station_address: str = "",
    station_emergency_contact: str = "",
    # Substitute
    requires_substitute: bool = False,
    substitute_user_id: int | None = None,
    user_department: str = "",
    user_designation: str = "",
) -> LeaveApplication:
    """Create and submit a new leave application (CW-EL-01 / EL-UC-001)."""
    # 1. Validate category eligibility (BR-EL-001, BR-EL-006)
    try:
        validate_category_eligibility(category, user_kind)
    except ValueError as e:
        raise BadRequestError(str(e)) from e

    year = start_date.year
    ensure_leave_accounts_for_user(user_id, year, user_kind)

    # 2. Closed holidays for counting
    closed_holidays = get_closed_holidays_set(year)

    # 3. Calculate chargeable days (BR-EL-010, BR-EL-011)
    try:
        chargeable_days = calculate_chargeable_days(
            category,
            start_date,
            end_date,
            is_half_day=is_half_day,
            closed_holidays=closed_holidays,
        )
    except ValueError as e:
        raise BadRequestError(str(e)) from e

    # 4. Check available balance (AFR-EL-003.2)
    balances = get_balances_for_user(user_id, year)
    avail_balance = balances.get(category, Decimal("0.00"))
    try:
        validate_balance_sufficient(avail_balance, chargeable_days, category)
    except ValueError as e:
        raise BadRequestError(str(e)) from e

    # 5. Overlap validation (BR-EL-012)
    existing_leaves = get_active_or_pending_leaves_for_user(user_id)
    try:
        validate_overlap(
            existing_leaves,
            start_date,
            end_date,
            is_half_day=is_half_day,
            half_day_session=half_day_session,
        )
    except ValueError as e:
        raise ConflictError(str(e)) from e

    # 6. Category-specific validations
    if category == LeaveCategory.RH.value:
        # BR-EL-003 / BR-EL-031: Must match published RH date
        published_rhs = get_restricted_holidays_set(year)
        try:
            validate_rh_date(start_date, published_rhs)
        except ValueError as e:
            raise BadRequestError(str(e)) from e

    if category == LeaveCategory.VL.value:
        # BR-EL-006: Must fall within external Academic Calendar vacation periods
        vac_periods = get_active_vacation_periods()
        intervals = [(vp.start_date, vp.end_date) for vp in vac_periods]
        try:
            validate_vacation_period(start_date, end_date, intervals)
        except ValueError as e:
            raise BadRequestError(str(e)) from e

    # 7. Substitute validation if nominated (BR-EL-014)
    if requires_substitute and substitute_user_id:
        # Get substitute kind via directory contract
        user_map = directory.get_users([substitute_user_id])
        sub_dto = user_map.get(substitute_user_id)
        sub_kind = sub_dto.kind if sub_dto else None
        sub_leaves = get_substitute_active_leaves(substitute_user_id)
        try:
            validate_substitute_eligibility(
                user_id,
                substitute_user_id,
                sub_kind,
                sub_leaves,
                start_date,
                end_date,
            )
        except ValueError as e:
            raise BadRequestError(str(e)) from e

    # 8. Resolve hierarchy routing (BR-EL-019)
    hierarchy = resolve_hierarchy_for_employee(
        user_id,
        department=user_department,
        designation=user_designation,
        category=category,
    )
    unit_head_id = hierarchy.unit_head_user_id if hierarchy else None
    establishment_id = hierarchy.establishment_user_id if hierarchy else None
    sanctioning_id = hierarchy.sanctioning_authority_user_id if hierarchy else None
    sanctioning_role = hierarchy.sanctioning_authority_role if hierarchy else "Dean"

    applicant_is_director = (
        "director" in [r.lower() for r in user_roles]
        or user_designation.lower() == "director"
    )

    # 9. Initial state (CW-EL-01)
    status = get_initial_submission_status(
        requires_substitute=requires_substitute and bool(substitute_user_id),
        applicant_is_director=applicant_is_director,
    )

    app = LeaveApplication.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        is_half_day=is_half_day,
        half_day_session=half_day_session if is_half_day else None,
        chargeable_days=chargeable_days,
        purpose=purpose,
        medical_certificate=medical_certificate,
        is_station_leave=is_station_leave,
        station_leave_departure=station_leave_departure,
        station_leave_return=station_leave_return,
        station_destination=station_destination,
        station_address=station_address,
        station_emergency_contact=station_emergency_contact,
        requires_substitute=requires_substitute and bool(substitute_user_id),
        substitute_user_id=substitute_user_id if requires_substitute else None,
        substitute_status=(
            SubstituteStatus.PENDING.value
            if requires_substitute and substitute_user_id
            else SubstituteStatus.NONE.value
        ),
        unit_head_user_id=unit_head_id,
        establishment_user_id=establishment_id,
        sanctioning_authority_user_id=sanctioning_id,
        sanctioning_authority_role=sanctioning_role,
        status=status.value,
    )

    # 10. Create initial actionable task (CFR-EL-030)
    if status == ApplicationStatus.AWAITING_SUBSTITUTE and substitute_user_id:
        WorkflowTask.objects.create(
            leave_application=app,
            task_type=TaskType.SUBSTITUTE_RESPONSE.value,
            assigned_to_user_id=substitute_user_id,
            status="pending",
        )
    elif status == ApplicationStatus.AWAITING_DIRECTOR:
        WorkflowTask.objects.create(
            leave_application=app,
            task_type=TaskType.DIRECTOR_SELF_SANCTION.value,
            assigned_to_user_id=user_id,
            status="pending",
        )
    elif status == ApplicationStatus.AWAITING_UNIT_HEAD and unit_head_id:
        WorkflowTask.objects.create(
            leave_application=app,
            task_type=TaskType.UNIT_HEAD_REVIEW.value,
            assigned_to_user_id=unit_head_id,
            status="pending",
        )

    # 11. Audit row
    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=user_id,
        action="submit_application",
        from_state="draft",
        to_state=status.value,
        remarks="Leave application submitted",
        payload={"chargeable_days": str(chargeable_days), "category": category},
    )

    return app


@transaction.atomic
def withdraw_leave(
    application_id: int,
    user_id: int,
    reason: str = "",
) -> LeaveApplication:
    """Withdraw a pending leave application immediately (CW-EL-01 / EL-UC-007 / BR-EL-022)."""
    app = get_application_by_id(application_id)
    if not app:
        raise NotFoundError(f"Leave application #{application_id} not found.")

    if app.user_id != user_id:
        raise BadRequestError("You can only withdraw your own leave application.")

    current_status = ApplicationStatus(app.status)
    try:
        new_status = transition_withdrawal(current_status)
    except ValueError as e:
        raise ConflictError(str(e)) from e

    from_state = app.status
    app.status = new_status.value
    app.withdrawn_at = timezone.now()
    app.withdrawn_reason = reason
    app.save(update_fields=["status", "withdrawn_at", "withdrawn_reason", "updated_at"])

    # Terminate remaining pending workflow tasks (CFR-EL-018.2)
    WorkflowTask.objects.filter(
        leave_application=app, status="pending"
    ).update(status="cancelled", completed_at=timezone.now())

    LeaveAuditLog.objects.create(
        leave_application=app,
        actor_user_id=user_id,
        action="withdraw_application",
        from_state=from_state,
        to_state=new_status.value,
        remarks=reason or "Withdrawn by applicant",
    )

    return app
