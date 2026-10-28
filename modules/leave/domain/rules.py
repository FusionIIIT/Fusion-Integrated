from datetime import date, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def is_half_day_cl_valid(category: str, half_day_slot: str, start_date: date, end_date: date) -> bool:
    """
    BR-EL-010: Half-day leave is valid strictly for Casual Leave (CL) on a single calendar date.
    """
    from modules.leave.models import LeaveCategory, HalfDaySlot

    if half_day_slot == HalfDaySlot.NONE:
        return True
    if category != LeaveCategory.CL:
        return False
    return start_date == end_date


def calculate_leave_days(category: str, start_date: date, end_date: date, half_day_slot: str) -> Decimal:
    """
    BR-EL-011:
    - Continuous-day counting for EL, COL, and VL (weekends/holidays count).
    - Working-day counting for CL, RH, and SCL (weekends/closed holidays excluded).
    - Half-day CL counts as 0.5.
    """
    from modules.leave.models import LeaveCategory, HalfDaySlot, HolidayCalendar

    if half_day_slot in (HalfDaySlot.FIRST_HALF, HalfDaySlot.SECOND_HALF):
        return Decimal("0.5")

    total_calendar_days = (end_date - start_date).days + 1
    if total_calendar_days <= 0:
        return Decimal("0.0")

    # Continuous counting categories
    if category in (LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL):
        return Decimal(str(total_calendar_days))

    # Working day counting for CL, RH, SCL
    closed_holiday_dates = set(
        HolidayCalendar.objects.filter(
            date__range=(start_date, end_date),
            is_rh=False,
        ).values_list("date", flat=True)
    )

    days_count = 0
    curr = start_date
    while curr <= end_date:
        # Weekend check: Monday=0 ... Sunday=6; Saturday=5, Sunday=6
        if curr.weekday() not in (5, 6) and curr not in closed_holiday_dates:
            days_count += 1
        curr += timedelta(days=1)

    return Decimal(str(max(1, days_count)))


def check_applicant_overlap(app) -> None:
    """
    BR-EL-012: Overlap check with the half-day CL exception.
    Rejects overlapping pending or approved requests, unless one is first-half
    and the other is second-half Casual Leave on the same calendar date.
    """
    from modules.leave.models import LeaveApplication, LeaveCategory, HalfDaySlot, LeaveStatus

    active_statuses = [
        LeaveStatus.SUBMITTED,
        LeaveStatus.SUBSTITUTE_PENDING,
        LeaveStatus.UNIT_HEAD_PENDING,
        LeaveStatus.SANCTIONING_PENDING,
        LeaveStatus.APPROVED,
    ]

    overlapping_qs = LeaveApplication.objects.filter(
        user_id=app.user_id,
        status__in=active_statuses,
        start_date__lte=app.end_date,
        end_date__gte=app.start_date,
    )
    if app.pk:
        overlapping_qs = overlapping_qs.exclude(pk=app.pk)

    for other in overlapping_qs:
        # Check half-day CL exception on the exact same date
        is_same_single_date = (
            app.start_date == app.end_date
            and other.start_date == other.end_date
            and app.start_date == other.start_date
        )
        is_both_cl = (
            app.category == LeaveCategory.CL
            and other.category == LeaveCategory.CL
        )
        is_opposite_halves = (
            (app.half_day_slot == HalfDaySlot.FIRST_HALF and other.half_day_slot == HalfDaySlot.SECOND_HALF)
            or (app.half_day_slot == HalfDaySlot.SECOND_HALF and other.half_day_slot == HalfDaySlot.FIRST_HALF)
        )

        if is_same_single_date and is_both_cl and is_opposite_halves:
            continue  # Permitted exception under BR-EL-012

        raise ValidationError({
            "start_date": _(
                f"Dates overlap with existing active/approved leave application #{other.pk} "
                f"({other.start_date} to {other.end_date}, status: {other.status})."
            )
        })


def check_substitute_eligibility(app) -> None:
    """
    BR-EL-014: Substitute must not be the applicant and must not have overlapping leave.
    """
    from modules.leave.models import LeaveApplication, LeaveStatus

    if not app.substitute_id:
        return

    if app.substitute_id == app.user_id:
        raise ValidationError({
            "substitute_id": _("Substitute cannot be the applicant themself.")
        })

    active_statuses = [
        LeaveStatus.SUBMITTED,
        LeaveStatus.SUBSTITUTE_PENDING,
        LeaveStatus.UNIT_HEAD_PENDING,
        LeaveStatus.SANCTIONING_PENDING,
        LeaveStatus.APPROVED,
    ]

    sub_leave_exists = LeaveApplication.objects.filter(
        user_id=app.substitute_id,
        status__in=active_statuses,
        start_date__lte=app.end_date,
        end_date__gte=app.start_date,
    ).exists()

    if sub_leave_exists:
        raise ValidationError({
            "substitute_id": _("The selected substitute has an overlapping active or approved leave.")
        })


def validate_station_leave(app) -> None:
    """
    BR-EL-013: Station Leave coupling.
    """
    if app.station_leave_applied:
        if not app.station_leave_address or not app.station_leave_address.strip():
            raise ValidationError({
                "station_leave_address": _("Address during station leave is required.")
            })
        if not app.station_leave_contact or not app.station_leave_contact.strip():
            raise ValidationError({
                "station_leave_contact": _("Emergency contact number during station leave is required.")
            })


def validate_leave_application(app) -> None:
    """
    Comprehensive domain validation coordinator.
    """
    from modules.leave.models import HalfDaySlot

    if not app.start_date:
        raise ValidationError({"start_date": _("Start date is required.")})
    if not app.end_date:
        raise ValidationError({"end_date": _("End date is required.")})
    if app.start_date > app.end_date:
        raise ValidationError({
            "start_date": _("Start date must be on or before end date.")
        })

    if not is_half_day_cl_valid(app.category, app.half_day_slot, app.start_date, app.end_date):
        raise ValidationError({
            "half_day_slot": _("Half-day leave is valid strictly for Casual Leave (CL) on a single calendar date.")
        })

    validate_station_leave(app)
    check_applicant_overlap(app)
    check_substitute_eligibility(app)

    # Compute and set calculated days
    app.calculated_days = calculate_leave_days(
        category=app.category,
        start_date=app.start_date,
        end_date=app.end_date,
        half_day_slot=app.half_day_slot,
    )
