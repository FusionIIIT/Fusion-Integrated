"""Policy and validation services for Employee Leave Management."""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Optional

from django.db.models import Q

from modules.elm.domain.errors import (
    BalanceExceededError,
    EligibilityError,
    OverlapError,
)
from modules.elm.domain.policy import (
    calculate_leave_duration,
    check_date_overlap,
    validate_eligibility,
    validate_rh_calendar,
    validate_vl_vacation_window,
)
from modules.elm.models import HolidayCalendarEntry, LeaveAccount, LeaveRequest, LeaveStatus


def get_holiday_calendar_dates(year: int) -> set[datetime.date]:
    """Retrieve all closed holidays for working-day calculations."""
    return set(
        HolidayCalendarEntry.objects.filter(year=year, is_rh=False).values_list("date", flat=True)
    )


def get_rh_calendar_dates(year: int) -> set[datetime.date]:
    """Retrieve all published Restricted Holiday dates."""
    return set(
        HolidayCalendarEntry.objects.filter(year=year, is_rh=True).values_list("date", flat=True)
    )


def validate_and_calculate_request(
    applicant_id: int,
    employee_kind: str,
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    is_half_day: bool = False,
    half_day_type: Optional[str] = None,
    exclude_request_id: Optional[int] = None,
) -> Decimal:
    """Validate leave request against eligibility, calendars, overlap, and balance."""
    # 1. Eligibility check
    validate_eligibility(employee_kind, category)

    # 2. Holiday and RH Calendar validation
    year = start_date.year
    holidays = get_holiday_calendar_dates(year)

    if category == "RH":
        rh_dates = get_rh_calendar_dates(year)
        validate_rh_calendar(start_date, rh_dates)

    # 3. Calculate duration
    duration = calculate_leave_duration(
        category=category,
        start_date=start_date,
        end_date=end_date,
        is_half_day=is_half_day,
        half_day_type=half_day_type,
        holiday_calendar=holidays,
    )

    # 4. Overlap validation (BR-EL-012)
    active_statuses = [
        LeaveStatus.AWAITING_SUBSTITUTE_RESPONSE,
        LeaveStatus.AWAITING_APPLICANT_ACTION,
        LeaveStatus.AWAITING_UNIT_HEAD_REVIEW,
        LeaveStatus.AWAITING_ESTABLISHMENT_REVIEW,
        LeaveStatus.AWAITING_SANCTION_AUTHORITY_REVIEW,
        LeaveStatus.APPROVED,
    ]
    qs = LeaveRequest.objects.filter(
        applicant_id=applicant_id,
        status__in=active_statuses,
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if exclude_request_id:
        qs = qs.exclude(id=exclude_request_id)

    for existing in qs:
        if check_date_overlap(
            start_date, end_date, half_day_type if is_half_day else None,
            existing.start_date, existing.end_date, existing.half_day_type if existing.is_half_day else None
        ):
            raise OverlapError(
                f"Requested leave overlaps with existing active leave ({existing.category} "
                f"from {existing.start_date} to {existing.end_date}, status: {existing.status})."
            )

    # 5. Balance check
    account, _ = LeaveAccount.objects.get_or_create(
        employee_id=applicant_id,
        category=category,
        year=year,
        defaults={"allotted": Decimal("0.0"), "available": Decimal("0.0")},
    )
    if account.available < duration:
        raise BalanceExceededError(
            f"Insufficient leave balance for {category}. Available: {account.available}, Required: {duration}."
        )

    return duration
