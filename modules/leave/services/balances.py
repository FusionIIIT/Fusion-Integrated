"""Leave balance initialization and adjustment services."""

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError
from modules.leave.models import LeaveBalance

DEFAULT_ENTITLEMENTS = {
    "CL": Decimal("8.0"),
    "RH": Decimal("2.0"),
    "SCL": Decimal("15.0"),
    "EL": Decimal("30.0"),
    "COL": Decimal("20.0"),
    "VL": Decimal("60.0"),
}


def ensure_user_balances_initialized(user_id: int, year: int, user_kind: str) -> None:
    """Ensure standard leave balances exist for the user for the given year."""
    types = ["CL", "RH", "SCL", "COL"]
    if user_kind == "faculty":
        types.append("VL")
    else:
        types.append("EL")

    for t_code in types:
        entitlement = DEFAULT_ENTITLEMENTS.get(t_code, Decimal("0.0"))
        LeaveBalance.objects.get_or_create(
            user_id=user_id,
            year=year,
            leave_type=t_code,
            defaults={
                "credited": entitlement,
                "availed": Decimal("0.0"),
                "balance": entitlement,
            },
        )


def adjust_balance(
    user_id: int,
    year: int,
    leave_type: str,
    delta: Decimal,
    is_credit: bool = True,
) -> LeaveBalance:
    """Adjust leave balance by delta (positive or negative)."""
    with transaction.atomic():
        bal, _ = LeaveBalance.objects.select_for_update().get_or_create(
            user_id=user_id,
            year=year,
            leave_type=leave_type,
            defaults={
                "credited": DEFAULT_ENTITLEMENTS.get(leave_type, Decimal("0.0")),
                "availed": Decimal("0.0"),
                "balance": DEFAULT_ENTITLEMENTS.get(leave_type, Decimal("0.0")),
            },
        )
        if is_credit:
            bal.balance += delta
            bal.credited += delta
        else:
            if bal.balance < delta:
                raise ConflictError(f"Cannot deduct {delta} from balance {bal.balance}.")
            bal.balance -= delta
            bal.availed += delta
        bal.save(update_fields=["credited", "availed", "balance", "updated_at"])
        return bal
