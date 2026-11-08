"""Validation services for employee leave applications."""

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction

from modules.elm.domain.leave_rules import (
    LeaveRuleError,
    inclusive_calendar_days,
    validate_date_range,
    validate_sufficient_balance,
)
from modules.elm.models import (
    LeaveApplication,
    LeaveApplicationStatus,
    LeaveBalance,
    LeaveType,
)
from modules.elm.services.authz import require_permission
from modules.elm.services.routing import resolve_leave_route


def _calendar_year_day_counts(start_date: date, end_date: date) -> dict[int, int]:
    """Count inclusive calendar days separately for each year."""
    counts = {}
    current = start_date

    while current <= end_date:
        year_end = date(current.year, 12, 31)
        segment_end = min(end_date, year_end)

        counts[current.year] = inclusive_calendar_days(
            current,
            segment_end,
        )
        current = segment_end + timedelta(days=1)

    return counts


def validate_leave_application(
    *,
    user_id: int,
    leave_type: str,
    start_date,
    end_date,
    requested_days: Decimal,
    half_day: str = "",
    exclude_application_id: int | None = None,
) -> None:
    """Validate a leave request without saving it to the database."""

    # 1. Validate the requested dates.
    validate_date_range(start_date, end_date)

    # 2. Validate the leave type.
    valid_leave_types = {choice[0] for choice in LeaveType.choices}
    if leave_type not in valid_leave_types:
        raise LeaveRuleError("Invalid leave type.")

    # 3. Half-day leave is permitted only for a single-date CL request.
    valid_half_days = {"", "first_half", "second_half"}
    if half_day not in valid_half_days:
        raise LeaveRuleError("Invalid half-day selection.")

    if half_day and (leave_type != LeaveType.CL or start_date != end_date):
        raise LeaveRuleError("Half-day leave is allowed only for a single-date CL request.")

    try:
        requested = Decimal(str(requested_days))
    except Exception as exc:
        raise LeaveRuleError("Requested days must be a valid number.") from exc

    if not requested.is_finite() or requested <= 0:
        raise LeaveRuleError("Requested leave must be greater than zero.")

    crosses_year = start_date.year != end_date.year

    # EL, COL and VL count every calendar day in the interval.
    if leave_type in {LeaveType.EL, LeaveType.COL, LeaveType.VL}:
        expected_days = Decimal(inclusive_calendar_days(start_date, end_date))
        if requested != expected_days:
            raise LeaveRuleError(
                f"{leave_type} requests must count every calendar day "
                "in the continuous leave interval."
            )

    # Half-day CL must consume exactly half a day.
    if half_day and requested != Decimal("0.5"):
        raise LeaveRuleError("A half-day CL request must be exactly 0.5 days.")

    # For other leave types, the requested amount cannot exceed
    # the inclusive date range. Their specific holiday/calendar
    # counting rules still need to be implemented separately.
    if (
        not half_day
        and leave_type not in {LeaveType.EL, LeaveType.COL, LeaveType.VL}
        and requested > inclusive_calendar_days(start_date, end_date)
    ):
        raise LeaveRuleError("Requested days cannot exceed the inclusive date range.")

    # 4. Check every relevant year's balance.
    if crosses_year:
        for leave_year, year_days in _calendar_year_day_counts(start_date, end_date).items():
            try:
                balance = LeaveBalance.objects.get(
                    user_id=user_id,
                    leave_type=leave_type,
                    leave_year=leave_year,
                )
            except LeaveBalance.DoesNotExist as exc:
                raise LeaveRuleError(
                    f"No {leave_type} balance exists for year {leave_year}."
                ) from exc

            validate_sufficient_balance(
                balance.available_balance,
                Decimal(year_days),
            )
    else:
        leave_year = start_date.year
        try:
            balance = LeaveBalance.objects.get(
                user_id=user_id,
                leave_type=leave_type,
                leave_year=leave_year,
            )
        except LeaveBalance.DoesNotExist as exc:
            raise LeaveRuleError("No balance exists for this leave type and year.") from exc

        validate_sufficient_balance(
            balance.available_balance,
            requested,
        )

    # 5. Reject overlapping pending or approved requests.
    existing = LeaveApplication.objects.filter(
        user_id=user_id,
        status__in=[
            LeaveApplicationStatus.PENDING,
            LeaveApplicationStatus.APPROVED,
        ],
        start_date__lte=end_date,
        end_date__gte=start_date,
    )

    if exclude_application_id is not None:
        existing = existing.exclude(pk=exclude_application_id)

    for application in existing:
        same_single_day = (
            start_date == end_date
            and application.start_date == application.end_date
            and application.start_date == start_date
        )

        # Opposite halves of the same day are allowed for CL only.
        opposite_cl_halves = (
            same_single_day
            and leave_type == LeaveType.CL
            and application.leave_type == LeaveType.CL
            and half_day in {"first_half", "second_half"}
            and application.half_day in {"first_half", "second_half"}
            and half_day != application.half_day
        )

        if opposite_cl_halves:
            continue

        raise LeaveRuleError("This request overlaps an existing pending or approved leave.")


@transaction.atomic
def submit_leave_application(
    *,
    actor,
    user_id: int,
    leave_type: str,
    start_date: date,
    end_date: date,
    requested_days: Decimal,
    half_day: str = "",
    reason: str = "",
) -> LeaveApplication:
    """Validate and record a new pending leave application.

    Submission does not deduct the leave balance. The balance is
    updated when the leave is approved.
    """

    require_permission(actor, "elm.leave_application.create")

    if getattr(actor, "user_id", None) != user_id:
        from core.api.exceptions import PermissionDeniedError

        raise PermissionDeniedError(
            "You may submit leave applications only for yourself.",
            code="permission_denied",
        )
    # Lock existing balances for the relevant years before validation.
    years = range(start_date.year, end_date.year + 1)

    list(
        LeaveBalance.objects.select_for_update()
        .filter(
            user_id=user_id,
            leave_type=leave_type,
            leave_year__in=years,
        )
        .order_by("leave_year")
    )

    validate_leave_application(
        user_id=user_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        requested_days=requested_days,
        half_day=half_day,
    )

    route = resolve_leave_route(
        actor=actor,
        applicant_user_id=user_id,
        leave_type=leave_type,
    )

    return LeaveApplication.objects.create(
        user_id=user_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        requested_days=requested_days,
        half_day=half_day,
        reason=reason,
        status=LeaveApplicationStatus.PENDING,
        assigned_unit_head_user_id=route.unit_head_user_id,
        assigned_final_authority_user_id=route.final_authority_user_id,
        workflow_stage=route.workflow_stage,
        establishment_required=route.establishment_required,
    )
