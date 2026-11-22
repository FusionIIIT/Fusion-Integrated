from datetime import timedelta
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from modules.directory.models import UserRef
from modules.elm.models import AuthorityRoute, CalendarDay, LeaveBalance, LeaveEvent


def locked_employee(employee):
    try:
        return UserRef.objects.select_for_update().get(
            user_id=employee, is_active=True, kind__in=["faculty", "staff"]
        )
    except UserRef.DoesNotExist:
        raise ValidationError("Employee not found or not active") from None


def account(employee, leave_type, year, kind):
    ensure_open_year(employee, year)
    allowed_types = ["CL", "RH", "SCL", "COL", "EL", "VL"]
    if leave_type.type not in allowed_types:
        raise ValidationError("Invalid leave type")

    balances = (
        LeaveBalance.objects.select_for_update()
        .filter(employee=employee, leave_type=leave_type, year=year)
        .values_list("id", flat=True)
    )

    if len(balances) > 1:
        raise ValidationError("Duplicate leave accounts require reconciliation")
    if len(balances) == 1:
        return LeaveBalance.objects.get(id=balances[0])

    entitlements = {
        "CL": Decimal("8"),
        "RH": Decimal("2"),
        "SCL": Decimal("15"),
        "COL": Decimal("20"),
    }

    if leave_type.type in entitlements:
        balance = entitlements[leave_type.type]
    else:
        if leave_type.type == "EL":
            balance = Decimal("30") if kind == "staff" else Decimal("0")
        elif leave_type.type == "VL":
            balance = Decimal("0") if kind == "staff" else Decimal("60")
        else:
            raise ValidationError("Invalid leave type")

    return LeaveBalance.objects.create(
        employee=employee, leave_type=leave_type, year=year, employee_kind=kind, balance=balance
    )


def count_days(category, start, end, half="FULL"):
    if half not in ("FULL", "FIRST", "SECOND"):
        raise ValidationError("Invalid half value")

    if start > end:
        raise ValidationError("Start date cannot be after end date")

    if start.year != end.year:
        raise ValidationError("Dates must be in the same year")

    if category not in ("CL", "RH", "SCL", "EL", "COL", "VL"):
        raise ValidationError("Invalid category")

    if half != "FULL" and category != "CL":
        raise ValidationError("Only CL supports half days")
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]

    if category in ("CL", "SCL"):
        eligible_dates = [
            d
            for d in dates
            if d.weekday() < 5
            and not CalendarDay.objects.filter(date=d, kind="CLOSED", published=True).exists()
        ]
        if half in ("FIRST", "SECOND"):
            if len(dates) != 1:
                raise ValidationError("Half-day count requires single date")
            d = dates[0]
            if d not in eligible_dates:
                raise ValidationError("Date is not eligible for half-day count")
            return Decimal("0.5")
        if not eligible_dates:
            raise ValidationError("No working leave days")
        return Decimal(len(eligible_dates))

    if category == "RH":
        for d in dates:
            if not CalendarDay.objects.filter(date=d, kind="RH", published=True).exists():
                raise ValidationError(f"Date {d} does not have RH status")
        return Decimal(len(dates))

    if category == "VL":
        for d in dates:
            if not CalendarDay.objects.filter(date=d, kind="VACATION", published=True).exists():
                raise ValidationError(f"Date {d} does not have VACATION status")
            if (
                not CalendarDay.objects.filter(date=d, kind="VACATION", published=True)
                .exclude(source="")
                .exists()
            ):
                raise ValidationError(f"Date {d} has VACATION status but no source")
        return Decimal(len(dates))

    if category in ("EL", "COL"):
        return Decimal(len(dates))

    raise ValidationError("Invalid category")


def resolve_route(employee, category):
    allowed_categories = {"CL", "RH", "SCL", "EL", "COL", "VL"}
    if category not in allowed_categories and category != "":
        raise ValidationError("Invalid leave category")

    try:
        route_row = AuthorityRoute.objects.get(employee=employee, leave_category=category)
    except AuthorityRoute.DoesNotExist:
        try:
            route_row = AuthorityRoute.objects.get(employee=employee, leave_category="")
        except AuthorityRoute.DoesNotExist:
            raise ValidationError("No matching authority route found") from None

    route = []
    if route_row.director_self:
        route = [employee]
    elif category in {"CL", "RH"}:
        route = [route_row.unit_head]
    else:
        if not route_row.higher_authorities:
            raise ValidationError("Higher authorities required for this category")
        route = [route_row.unit_head, *route_row.higher_authorities]

    # Validate route elements
    if not all(isinstance(x, int) and x > 0 for x in route):
        raise ValidationError("Route contains invalid integers")
    if len(route) != len(set(route)):
        raise ValidationError("Route contains duplicates")
    if employee in route and not route_row.director_self:
        raise ValidationError("Employee cannot be in route unless director_self is True")

    # Validate UserRef existence
    user_ids = route
    user_refs = UserRef.objects.filter(
        user_id__in=user_ids, is_active=True, kind__in=["faculty", "staff"]
    )
    if len(user_refs) != len(user_ids):
        raise ValidationError("Incomplete UserRef matching route")

    return route


def ensure_open_year(employee, year):
    if LeaveEvent.objects.filter(
        employee=employee, action="YEAR_END_ROLLED_OVER", details__year=year
    ).exists():
        raise ValidationError("Closed leave year requires reconciliation")
