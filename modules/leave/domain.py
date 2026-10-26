"""Category eligibility, date counting, and starting balances for ELM."""
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError

from modules.leave.models import LeaveCalendar, LeaveRequest

ANNUAL_ENTITLEMENTS = {
    "CL": Decimal("8"), "RH": Decimal("2"), "SCL": Decimal("15"),
    "COL": Decimal("20"),
}


def eligible_for(kind: str, leave_type: str) -> bool:
    if leave_type == "EL":
        return kind == "staff"
    if leave_type == "VL":
        return kind == "faculty"
    return leave_type in {code for code, _ in LeaveRequest.TYPE}


def starting_balance(kind: str, leave_type: str) -> Decimal:
    if not eligible_for(kind, leave_type):
        return Decimal("0")
    if leave_type == "EL":
        return Decimal("30")
    if leave_type == "VL":
        return Decimal("60")
    return ANNUAL_ENTITLEMENTS[leave_type]


def charge_by_year(leave_type: str, start_date, end_date, cl_period="full") -> dict[str, Decimal]:
    """Count continuous leave as calendar days, other categories as workdays.

    The current published calendar supplies closures and RH dates. A half-day
    CL is charged as 0.5 and may only occupy one date (validated by the model).
    """
    if end_date < start_date:
        raise ValidationError({"end_date": "End date must not precede start date."})
    active = LeaveCalendar.objects.filter(status="published").order_by("-published_at").first()
    days = active.days.all() if active else None
    closed = set(days.filter(is_closed=True).values_list("date", flat=True)) if days else set()
    restricted = set(days.filter(is_restricted_holiday=True).values_list("date", flat=True)) \
        if days else set()
    if leave_type == "RH" and (start_date != end_date or start_date not in restricted):
        raise ValidationError({"start_date": "Choose a date in the published RH calendar."})

    result: dict[str, Decimal] = {}
    day = start_date
    while day <= end_date:
        if leave_type in {"EL", "COL", "VL", "RH"}:
            amount = Decimal("1")
        elif day.weekday() < 5 and day not in closed:
            amount = Decimal("1")
        else:
            amount = Decimal("0")
        if leave_type == "CL" and cl_period != "full":
            amount = Decimal("0.5") if amount and day == start_date else Decimal("0")
        if amount:
            key = str(day.year)
            result[key] = result.get(key, Decimal("0")) + amount
        day += timedelta(days=1)
    if not result:
        raise ValidationError({"end_date": "The selected dates contain no chargeable leave days."})
    return result
