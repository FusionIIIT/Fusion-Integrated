"""elm's public surface — the ONLY thing other modules may import.

Plural by signature on purpose: a singular ``get_balance(user_id)`` is
what gets called inside a loop, and the N+1 must be unwritable.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from modules.elm.models import LeaveAccount


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    leave_year: str
    category: str
    opening_days: Decimal
    entitled_days: Decimal
    used_days: Decimal
    pending_days: Decimal

    @property
    def available_days(self) -> Decimal:
        return self.opening_days + self.entitled_days - self.used_days - self.pending_days


def _to_dto(account: LeaveAccount, pending_days: Decimal) -> LeaveBalanceDTO:
    return LeaveBalanceDTO(
        user_id=account.user_id,
        leave_year=account.leave_year,
        category=account.category,
        opening_days=account.opening_days,
        entitled_days=account.entitled_days,
        used_days=account.used_days,
        pending_days=pending_days,
    )


def get_balances(user_ids: Sequence[int],
                 leave_year: str) -> dict[int, list[LeaveBalanceDTO]]:
    """Current balances for several people at once.

    A person with no account for the year is simply absent from the
    mapping — a visible case, not a silent empty list three layers up.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    from modules.elm.selectors import balances as balance_selector

    return balance_selector.balances_for(ids, leave_year)


def get_employee_profiles(user_ids: Sequence[int]) -> dict[int, dict]:
    """Designation and organizational unit for several employees at once.

    Routing (Unit Head, Establishment, Sanctioning Authority) is resolved
    from these, so callers batch rather than loop.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    from modules.elm.models import EmployeeProfile

    rows = EmployeeProfile.objects.filter(user_id__in=ids, is_active=True)
    return {
        r.user_id: {
            "user_id": r.user_id,
            "employee_kind": r.employee_kind,
            "designation_name": r.designation_name,
            "unit_code": r.unit_code,
        }
        for r in rows
    }
