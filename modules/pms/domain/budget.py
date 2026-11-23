"""Budget rules: the three cost components, the threshold, and when a budget may be decided."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import InvalidInput, RuleViolation

MAX_AMOUNT = Decimal("9999999999.99")
NOT_AVAILABLE = "not_available"      # BR-PMS-053: no budget-availability source exists


def amount(value, label: str) -> Decimal:
    try:
        out = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InvalidInput(f"The {label} must be an amount in rupees.",
                           code="invalid_amount") from exc
    if not out.is_finite() or out < 0 or out > MAX_AMOUNT \
            or out != out.quantize(Decimal("0.01")):
        raise InvalidInput(f"The {label} must be zero or more, in rupees with at most two "
                           f"decimal places.", code="invalid_amount")
    return out


def check_components(filing_fee, attorney_fee, admin_cost) -> tuple[Decimal, Decimal,
                                                                     Decimal, Decimal]:
    """BR-PMS-048..050: all three components are present; returns them and the total."""
    f = amount(filing_fee, "filing fee")
    a = amount(attorney_fee, "attorney fee")
    m = amount(admin_cost, "administrative cost")
    total = f + a + m
    if total > MAX_AMOUNT:
        raise InvalidInput("The total budget is too large to record.", code="invalid_amount")
    return f, a, m, total


def application_allows_budget(status: str) -> bool:
    """BR-PMS-052 as ruled (B5)."""
    return status in sm.BUDGET_STATUSES


def exceeds_threshold(total: Decimal, threshold: Decimal | None) -> bool:
    """BR-PMS-051; no threshold means no decision is possible (ruling C14)."""
    if threshold is None:
        raise RuleViolation("No budget threshold is configured. Ask the PCC_ADMIN to set one "
                            "under Settings before a budget can be decided.",
                            code="budget_threshold_missing")
    return total > threshold
