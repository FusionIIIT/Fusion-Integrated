"""Leave application submission and withdrawal services."""

from datetime import date
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.leave.domain.counting import calculate_leave_days
from modules.leave.domain.entities import HalfDayType, LeaveCategory, LeaveStatus
from modules.leave.domain.errors import DomainError
from modules.leave.domain.rules import (
    validate_balance_sufficient,
    validate_category_eligibility,
    validate_no_overlap,
    validate_positive_leave_days,
    validate_rh_date,
    validate_substitute_eligibility,
    validate_vacation_period,
)
from modules.leave.models import LeaveActionLog, LeaveApplication, LeaveBalance
from modules.leave.selectors.calendar import (
    get_closed_holiday_dates,
    get_restricted_holiday_dates,
    get_vacation_period_tuples,
)
from modules.leave.services.balances import ensure_user_balances_initialized


def submit_application(
    principal,
    data: dict,
) -> LeaveApplication:
    """Create and submit a new leave application (EL-UC-001)."""
    user_id = principal.user_id
    user_kind = principal.kind
    category = data["leave_type"]
    start_date: date = data["start_date"]
    end_date: date = data["end_date"]
    half_day = data.get("half_day_type", HalfDayType.FULL.value)
    reason = data.get("reason", "")
    substitute_user_id = data.get("substitute_user_id")

    # Domain validations
    try:
        validate_category_eligibility(user_kind, category)
    except DomainError as e:
        raise BadRequestError(e.message) from None

    current_year = start_date.year
    ensure_user_balances_initialized(user_id, current_year, user_kind)

    closed_holidays = get_closed_holiday_dates(current_year)
    rh_holidays = get_restricted_holiday_dates(current_year)
    vacations = get_vacation_period_tuples(current_year)

    if category == LeaveCategory.RH.value:
        try:
            validate_rh_date(start_date, end_date, rh_holidays)
        except DomainError as e:
            raise BadRequestError(e.message) from None

    if category == LeaveCategory.VL.value:
        try:
            validate_vacation_period(start_date, end_date, vacations)
        except DomainError as e:
            raise BadRequestError(e.message) from None

    try:
        days_count = calculate_leave_days(
            category=category,
            start_date=start_date,
            end_date=end_date,
            half_day_type=half_day,
            closed_holiday_dates=closed_holidays,
        )
        validate_positive_leave_days(days_count)
    except DomainError as e:
        raise BadRequestError(e.message) from None

    with transaction.atomic():
        # Balance validation
        bal = (
            LeaveBalance.objects.select_for_update()
            .filter(
                user_id=user_id,
                year=current_year,
                leave_type=category,
            )
            .first()
        )

        available = bal.balance if bal else Decimal("0.0")
        try:
            validate_balance_sufficient(days_count, available)
        except DomainError as e:
            raise ConflictError(e.message) from None

        # Overlap validation
        active_leaves = LeaveApplication.objects.filter(
            applicant_user_id=user_id,
            status__in=[
                LeaveStatus.AWAITING_SUBSTITUTE.value,
                LeaveStatus.AWAITING_UNIT_HEAD.value,
                LeaveStatus.AWAITING_ESTABLISHMENT.value,
                LeaveStatus.AWAITING_SANCTION.value,
                LeaveStatus.APPROVED.value,
            ],
        ).values("start_date", "end_date", "leave_type", "half_day_type")

        try:
            validate_no_overlap(
                existing_leaves=list(active_leaves),
                new_start=start_date,
                new_end=end_date,
                new_category=category,
                new_half_day=half_day,
            )
        except DomainError as e:
            raise ConflictError(e.message) from None

        # Substitute validation
        if substitute_user_id:
            sub_leaves = list(
                LeaveApplication.objects.filter(
                    applicant_user_id=substitute_user_id,
                    status="APPROVED",
                ).values_list("start_date", "end_date")
            )
            try:
                validate_substitute_eligibility(
                    applicant_user_id=user_id,
                    substitute_user_id=substitute_user_id,
                    substitute_active_leaves=sub_leaves,
                    requested_start=start_date,
                    requested_end=end_date,
                )
            except DomainError as e:
                raise ConflictError(e.message) from None

        # Initial workflow routing
        is_director = getattr(principal, "active_role", None) == "Director"
        if substitute_user_id:
            initial_status = LeaveStatus.AWAITING_SUBSTITUTE.value
            sub_status = "PENDING"
        elif is_director:
            # Director self-sanction (BW-EL-07)
            initial_status = LeaveStatus.APPROVED.value
            sub_status = "ACCEPTED"
            # Deduct balance immediately
            bal.balance -= days_count
            bal.availed += days_count
            bal.save(update_fields=["balance", "availed", "updated_at"])
        else:
            initial_status = LeaveStatus.AWAITING_UNIT_HEAD.value
            sub_status = "ACCEPTED"

        app = LeaveApplication.objects.create(
            applicant_user_id=user_id,
            leave_type=category,
            start_date=start_date,
            end_date=end_date,
            half_day_type=half_day,
            days_count=days_count,
            reason=reason,
            status=initial_status,
            substitute_user_id=substitute_user_id,
            substitute_status=sub_status,
            is_station_leave=data.get("is_station_leave", False),
            station_departure_date=data.get("station_departure_date"),
            station_arrival_date=data.get("station_arrival_date"),
            station_address=data.get("station_address", ""),
            contact_number=data.get("contact_number", ""),
        )

        LeaveActionLog.objects.create(
            application=app,
            actor_user_id=user_id,
            action="SUBMIT",
            from_status="DRAFT",
            to_status=initial_status,
            remarks="Application submitted",
        )

        return app


def withdraw_application(application_id: int, principal) -> LeaveApplication:
    """Immediately withdraw a pending application (EL-UC-007, BR-EL-022)."""
    with transaction.atomic():
        try:
            app = LeaveApplication.objects.select_for_update().get(pk=application_id)
        except LeaveApplication.DoesNotExist:
            raise NotFoundError(f"Application #{application_id} not found.") from None

        if app.applicant_user_id != principal.user_id:
            raise ConflictError("You can only withdraw your own applications.")

        pending_states = [
            LeaveStatus.AWAITING_SUBSTITUTE.value,
            LeaveStatus.SUBSTITUTE_DECLINED.value,
            LeaveStatus.AWAITING_UNIT_HEAD.value,
            LeaveStatus.AWAITING_ESTABLISHMENT.value,
            LeaveStatus.AWAITING_SANCTION.value,
        ]
        if app.status not in pending_states:
            raise ConflictError(f"Application cannot be withdrawn in status '{app.status}'.")

        from_status = app.status
        app.status = LeaveStatus.WITHDRAWN.value
        app.save(update_fields=["status", "updated_at"])

        LeaveActionLog.objects.create(
            application=app,
            actor_user_id=principal.user_id,
            action="WITHDRAW",
            from_status=from_status,
            to_status=LeaveStatus.WITHDRAWN.value,
            remarks="Application withdrawn by applicant",
        )

        return app
