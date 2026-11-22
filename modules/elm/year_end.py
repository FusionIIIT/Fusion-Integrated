from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from modules.elm.models import LeaveBalance, LeaveEvent, LeaveRequest
from modules.elm.validation import locked_employee


def next_balances(kind, balances):
    # Validate kind
    if kind not in {"staff", "faculty"}:
        raise ValidationError("Invalid kind")

    # Validate input keys
    allowed_keys = {
        "staff": {"CL", "RH", "SCL", "EL", "COL"},
        "faculty": {"CL", "RH", "SCL", "EL", "COL", "VL"},
    }
    if set(balances) != allowed_keys[kind]:
        raise ValidationError("Incomplete account set")
    for key in balances:
        if key not in allowed_keys[kind]:
            raise ValidationError(f"Invalid key: {key}")

    # Validate values are Decimal and non-negative/finite
    for key, value in balances.items():
        if not isinstance(value, Decimal):
            raise ValidationError(f"Invalid value type for {key}")
        if not value.is_finite() or value < 0:
            raise ValidationError(f"Invalid value for {key}")

    result = {}

    # CL8, RH2, SCL15
    result["CL"] = Decimal("8")
    result["RH"] = Decimal("2")
    result["SCL"] = Decimal("15")

    # COL20 + prior COL
    prior_col = balances.get("COL", Decimal("0"))
    result["COL"] = Decimal("20") + prior_col

    # Staff EL: 30 + prior EL
    if kind == "staff":
        prior_el = balances.get("EL", Decimal("0"))
        result["EL"] = Decimal("30") + prior_el

    # Faculty EL: prior EL + prior VL/2
    if kind == "faculty":
        prior_el = balances.get("EL", Decimal("0"))
        prior_vl = balances.get("VL", Decimal("0"))
        result["EL"] = prior_el + (prior_vl / Decimal("2"))

    # Faculty VL: 60
    if kind == "faculty":
        result["VL"] = Decimal("60")

    return result


@transaction.atomic
def rollover_employee(employee, year, actor):
    user = rollover_preflight(employee, year)
    if not user:
        return {"employee": employee, "status": "already_processed"}
    closing, types = closing_accounts(employee, year, user.kind)
    opening = next_balances(user.kind, closing)
    if LeaveBalance.objects.filter(employee=employee, year=year + 1).exists():
        raise ValidationError("Existing next year accounts require reconciliation")
    for code, value in opening.items():
        LeaveBalance.objects.create(
            employee=employee,
            leave_type=types[code],
            balance=value,
            year=year + 1,
            employee_kind=user.kind,
        )
    LeaveEvent.objects.create(
        employee=employee,
        actor=actor,
        action="YEAR_END_ROLLED_OVER",
        details={
            "year": year,
            "closing": {k: str(v) for k, v in closing.items()},
            "opening": {k: str(v) for k, v in opening.items()},
        },
    )
    return {"employee": employee, "status": "processed"}


def rollover_preflight(employee, year):
    user = locked_employee(employee)
    if (
        not isinstance(year, int)
        or isinstance(year, bool)
        or not (2000 <= year < timezone.localdate().year)
    ):
        raise ValidationError("Invalid year")
    if LeaveEvent.objects.filter(
        employee=employee, action="YEAR_END_ROLLED_OVER", details__year=year
    ).exists():
        return None
    if LeaveRequest.objects.filter(
        employee=employee, start_date__year=year, status="PENDING"
    ).exists():
        raise ValidationError("Pending leave request")
    if LeaveRequest.objects.filter(
        employee=employee,
        start_date__year=year,
        status="APPROVED",
        operation="LEAVE",
        leave_type__type__in=["EL", "COL", "VL"],
        actual_return_date__isnull=True,
    ).exists():
        raise ValidationError("Unsettled return date")
    return user


def closing_accounts(employee, year, kind):
    rows = (
        LeaveBalance.objects.select_for_update()
        .filter(employee=employee, year=year)
        .select_related("leave_type")
    )
    closing = {}
    types = {}
    for row in rows:
        if row.employee_kind != kind:
            raise ValidationError("Invalid employee kind")
        if row.leave_type.type in closing:
            raise ValidationError("Duplicate category code")
        closing[row.leave_type.type] = row.balance
        types[row.leave_type.type] = row.leave_type
    return closing, types
