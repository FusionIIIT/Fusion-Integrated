"""
modules/leave/domain/rules.py
Pure domain logic for leave management.  No Django ORM calls here.
"""
from decimal import Decimal
from datetime import date, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Entitlement table
# ---------------------------------------------------------------------------

_ENTITLEMENTS: dict[str, dict[str, Any]] = {
    "CL": {
        "days_per_year": 8,
        "half_day_allowed": True,
        "carries_forward": False,
        "requires_substitute": False,
        "unit_head_scope": "final",
    },
    "RH": {
        "days_per_year": 2,
        "half_day_allowed": False,
        "carries_forward": False,
        "requires_substitute": False,
        "unit_head_scope": "final",
    },
    "SCL": {
        "days_per_year": 15,
        "half_day_allowed": False,
        "carries_forward": False,
        "requires_substitute": False,
        "unit_head_scope": "recommend",
    },
    "EL": {
        "days_per_year": 30,          # for staff; faculty use VL
        "half_day_allowed": False,
        "carries_forward": True,
        "requires_substitute": True,
        "unit_head_scope": "recommend",
    },
    "COL": {
        "days_per_year": 20,          # BR-EL-009: 20 COL days/year
        "half_day_allowed": False,
        "carries_forward": True,
        "requires_substitute": True,
        "unit_head_scope": "recommend",
    },
    "VL": {
        "days_per_year": 60,          # BR-EL-006: 60 VL associated with vacation periods
        "half_day_allowed": False,
        "carries_forward": False,     # BR-EL-007: converts 2:1 to EL, VL itself does not carry forward
        "requires_substitute": True,
        "unit_head_scope": "recommend",
    },
}


def get_category_entitlement(category: str, employee_kind: str = "staff") -> dict:
    """Return entitlement dict for given leave category and employee kind."""
    base = _ENTITLEMENTS.get(category, {})
    result = dict(base)
    # Faculty get VL instead of EL, EL entitlement is 0 for them
    if employee_kind == "faculty" and category == "EL":
        result["days_per_year"] = 0
    if employee_kind != "faculty" and category == "VL":
        result["days_per_year"] = 0
    return result


def count_leave_days(
    start_date: date,
    end_date: date,
    category: str = "CL",
    half_day: bool = False,
    holidays: set[date] | None = None,
) -> Decimal:
    """
    Count leave days between start and end dates (inclusive).
    BR-EL-010: Returns 0.5 for a half-day leave (CL only).
    BR-EL-011: For EL, COL, and VL, intervening weekends and closed holidays
    inside the continuous approved interval count as leave days.
    For CL, SCL, and RH, weekends and closed holidays do NOT count as leave days.
    """
    if half_day:
        return Decimal("0.5")
    if end_date < start_date:
        return Decimal("0")

    if category in ("EL", "COL", "VL"):
        delta = (end_date - start_date).days + 1
        return Decimal(str(delta))

    holidays = holidays or set()
    total = 0
    cur = start_date
    while cur <= end_date:
        # Weekend: Saturday is 5, Sunday is 6
        if cur.weekday() < 5 and cur not in holidays:
            total += 1
        cur += timedelta(days=1)
    return Decimal(str(total))


def can_take_half_day(category: str) -> bool:
    """Only Casual Leave supports half-day."""
    return _ENTITLEMENTS.get(category, {}).get("half_day_allowed", False)


def carries_forward(category: str) -> bool:
    """EL and COL carry forward; CL, RH, SCL, VL lapse at year end."""
    return _ENTITLEMENTS.get(category, {}).get("carries_forward", False)


def requires_substitute(category: str) -> bool:
    """EL, COL, and VL require a substitute arrangement."""
    return _ENTITLEMENTS.get(category, {}).get("requires_substitute", False)


def get_unit_head_scope(category: str) -> str:
    """
    Returns 'final' if unit head can directly sanction/reject,
    or 'recommend' if unit head can only recommend and final authority lies elsewhere.
    """
    return _ENTITLEMENTS.get(category, {}).get("unit_head_scope", "recommend")


def year_end_process(user_id: int, year: str, balances: list[dict], employee_kind: str = "staff") -> list[dict]:
    """
    Compute year-end adjustments for the user.
    balances: list of {category: str, balance_days: Decimal}
    Returns list of adjustment dicts describing what should happen.
    BR-EL-002, 003, 004: CL, RH, SCL lapse at year end.
    BR-EL-007, 008: At year end, all unused faculty VL converts to EL at 2 VL : 1 EL.
    BR-EL-005, 009: EL and COL carry forward.
    """
    adjustments = []
    for b in balances:
        cat = b["category"]
        days = Decimal(str(b.get("balance_days", 0)))
        if cat == "VL" and employee_kind == "faculty":
            # BR-EL-007: 2 VL -> 1 EL (including fractional conversion)
            converted_el = days / Decimal("2")
            adjustments.append({
                "user_id": user_id,
                "category": "VL",
                "year": year,
                "action": "convert_to_el",
                "days": days,
                "credited_el": converted_el,
            })
        elif carries_forward(cat):
            # EL: cap carry-forward at 300 days (simplified rule)
            cap = Decimal("300")
            carry = min(days, cap)
            adjustments.append({
                "user_id": user_id,
                "category": cat,
                "year": year,
                "action": "carry_forward",
                "days": carry,
            })
        else:
            # lapse remaining balance
            adjustments.append({
                "user_id": user_id,
                "category": cat,
                "year": year,
                "action": "lapse",
                "days": days,
            })
    return adjustments
