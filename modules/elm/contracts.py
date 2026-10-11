"""Public interface for the Employee Leave Management (ELM) module (ADR-0010)."""
from dataclasses import dataclass
from modules.elm.selectors.leave import get_user_balances


@dataclass(frozen=True)
class LeaveSummaryDTO:
    user_id: int
    year: int
    balances: dict[str, float]


def get_user_leave_summary(user_id: int, year: int = 2026) -> LeaveSummaryDTO:
    qs = get_user_balances(user_id, year)
    balances = {b.leave_type: b.available_balance for b in qs}
    return LeaveSummaryDTO(user_id=user_id, year=year, balances=balances)
