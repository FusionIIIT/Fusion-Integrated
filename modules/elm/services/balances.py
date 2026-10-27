"""Leave balance management and year-end conversion service.

Implements authoritative business rules:
- BR-EL-002: CL entitlement (8 days) & annual lapse (no carry forward).
- BR-EL-005: Non-faculty EL entitlement (30 days) & carry forward.
- BR-EL-006: Faculty VL entitlement (60 days).
- BR-EL-007: VL-to-EL year-end conversion (2 VL : 1 EL, including fractional conversion, VL does not carry forward).
- BR-EL-008: Converted EL credited to faculty EL balance.
- BR-EL-009: Commuted Leave (COL, 20 days) entitlement & carry forward.
"""

from decimal import Decimal
from django.db import transaction
from modules.elm.models import LeaveType, LeaveBalance


ANNUAL_ENTITLEMENTS = {
    "faculty": {
        "CL": Decimal("8.0"),
        "RH": Decimal("2.0"),
        "SCL": Decimal("15.0"),
        "VL": Decimal("60.0"),
        "COL": Decimal("20.0"),
    },
    "staff": {
        "CL": Decimal("8.0"),
        "RH": Decimal("2.0"),
        "SCL": Decimal("15.0"),
        "EL": Decimal("30.0"),
        "COL": Decimal("20.0"),
    },
}


def credit_annual_leaves(employee_user_id: int, kind: str, year: int) -> list[LeaveBalance]:
    """Credit annual entitlements for an employee for the given year.

    Idempotent: If record already exists, retains existing credit rather than duplicating.
    """
    entitlements = ANNUAL_ENTITLEMENTS.get(kind, ANNUAL_ENTITLEMENTS["staff"])
    created_or_updated = []

    with transaction.atomic():
        for code, days in entitlements.items():
            leave_type, _ = LeaveType.objects.get_or_create(
                code=code,
                defaults={"name": f"{code} Leave", "is_active": True},
            )
            balance, created = LeaveBalance.objects.get_or_create(
                employee_user_id=employee_user_id,
                leave_type=leave_type,
                year=year,
                defaults={"credited": days, "used": Decimal("0.0")},
            )
            created_or_updated.append(balance)

    return created_or_updated


def process_year_end(employee_user_id: int, kind: str, current_year: int) -> dict[str, Decimal]:
    """Execute year-end rollover and VL-to-EL conversion for an employee into the next year.

    Idempotent: Uses exact balance calculation without repeated increments on reruns.
    - Unused CL & SCL lapse (do not carry forward).
    - Unused non-faculty EL carries forward into new year.
    - Unused COL carries forward into new year.
    - Unused faculty VL converts at 2 VL : 1 EL into faculty EL in next year (BR-EL-007, BR-EL-008).
    - Unused VL itself does not carry forward.
    """
    next_year = current_year + 1
    summary: dict[str, Decimal] = {}

    with transaction.atomic():
        balances = LeaveBalance.objects.filter(
            employee_user_id=employee_user_id,
            year=current_year,
        ).select_related("leave_type")

        # Collect remaining balances from current year
        remaining_by_type = {b.leave_type.code: b.remaining for b in balances}

        # Initialize or fetch base entitlements for next year
        credit_annual_leaves(employee_user_id, kind, next_year)
        entitlements = ANNUAL_ENTITLEMENTS.get(kind, ANNUAL_ENTITLEMENTS["staff"])

        if kind == "faculty":
            unused_vl = remaining_by_type.get("VL", Decimal("0.0"))
            converted_el = unused_vl / Decimal("2.0") if unused_vl > Decimal("0.0") else Decimal("0.0")
            summary["converted_el_from_vl"] = converted_el

            el_type, _ = LeaveType.objects.get_or_create(
                code="EL",
                defaults={"name": "Earned Leave", "is_active": True},
            )
            el_balance, _ = LeaveBalance.objects.get_or_create(
                employee_user_id=employee_user_id,
                leave_type=el_type,
                year=next_year,
                defaults={"credited": Decimal("0.0"), "used": Decimal("0.0")},
            )
            # Sets converted EL accurately (idempotent overwrite)
            el_balance.credited = converted_el
            el_balance.save(update_fields=["credited"])

            # COL carries forward: base entitlement (20.0) + unused_col
            unused_col = remaining_by_type.get("COL", Decimal("0.0"))
            base_col = entitlements.get("COL", Decimal("20.0"))
            col_balance = LeaveBalance.objects.get(
                employee_user_id=employee_user_id,
                leave_type__code="COL",
                year=next_year,
            )
            col_balance.credited = base_col + unused_col
            col_balance.save(update_fields=["credited"])
            summary["carried_forward_col"] = unused_col

        elif kind == "staff":
            # Non-faculty EL carries forward: base entitlement (30.0) + unused_el
            unused_el = remaining_by_type.get("EL", Decimal("0.0"))
            base_el = entitlements.get("EL", Decimal("30.0"))
            el_balance = LeaveBalance.objects.get(
                employee_user_id=employee_user_id,
                leave_type__code="EL",
                year=next_year,
            )
            el_balance.credited = base_el + unused_el
            el_balance.save(update_fields=["credited"])
            summary["carried_forward_el"] = unused_el

            # COL carries forward: base entitlement (20.0) + unused_col
            unused_col = remaining_by_type.get("COL", Decimal("0.0"))
            base_col = entitlements.get("COL", Decimal("20.0"))
            col_balance = LeaveBalance.objects.get(
                employee_user_id=employee_user_id,
                leave_type__code="COL",
                year=next_year,
            )
            col_balance.credited = base_col + unused_col
            col_balance.save(update_fields=["credited"])
            summary["carried_forward_col"] = unused_col

    return summary


def calculate_leave_days(leave_type_code: str, start_date, end_date, half_day_type: str = "FULL") -> Decimal:
    """Calculate the number of leave days requested.

    Implements:
    - BR-EL-010: Half-day CL consumes 0.5 day.
    - BR-EL-011: Calendar continuous day interval.
    """
    if leave_type_code == "CL" and half_day_type in ("FIRST_HALF", "SECOND_HALF"):
        return Decimal("0.5")
    delta_days = (end_date - start_date).days + 1
    return Decimal(str(max(0, delta_days)))


def debit_leave_balance(employee_user_id: int, leave_type_code: str, days: Decimal, year: int) -> bool:
    """Deduct approved leave days from the employee's credited balance (BR-EL-010, BR-EL-023)."""
    with transaction.atomic():
        try:
            balance = LeaveBalance.objects.select_for_update().get(
                employee_user_id=employee_user_id,
                leave_type__code=leave_type_code,
                year=year,
            )
            balance.used = balance.used + days
            balance.save(update_fields=["used"])
            return True
        except LeaveBalance.DoesNotExist:
            return False


def restore_leave_balance(employee_user_id: int, leave_type_code: str, days: Decimal, year: int) -> bool:
    """Restore leave balance upon approved cancellation before leave start (BR-EL-023)."""
    with transaction.atomic():
        try:
            balance = LeaveBalance.objects.select_for_update().get(
                employee_user_id=employee_user_id,
                leave_type__code=leave_type_code,
                year=year,
            )
            balance.used = max(Decimal("0.0"), balance.used - days)
            balance.save(update_fields=["used"])
            return True
        except LeaveBalance.DoesNotExist:
            return False

