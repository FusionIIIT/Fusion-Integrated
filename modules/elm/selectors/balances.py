from datetime import date
from decimal import Decimal
from modules.elm.models import EmployeeLeaveBalance
from modules.elm.domain.constants import LEAVE_CATEGORIES, DEFAULT_ENTITLEMENTS


def get_user_balances(user_id: int, year: int | None = None) -> list[EmployeeLeaveBalance]:
    target_year = year or date.today().year
    balances = list(
        EmployeeLeaveBalance.objects.filter(user_id=user_id, year=target_year)
    )
    if not balances:
        # Initialize default balances for the user
        for cat in LEAVE_CATEGORIES:
            ent = DEFAULT_ENTITLEMENTS[cat]
            b = EmployeeLeaveBalance.objects.create(
                user_id=user_id,
                year=target_year,
                leave_category=cat,
                allocated_days=ent,
                availed_days=Decimal("0.0"),
                carried_forward=Decimal("0.0"),
                pending_days=Decimal("0.0"),
            )
            balances.append(b)
    return balances
